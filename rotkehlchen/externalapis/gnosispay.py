import logging
from dataclasses import dataclass
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, cast

import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.chain.evm.constants import EVM_ADDRESS_REGEX
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.utils import notify_reauthentication_required
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_fval
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import (
    ROTKI_USER_AGENT,
    iso8601ts_to_timestamp,
    set_user_agent,
    timestamp_to_iso8601,
    ts_ms_to_sec,
    ts_now,
)
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# the seconds around a transaction to search for when querying the API.
# We use 8 hours because it seems that they don't respect timezones and in order to be
# safe we use a wide query range
GNOSIS_PAY_TX_TIMESTAMP_RANGE: Final = HOUR_IN_SECONDS * 8
GNOSIS_PAY_PAGE_SIZE: Final = 100
GNOSIS_PAY_API_BASE_URL: Final = 'https://api.gnosispay.com/api/v1'
GNOSIS_PAY_AUTH_NONCE_ENDPOINT: Final = 'auth/nonce'
GNOSIS_PAY_AUTH_CHALLENGE_ENDPOINT: Final = 'auth/challenge'
GNOSIS_PAY_SAFE_MIGRATION_ENDPOINT: Final = 'safe/migration'
GNOSIS_PAY_SAFE_MIGRATION_ID: Final = 'safe-replacement-2026-06'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class GnosisPayTransaction:
    """The merchant data we keep for a gnosis pay transaction"""
    tx_hash: EVMTxHash
    timestamp: Timestamp
    merchant_name: str
    merchant_city: str | None  # sometimes missing (due to being a phone)
    country: str  # the alpha2 country code
    mcc: int
    transaction_symbol: str
    transaction_amount: FVal
    billing_symbol: str | None  # only if different to the transaction one
    billing_amount: FVal | None  # only if different to the transaction one
    reversal_symbol: str | None  # only if there is a refund
    reversal_amount: FVal | None  # only if there is a refund


@dataclass(frozen=True)
class GnosisPaySafeMigration:
    migration_id: str
    old_safe: ChecksumEvmAddress | None
    new_safe: ChecksumEvmAddress

    def serialize(self) -> dict[str, str | None]:
        return {
            'migration_id': self.migration_id,
            'old_safe': self.old_safe,
            'new_safe': self.new_safe,
        }


