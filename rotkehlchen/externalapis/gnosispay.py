import logging
from dataclasses import dataclass
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal

import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import EVMTxHash, Location, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import (
    iso8601ts_to_timestamp,
    set_user_agent,
    timestamp_to_iso8601,
    ts_now,
)
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# the seconds around a transaction to search for when querying the API
GNOSIS_PAY_TX_TIMESTAMP_RANGE = 30


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
    reversal_tx_hash: EVMTxHash | None  # only if there is a refund


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

    def _query(
            self,
            endpoint: Literal['transactions'],
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query a gnosis pay API endpoint with the hacky session token authentication

        May raise:
        - RemoteError if there is a problem querying the API
        """
        querystr = 'https://api.gnosispay.com/api/v1/' + endpoint
        log.debug(f'Querying Gnosis Pay API {querystr} with {params=}')
        timeout = CachedSettings().get_timeout_tuple()
        try:
            response = self.session.get(
                url=querystr,
                params=params,
                timeout=timeout,
                cookies={'__Secure-authjs.session-token': self.session_token},
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying {querystr} failed due to {e!s}') from e

        if response.status_code != HTTPStatus.OK:
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                try:
                    error_message = response.json().get('message', response.text)
                except JSONDecodeError:
                    error_message = response.text

                self.database.msg_aggregator.add_message(
                    message_type=WSMessageType.GNOSISPAY_SESSIONKEY_EXPIRED,
                    data={'error': error_message},
                )

            raise RemoteError(
                f'Gnosis Pay API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_list(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Gnosis Pay API returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    def maybe_deserialize_transaction(self, data: dict[str, Any]) -> GnosisPayTransaction | None:
        try:
            if (
                    (kind := data['kind']) == 'Payment' and
                    # status is missing for kind == Reversal so None is also valid here
                    data.get('status') not in ('Approved', 'Reversal', 'PartialReversal')
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
                reversal_tx_hash=None,  # atm does not appear in the API
            )

        except KeyError as e:
            log.error(f'Could not find key {e!s} in Gnosis pay transaction response: {data}')
        except DeserializationError as e:
            log.error(f'Failed to read gnosis pay data {data} due to {e!s}')

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
            reversal_tx_hash=deserialize_evm_tx_hash(data[12]) if data[12] is not None else None,
        )

    def find_db_data(
            self,
            wherestatement: str,
            bindings: tuple,
            with_identifier: bool = False,
    ) -> tuple[GnosisPayTransaction | None, int | None]:
        """Return the gnosis pay data matching the given DB data"""
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                f'SELECT tx_hash, timestamp, merchant_name, merchant_city, country, mcc, '
                f'transaction_symbol, transaction_amount, billing_symbol, billing_amount, '
                f'reversal_symbol, reversal_amount, reversal_tx_hash '
                f'{", identifier " if with_identifier else ""}'
                f'FROM gnosispay_data WHERE {wherestatement}', bindings,
            )
            if (result := cursor.fetchone()) is None:
                return None, None

        return (
            self._deserialize_transaction_from_db(result),
            result[13] if with_identifier else None,
        )

    def maybe_find_update_refund(
            self,
            tx_hash: EVMTxHash,
            tx_timestamp: Timestamp,
            amount: FVal,
            asset: AssetWithSymbol,
    ) -> str | None:
        transaction, identifier = self.find_db_data(
            wherestatement='reversal_amount=? AND reversal_symbol=? AND timestamp<?',
            bindings=(
                str(amount),
                asset.resolve_to_asset_with_symbol().symbol[:-1],  # API shows normal EUR, GBP
                tx_timestamp,
            ),
            with_identifier=True,
        )
        if transaction is None:
            return None

        with self.database.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE gnosispay_data SET reversal_tx_hash=? WHERE identifier=?',
                (tx_hash, identifier),
            )

        return self.create_notes_for_transaction(transaction, is_refund=True)

    def get_data_for_transaction(
            self,
            tx_hash: EVMTxHash,
            tx_timestamp: Timestamp,
    ) -> str | None:
        """Gets the Gnosis pay data for the given transaction and returns its notes if found.

        Either from the DB or by querying the API
        """
        transaction, _ = self.find_db_data(
            wherestatement='tx_hash=? OR reversal_tx_hash=?',
            bindings=(tx_hash, tx_hash),
        )
        if transaction:
            return self.create_notes_for_transaction(
                transaction=transaction,
                is_refund=False,
            )

        # else we need to query the API
        try:
            data = self._query(
                endpoint='transactions',
                params={
                    'after': timestamp_to_iso8601(Timestamp(tx_timestamp - 1)),
                    'before': timestamp_to_iso8601(Timestamp(tx_timestamp + 1)),
                },
            )
        except RemoteError as e:
            log.error(f'Could not query Gnosis Pay API due to {e!s}')
            return None

        # since this probably contains more transactions than the one we need dont
        # let the query go to waste and update data for all and return only the one we need
        result_tx = None
        for entry in data:
            if (transaction := self.maybe_deserialize_transaction(entry)) is None:
                continue

            if tx_hash == transaction.tx_hash:
                result_tx = transaction
            else:
                self.maybe_update_event_with_api_data(transaction)

            self.write_txdata_to_db(transaction)

        return self.create_notes_for_transaction(result_tx, is_refund=False) if result_tx else None

    def query_remote_for_tx_and_update_events(self, tx_timestamp: Timestamp) -> None:
        """Query the API for a single transaction and update the events if found"""
        try:
            data = self._query(
                endpoint='transactions',
                params={
                    'after': timestamp_to_iso8601(Timestamp(tx_timestamp - GNOSIS_PAY_TX_TIMESTAMP_RANGE)),  # noqa: E501
                    'before': timestamp_to_iso8601(Timestamp(tx_timestamp + GNOSIS_PAY_TX_TIMESTAMP_RANGE)),  # noqa: E501
                },
            )
        except RemoteError as e:
            log.error(f'Could not query Gnosis Pay API due to {e!s}')
            return None

        log.debug(f'Gnosis api query returned {len(data)} transactions')
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
        existing_txs = set()
        with self.database.conn.read_ctx() as cursor:
            for bindings, placeholders in get_query_chunks(data=list(tx_timestamps.keys())):
                for row in cursor.execute(
                    f'SELECT tx_hash, timestamp, merchant_name, merchant_city, country, mcc, '
                    f'transaction_symbol, transaction_amount, billing_symbol, billing_amount, '
                    f'reversal_symbol, reversal_amount, reversal_tx_hash FROM gnosispay_data '
                    f'WHERE tx_hash IN ({placeholders})',
                    bindings,
                ):
                    self.maybe_update_event_with_api_data(
                        transaction=(tx := self._deserialize_transaction_from_db(row)),
                    )
                    existing_txs.add(tx.tx_hash)

        missing_txs = sorted(
            set(tx_timestamps.keys()) - existing_txs,
            key=lambda tx_hash: tx_timestamps[tx_hash],
        )
        last_queried_ts = Timestamp(0)
        for tx_hash in missing_txs:
            if (tx_timestamp := tx_timestamps[tx_hash]) - last_queried_ts <= GNOSIS_PAY_TX_TIMESTAMP_RANGE:  # noqa: E501
                continue  # skip if already included in last query

            self.query_remote_for_tx_and_update_events(tx_timestamp=tx_timestamp)
            last_queried_ts = tx_timestamp

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

        notes += f' {preposition} {transaction.merchant_name}'
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
            log.error(f'Could not find gnosis pay event corresponding to {transaction.tx_hash.hex()} in the DB. Skipping.')  # pylint: disable=no-member # noqa: E501
            return

        notes = self.create_notes_for_transaction(transaction, is_refund=False)
        log.debug(f'Updating notes for gnosis pay event with tx_hash={transaction.tx_hash.hex()}')  # pylint: disable=no-member
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
        data = self._query(
            endpoint='transactions',
            params={'after': timestamp_to_iso8601(after_ts)},  # after is exclusive
        )
        for entry in data:
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