class GnosisPay:
    """This is the gnosis pay API interface

    https://api.gnosispay.com/api-docs/

    For now they have no api keys but you can get the __Secure-authjs.session-token
    cookie from your local storage once logged in and put it to rotki. Then all data
    is queriable.

    DMed by gnosis pay devs
    export enum PaymentStatus {
      Approved = "Approved",
      IncorrectPin = "IncorrectPin",
      InsufficientFunds = "InsufficientFunds",
      InvalidAmount = "InvalidAmount",
      PinEntryTriesExceeded = "PinEntryTriesExceeded",
      IncorrectSecurityCode = "IncorrectSecurityCode",
      Reversal = "Reversal",
      PartialReversal = "PartialReversal",
      Other = "Other",
    }

    mcc is the merchant code category and details can be seen here:
    https://usa.visa.com/content/dam/VCOM/download/merchants/visa-merchant-data-standards-manual.pdf
    """

    def __init__(self, database: 'DBHandler', session_token: str) -> None:
        self.database = database
        self.session = create_session()
        self.session_token = session_token
        set_user_agent(self.session)
        self.session.headers = {'Authorization': f'Bearer {self.session_token}'}

    def _query(
            self,
            endpoint: Literal['cards/transactions', 'safe/migration'],
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query a gnosis pay API endpoint.

        May raise:
        - RemoteError if there is a problem querying the API
        """
        querystr = f'{GNOSIS_PAY_API_BASE_URL}/{endpoint}'
        log.debug(f'Querying Gnosis Pay API {querystr} with {params=}')
        timeout = CachedSettings().get_timeout_tuple()
        try:
            response = self.session.get(
                url=querystr,
                params=params,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying {querystr} failed due to {e!s}') from e

        if response.status_code != HTTPStatus.OK:
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                try:
                    error_message = response.json().get('message', response.text)
                except JSONDecodeError:
                    error_message = response.text

                log.error(f'Failed to connect to the GnosisPay API due to {error_message}')
                notify_reauthentication_required(database=self.database, service='gnosispay')

            raise RemoteError(
                f'Gnosis Pay API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        # paginated response has this format
        # {"count":565,"next":"/api/v1/cards/transactions?after=1970-01-01T00%3A00%3A00%2B00%3A00&offset=100&limit=100","previous":null,"results":[]}  # noqa: E501,ERA001

        try:
            data = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Gnosis Pay API returned invalid JSON response: {response.text}',
            ) from e

        return data

    def _query_paginated(
            self,
            before: Timestamp | None = None,
            after: Timestamp | None = None,
            page_size: int = GNOSIS_PAY_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from the paginated cards/transactions endpoint.

        The endpoint supports integer limit/offset and ISO 8601 before/after filters.
        https://docs.gnosispay.com/api-reference/card-management/get-paginated-transactions-for-activated-cards
        """
        collected: list[dict[str, Any]] = []
        offset, limit = 0, page_size
        page_params: dict[str, str | int] = {}

        if before is not None:
            page_params['before'] = timestamp_to_iso8601(before)
        if after is not None:
            page_params['after'] = timestamp_to_iso8601(after)

        while True:
            page_params['limit'] = limit
            page_params['offset'] = offset
            data = self._query(endpoint='cards/transactions', params=page_params)
            if not isinstance(page := data.get('results'), list):
                log.error('Missing or invalid results in gnosis pay response: %s', data)
                raise RemoteError('results key missing from paginated endpoint')

            if len(page) == 0:
                # from the docs: The final number might differ a little bit, as one thread might contain multiple transactions.  # noqa: E501
                # GnosisPay has the concept of threads that are unique payments made with card
                # and each thread contains one or two transactions, the payment and the reversal.
                # The endpoint returns a list of threads and each one of those contains the
                # on chain transactions. The pagination is done with transactions and this
                # is why the len of the page might not match the limit.
                break

            collected.extend(cast('list[dict[str, Any]]', page))
            offset += limit

        return collected

    @staticmethod
    def _deserialize_safe_migration(data: dict[str, Any]) -> GnosisPaySafeMigration | None:
        """Validate and deserialize a Gnosis Pay Safe migration response."""
        try:
            old_safe_data = data.get('oldSafe') if data.get('hasOldSafe') is True else None
            gnosis_chain_id = str(ChainID.GNOSIS.serialize())
            if (
                data['migrationId'] != GNOSIS_PAY_SAFE_MIGRATION_ID or
                data['newSafe']['chainId'] != gnosis_chain_id or
                (
                    old_safe_data is not None and
                    old_safe_data['chainId'] != gnosis_chain_id
                )
            ):
                log.error('Ignoring unsupported Gnosis Pay Safe migration data: %s', data)
                return None

            return GnosisPaySafeMigration(
                migration_id=data['migrationId'],
                old_safe=(
                    deserialize_evm_address(old_safe_data['address'])
                    if old_safe_data is not None
                    else None
                ),
                new_safe=deserialize_evm_address(data['newSafe']['address']),
            )
        except (DeserializationError, KeyError, TypeError) as e:
            log.error(
                'Failed to deserialize Gnosis Pay Safe migration data %s due to %s',
                data,
                e,
            )
            return None

    def _get_safe_migration(self) -> GnosisPaySafeMigration | None:
        with self.database.conn.read_ctx() as cursor:
            cached_data = self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.GNOSIS_PAY_SAFE_MIGRATION,
            )

        if isinstance(cached_data, str):
            try:
                migration = self._deserialize_safe_migration_from_cache(
                    data=jsonloads_dict(cached_data),
                )
            except JSONDecodeError as e:
                log.error('Failed to deserialize cached Gnosis Pay Safe migration due to %s', e)
            else:
                if migration is not None:
                    return migration

        data = self._query(
            endpoint=GNOSIS_PAY_SAFE_MIGRATION_ENDPOINT,
            params={'migrationId': GNOSIS_PAY_SAFE_MIGRATION_ID},
        )
        if (migration := self._deserialize_safe_migration(data)) is None:
            return None

        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.GNOSIS_PAY_SAFE_MIGRATION,
                value=rlk_jsondumps(migration.serialize()),
            )
        return migration

    @staticmethod
    def _deserialize_safe_migration_from_cache(
            data: dict[str, Any],
    ) -> GnosisPaySafeMigration | None:
        try:
            if data['migration_id'] != GNOSIS_PAY_SAFE_MIGRATION_ID:
                return None

            return GnosisPaySafeMigration(
                migration_id=data['migration_id'],
                old_safe=(
                    deserialize_evm_address(data['old_safe'])
                    if data['old_safe'] is not None
                    else None
                ),
                new_safe=deserialize_evm_address(data['new_safe']),
            )
        except (DeserializationError, KeyError, TypeError) as e:
            log.error(
                'Failed to deserialize cached Gnosis Pay Safe migration %s due to %s',
                data,
                e,
            )
            return None

    def check_safe_migration(self) -> None:
        """Suggest the other Safe when exactly one side of the migration is tracked."""
        try:
            migration = self._get_safe_migration()
        except RemoteError as e:
            log.error('Could not query Gnosis Pay Safe migration due to %s', e)
            return

        if migration is None or migration.old_safe is None:
            return

        with self.database.conn.read_ctx() as cursor:
            tracked_addresses = {
                address for (address,) in cursor.execute(
                    'SELECT account FROM blockchain_accounts WHERE blockchain=?',
                    (SupportedBlockchain.GNOSIS.value,),
                )
            }

        old_is_tracked = migration.old_safe in tracked_addresses
        new_is_tracked = migration.new_safe in tracked_addresses
        if old_is_tracked == new_is_tracked:
            return

        tracked_address = migration.old_safe if old_is_tracked else migration.new_safe
        missing_address = migration.new_safe if old_is_tracked else migration.old_safe
        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.GNOSIS_PAY_SAFE_MIGRATION,
            data={
                'migration_id': migration.migration_id,
                'tracked_address': tracked_address,
                'missing_address': missing_address,
                'missing_address_type': 'new' if old_is_tracked else 'old',
                'chain': SupportedBlockchain.GNOSIS.serialize(),
            },
            deduplication_key=f'gnosis_pay_safe_migration_{migration.migration_id}',
        )

    def maybe_deserialize_transaction(self, data: dict[str, Any]) -> GnosisPayTransaction | None:
        try:
            if (
                (
                    (kind := data['kind']) == 'Payment' and
                    # status is missing for kind == Reversal so None is also valid here
                    data.get('status') not in ('Approved', 'Reversal', 'PartialReversal')
                ) or
                kind == 'Refund'  # Refunds are missing transactions data so we can't link them to onchain events  # noqa: E501
            ):
                log.debug(f'Ignoring gnosis pay data entry {data}')
                return None  # only use Approved/Reversal for payments

            log.debug(f'Deserializing gnosis pay transaction: {data}')
            if (city := data['merchant']['city'].rstrip()).startswith('+') or city.replace('-', '').isdigit():  # noqa: E501
                city = None
            tx_currency_symbol = data['transactionCurrency']['symbol']
            tx_currency_amount = deserialize_fval(value=data['transactionAmount'], name='currency_amount', location='gnosis pay data') / FVal(10 ** data['transactionCurrency']['decimals'])  # noqa: E501
            if (billing_currency_symbol := data['billingCurrency']['symbol']) != tx_currency_symbol:  # noqa: E501
                billing_currency_amount = deserialize_fval(value=data['billingAmount'], name='billing_amount', location='gnosis pay data') / FVal(10 ** data['billingCurrency']['decimals'])  # noqa: E501
            else:
                billing_currency_symbol, billing_currency_amount = None, None

            reversal_currency_symbol, reversal_amount = None, None
            if kind in ('Reversal', 'PartialReversal'):
                reversal_currency_symbol = data['reversalCurrency']['symbol']
                reversal_amount = deserialize_fval(value=data['reversalAmount'], name='reversal_amount', location='gnosis pay data') / FVal(10 ** data['reversalCurrency']['decimals'])  # noqa: E501

            return GnosisPayTransaction(
                tx_hash=deserialize_evm_tx_hash(data['transactions'][0]['hash']),
                timestamp=iso8601ts_to_timestamp(data['createdAt']),
                merchant_name=data['merchant']['name'].rstrip(),
                merchant_city=city,
                country=data['merchant']['country']['alpha2'],
                mcc=int(data['mcc']),
                transaction_symbol=tx_currency_symbol,
                transaction_amount=tx_currency_amount,
                billing_symbol=billing_currency_symbol,
                billing_amount=billing_currency_amount,
                reversal_symbol=reversal_currency_symbol,
                reversal_amount=reversal_amount,
            )

        except (DeserializationError, KeyError, IndexError) as e:
            msg = f'missing key: {e}' if isinstance(e, KeyError) else str(e)
            log.error(f'Failed to read gnosis pay data {data} due to {msg}')

        return None

    def write_txdata_to_db(self, transaction: GnosisPayTransaction) -> None:
        with self.database.conn.read_ctx() as cursor:
            existing_result = cursor.execute(
                'SELECT reversal_amount FROM gnosispay_data WHERE tx_hash=?',
                (transaction.tx_hash,),
            ).fetchone()

        if existing_result and existing_result[0] is not None:
            return  # already existing and has a reversal amount. Don't overwrite

        # else it either does not exist in the DB or exists with normal data so
        # even if overwriting we should not lose any data
        with self.database.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO gnosispay_data(tx_hash, timestamp, merchant_name, '
                'merchant_city, country, mcc, transaction_symbol, transaction_amount, '
                'billing_symbol, billing_amount, reversal_symbol, reversal_amount) '
                'VALUES(?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?)',
                (transaction.tx_hash, transaction.timestamp, transaction.merchant_name,
                 transaction.merchant_city, transaction.country, transaction.mcc,
                 transaction.transaction_symbol, str(transaction.transaction_amount),
                 transaction.billing_symbol,
                 str(transaction.billing_amount) if transaction.billing_amount else None,
                 transaction.reversal_symbol,
                 str(transaction.reversal_amount) if transaction.reversal_amount else None),
            )

    def _deserialize_transaction_from_db(self, data: tuple[Any, ...]) -> GnosisPayTransaction:
        """Deserialize a gnosis pay transaction from the DB data"""
        billing_symbol, billing_amount = None, None
        if data[8] is not None:
            billing_symbol, billing_amount = data[8], FVal(data[9])

        reversal_symbol, reversal_amount = None, None
        if data[10] is not None:
            reversal_symbol, reversal_amount = data[10], FVal(data[11])

        return GnosisPayTransaction(
            tx_hash=deserialize_evm_tx_hash(data[0]),
            timestamp=Timestamp(data[1]),
            merchant_name=data[2],
            merchant_city=data[3],
            country=data[4],
            mcc=data[5],
            transaction_symbol=data[6],
            transaction_amount=FVal(data[7]),
            billing_symbol=billing_symbol,
            billing_amount=billing_amount,
            reversal_symbol=reversal_symbol,
            reversal_amount=reversal_amount,
        )

    def find_db_data(
            self,
            wherestatement: str,
            bindings: tuple,
    ) -> GnosisPayTransaction | None:
        """Return the gnosis pay data matching the given DB data"""
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                f'SELECT tx_hash, timestamp, merchant_name, merchant_city, country, mcc, '
                f'transaction_symbol, transaction_amount, billing_symbol, billing_amount, '
                f'reversal_symbol, reversal_amount '
                f'FROM gnosispay_data WHERE {wherestatement}', bindings,
            )
            if (result := cursor.fetchone()) is None:
                return None

        return self._deserialize_transaction_from_db(result)

    def maybe_find_update_refund(
            self,
            tx_hash: EVMTxHash,
            tx_timestamp: Timestamp,
            amount: FVal,
            asset: AssetWithSymbol,
    ) -> str | None:
        transaction = self.find_db_data(
            wherestatement='reversal_amount=? AND reversal_symbol=? AND timestamp<?',
            bindings=(
                str(amount),
                asset.resolve_to_asset_with_symbol().symbol[:-1],  # API shows normal EUR, GBP
                tx_timestamp,
            ),
        )
        if transaction is None:
            return None

        return self.create_notes_for_transaction(transaction, is_refund=True)

    def query_remote_for_tx_and_update_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Query the API for transactions in a range of time.

        If before_ts and after_ts are equal and match the timestamp of a transaction it
        will return the information relevant to that transaction only.

        After querying the transaction information it is saved in the database
        and the history event entry for that transaction is updated.
        """
        try:
            data = self._query_paginated(
                before=Timestamp(end_ts + GNOSIS_PAY_TX_TIMESTAMP_RANGE),
                after=Timestamp(start_ts - GNOSIS_PAY_TX_TIMESTAMP_RANGE),
            )
        except RemoteError as e:
            log.error(f'Could not query Gnosis Pay API due to {e!s}')
            return None

        log.debug('Gnosis api query returned %s transactions', len(data))
        # since this may contain more transactions than the one we need dont
        # let the query go to waste and update data for all
        for entry in data:
            if (transaction := self.maybe_deserialize_transaction(entry)) is None:
                continue

            self.write_txdata_to_db(transaction)
            self.maybe_update_event_with_api_data(transaction)

    def update_events(self, tx_timestamps: dict[EVMTxHash, Timestamp]) -> None:
        """Update the events for the given transactions.
        Queries the API only for transactions missing from the db.
        """
        existing_tx_hashes = set()
        with self.database.conn.read_ctx() as cursor:
            for bindings, placeholders in get_query_chunks(data=list(tx_timestamps.keys())):
                for row in cursor.execute(
                    f'SELECT tx_hash, timestamp, merchant_name, merchant_city, country, mcc, '
                    f'transaction_symbol, transaction_amount, billing_symbol, billing_amount, '
                    f'reversal_symbol, reversal_amount FROM gnosispay_data '
                    f'WHERE tx_hash IN ({placeholders})',
                    bindings,
                ):
                    self.maybe_update_event_with_api_data(
                        transaction=(tx := self._deserialize_transaction_from_db(row)),
                    )
                    existing_tx_hashes.add(tx.tx_hash)

        missing_tx_hashes = sorted(  # missing tx hashes in ascending order of ts
            set(tx_timestamps.keys()) - existing_tx_hashes,
            key=lambda tx_hash: tx_timestamps[tx_hash],
        )

        if len(missing_tx_hashes) == 0:
            log.debug('No gnosis transaction is missing metadata information from this batch.')
            return

        # else
        log.debug(f'{missing_tx_hashes} transactions are missing gnosis pay information locally. Will query it')  # noqa: E501
        self.query_remote_for_tx_and_update_events(
            start_ts=tx_timestamps[missing_tx_hashes[0]],
            end_ts=tx_timestamps[missing_tx_hashes[-1]],
        )

    def backfill_missing_events(self) -> None:
        """Fetch merchant data for events missing Gnosis Pay metadata."""
        tx_timestamps: dict[EVMTxHash, Timestamp] = {}
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT EI.tx_ref, H.timestamp '
                'FROM history_events H '
                'INNER JOIN chain_events_info EI ON EI.identifier = H.identifier '
                'WHERE H.location = ? AND EI.counterparty = ? AND H.notes LIKE ?',
                (Location.GNOSIS.serialize_for_db(), CPT_GNOSIS_PAY, 'Spend% via Gnosis Pay'),
            )
            for raw_tx_hash, timestamp_ms in cursor:
                if raw_tx_hash is None or timestamp_ms is None:
                    continue

                try:
                    tx_hash = deserialize_evm_tx_hash(raw_tx_hash)
                except DeserializationError as exc:
                    log.error(f'Failed to deserialize Gnosis Pay tx hash {raw_tx_hash}. {exc!s}')
                    continue

                tx_timestamps[tx_hash] = ts_ms_to_sec(TimestampMS(timestamp_ms))

        if len(tx_timestamps) == 0:
            log.debug('No Gnosis Pay events require fetching merchant metadata.')
            return

        self.update_events(tx_timestamps=tx_timestamps)

    def create_notes_for_transaction(
            self,
            transaction: GnosisPayTransaction,
            is_refund: bool,
    ) -> str:
        """Create the modified notes for the gnosis pay transaction"""
        verb, preposition = 'Pay', 'to'
        if transaction.mcc == 6011:  # ATM cash withdrawal
            verb, preposition = 'Withdraw', 'from'

        if is_refund:
            preposition = 'from'
            notes = f'Receive refund of {transaction.reversal_amount} {transaction.reversal_symbol}'  # noqa: E501
        else:
            notes = f'{verb} {transaction.transaction_amount} {transaction.transaction_symbol}'
            if transaction.billing_symbol:
                notes += f' ({transaction.billing_amount} {transaction.billing_symbol})'

        notes += f' {preposition} :merchant_code:{transaction.mcc}: {transaction.merchant_name}'
        if transaction.merchant_city:
            notes += f' in {transaction.merchant_city}'

        notes += f' :country:{transaction.country}:'
        return notes

    def maybe_update_event_with_api_data(self, transaction: GnosisPayTransaction) -> None:
        """Try to find the history event for the given Gnosis Pay merchant data and update it"""
        dbevents = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            events = dbevents.get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    tx_hashes=[transaction.tx_hash],
                    counterparties=[CPT_GNOSIS_PAY],
                    location=Location.GNOSIS,
                ),
            )

        if len(events) != 1:
            log.error(f'Could not find gnosis pay event corresponding to {transaction.tx_hash!s} in the DB. Skipping.')  # noqa: E501
            return

        notes = self.create_notes_for_transaction(transaction, is_refund=False)
        log.debug(f'Updating notes for gnosis pay event with tx_hash={transaction.tx_hash!s}')
        with self.database.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE history_events SET notes=? WHERE identifier=?',
                (notes, events[0].identifier),
            )

    def get_and_process_transactions(
            self,
            after_ts: Timestamp,
    ) -> None:
        """Query for gnosis pay transactions and merchant data after a given timestamp.

        Then search for our events and if there is a matching event overlay the
        merchant data on top.
        """
        log.debug('Starting task to query for gnosis pay merchant transaction data')
        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.execute(  # remember last time task ran
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value, str(ts_now())),
            )

        # after is exclusive. Use paginated fetching to cover all pages
        for entry in self._query_paginated(after=after_ts):
            if (transaction := self.maybe_deserialize_transaction(entry)) is None:
                continue

            self.write_txdata_to_db(transaction)
            self.maybe_update_event_with_api_data(transaction)


def init_gnosis_pay(database: 'DBHandler') -> GnosisPay | None:
    """Create a gnosis pay instance using the provided database"""
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT api_key FROM external_service_credentials WHERE name=?',
            ('gnosis_pay',),
        ).fetchone()
        if result is None:
            return None

    return GnosisPay(database=database, session_token=result[0])


def fetch_gnosis_pay_siwe_nonce() -> str:
    """Fetch a SIWE nonce from the public Gnosis Pay API.

    May raise:
    - RemoteError if the request fails or returns an unexpected payload.
    """
    timeout = CachedSettings().get_timeout_tuple()
    url = f'{GNOSIS_PAY_API_BASE_URL}/{GNOSIS_PAY_AUTH_NONCE_ENDPOINT}'
    try:
        response = requests.get(
            url=url,
            timeout=timeout,
            headers={'User-Agent': ROTKI_USER_AGENT},
        )
    except requests.RequestException as e:
        raise RemoteError(f'Failed to fetch Gnosis Pay nonce: {e!s}') from e

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(
            f'Gnosis Pay nonce request failed with HTTP status code '
            f'{response.status_code} and text {response.text}',
        )

    nonce = response.text.strip()
    if nonce == '':
        raise RemoteError('Gnosis Pay nonce response was empty')

    return nonce


def verify_gnosis_pay_siwe_signature(message: str, signature: str) -> str:
    """Verify a SIWE signature and retrieve the auth token from Gnosis Pay.

    May raise:
    - RemoteError if the request fails or the response is invalid.
    """
    timeout = CachedSettings().get_timeout_tuple()
    try:
        response = requests.post(
            url=f'{GNOSIS_PAY_API_BASE_URL}/{GNOSIS_PAY_AUTH_CHALLENGE_ENDPOINT}',
            json={'message': message, 'signature': signature, 'ttlInSeconds': DAY_IN_SECONDS},
            timeout=timeout,
            headers={'User-Agent': ROTKI_USER_AGENT},
        )
    except requests.RequestException as e:
        raise RemoteError(f'Failed to verify Gnosis Pay SIWE signature: {e!s}') from e

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(
            f'Gnosis Pay challenge request failed with HTTP status code '
            f'{response.status_code} and text {response.text}',
        )

    try:
        data = jsonloads_dict(response.text)
    except JSONDecodeError as e:
        raise RemoteError(
            f'Gnosis Pay challenge returned invalid JSON response: {response.text}',
        ) from e

    if not isinstance(token := data.get('token'), str) or token == '':
        raise RemoteError(
            f'Unexpected payload while verifying Gnosis Pay SIWE signature: {response.text}',
        )

    try:
        balances_response = requests.get(
            url=f'{GNOSIS_PAY_API_BASE_URL}/account-balances',
            timeout=timeout,
            headers={'User-Agent': ROTKI_USER_AGENT, 'Authorization': f'Bearer {token}'},
        )
    except requests.RequestException as e:
        raise RemoteError(f'Failed to verify Gnosis Pay token against account balances: {e!s}') from e  # noqa: E501

    if balances_response.status_code != HTTPStatus.OK:
        signer_address_match = EVM_ADDRESS_REGEX.search(message)
        signer_address = signer_address_match.group(0) if signer_address_match else 'unknown address'  # unknown address should never appear  # noqa: E501
        raise RemoteError(
            f'Failed to authenticate with "{signer_address}". '
            'Make sure it is is an owner/signer of the Gnosis Pay safe',
        )

    return token
