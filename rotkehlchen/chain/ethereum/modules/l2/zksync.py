import logging
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, Optional
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_evm_address,
    deserialize_fee,
    deserialize_int_from_str,
)
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Fee,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium

from .constants import ZKSYNCLITE_MAX_LIMIT, ZKSYNCLITE_TX_SAVEPREFIX

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZKSyncLiteTXType(DBCharEnumMixIn):
    TRANSFER = 1
    DEPOSIT = 2
    WITHDRAW = 3
    CHANGEPUBKEY = 4  # we only use it for fee of changing public key
    FORCEDEXIT = 5  # we only use it for fee of exit.


ZKSyncLiteTransactionDBTuple = tuple[
    EVMTxHash,  # tx_hash
    str,    # type
    int,    # timestamp
    int,    # block number
    str | None,  # from_address
    str | None,  # to_address
    str,    # asset
    str,    # amount
    str | None,    # fee
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=True, frozen=False)
class ZKSyncLiteTransaction:
    tx_hash: EVMTxHash
    tx_type: ZKSyncLiteTXType
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEvmAddress | None
    to_address: ChecksumEvmAddress | None
    asset: Asset
    amount: FVal
    fee: Fee | None

    def serialize_for_db(self) -> ZKSyncLiteTransactionDBTuple:
        return (
            self.tx_hash,
            self.tx_type.serialize_for_db(),
            self.timestamp,
            self.block_number,
            self.from_address,
            self.to_address,
            self.asset.identifier,
            str(self.amount),
            str(self.fee) if self.fee is not None else None,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            data: ZKSyncLiteTransactionDBTuple,
    ) -> 'ZKSyncLiteTransaction':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            tx_hash=data[0],
            tx_type=ZKSyncLiteTXType.deserialize_from_db(data[1]),
            timestamp=Timestamp(data[2]),
            block_number=data[3],
            from_address=None if data[4] is None else string_to_evm_address(data[4]),
            to_address=None if data[5] is None else string_to_evm_address(data[5]),
            asset=Asset(data[6]),
            amount=deserialize_asset_amount(data[7]),
            fee=deserialize_fee(data[8]) if data[8] is not None else None,
        )


class ZksyncLite(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',  # pylint: disable=unused-argument
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,  # pylint: disable=unused-argument
            premium: Optional['Premium'],
    ) -> None:
        self.database = database
        self.premium = premium
        self.session = requests.session()
        set_user_agent(self.session)
        self.id_to_token: dict[int, CryptoAsset] = {}
        self.symbol_to_token: dict[str, CryptoAsset] = {}
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.ethereum_inquirer = ethereum_inquirer

    def _query_api(
            self,
            url: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """Queries zksync lite api v0.2

        https://docs.zksync.io/apiv02-docs/
        Unfortunately docs are offline and they don't fix them. Thankfully wayback machine has this
        https://web.archive.org/web/20230926085214/https://docs.zksync.io/apiv02-docs/#

        May raise:
        - RemoteError if there are any problems with reaching their server or if
        an unexpected response is returned
        """
        result: dict[str, Any] = {}
        query_str = 'https://api.zksync.io/api/v0.2/' + url
        if options:
            query_str += f'?{urlencode(options)}'

        backoff = 1
        backoff_limit = 33
        timeout = timeout if timeout else CachedSettings().get_timeout_tuple()
        while backoff < backoff_limit:
            log.debug(f'Querying zksync lite: {query_str}')
            try:
                response = self.session.get(query_str, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'ZKSync Lite API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if backoff >= backoff_limit:
                    raise RemoteError(
                        'Getting zksync lite too many requests error '
                        'even after we incrementally backed off',
                    )

                log.debug(
                    f'Got too many requests error from zksync lite. Will '
                    f'backoff for {backoff} seconds.',
                )
                gevent.sleep(backoff)
                backoff = backoff * 2
                continue

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'ZKSync Lite API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'ZKSync Lite API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            if (result := json_ret.get('result')) is None:  # type: ignore  # this if checks None
                raise RemoteError(
                    f'Unexpected format of ZKSync lite response for request {response.url}. '
                    f'Missing a result in response. Response was: {response.text}',
                )

            # success, break out of the loop and return result
            return result

        return result

    def _query_and_save_transactions_for_range(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            from_hash: str,
            direction: Literal['older', 'newer'],
    ) -> None:
        ranges = DBQueryRanges(self.database)
        location = f'{ZKSYNCLITE_TX_SAVEPREFIX}{address}'
        current_start_ts = start_ts
        current_end_ts = end_ts
        input_transactions: set[ZKSyncLiteTransaction] = set()
        for new_transactions in self._query_zksync_api_transactions(
                address=address,
                from_hash=from_hash,
                direction=direction,
        ):
            if len(new_transactions) == 0:
                continue

            unique_transactions = set(new_transactions)
            existing_txs = len(unique_transactions.intersection(input_transactions))
            if existing_txs != 0:
                log.debug(f'Got {existing_txs} already queried transactions during pagination')
                unique_transactions -= input_transactions

            with self.database.conn.write_ctx() as write_cursor:
                self._add_zksynctxs_db(
                    write_cursor=write_cursor,
                    transactions=unique_transactions,
                )
                if direction == 'older':
                    current_start_ts = new_transactions[-1].timestamp
                else:  # direction -> newer
                    current_end_ts = new_transactions[-1].timestamp
                ranges.update_used_query_range(
                    write_cursor=write_cursor,
                    location_string=location,
                    queried_ranges=[(current_start_ts, current_end_ts)],
                )

            input_transactions |= unique_transactions

    def _create_tokens_mapping(self) -> None:
        from_idx = 0
        while True:
            options = {'from': from_idx, 'direction': 'newer', 'limit': ZKSYNCLITE_MAX_LIMIT}
            response = self._query_api(url='tokens', options=options)
            result = response.get('list', None)
            if result is None:
                msg = 'Unexpected zksync lite tokens response. Could not find result in the response.'  # noqa: E501
                log.error(f'{msg} Response: {response}')
                raise RemoteError(msg)

            asset: CryptoAsset
            for entry in result[0 if from_idx == 0 else 1:]:
                try:  # if not first page we skip first since the from_idx repeats first entry
                    token_id = entry['id']
                    token_symbol = entry['symbol']
                    address = deserialize_evm_address(entry['address'])
                    if address == ZERO_ADDRESS:
                        asset = self.eth
                    else:
                        try:
                            asset = get_or_create_evm_token(
                                userdb=self.database,
                                evm_address=address,
                                chain_id=ChainID.ETHEREUM,
                                evm_inquirer=self.ethereum_inquirer,
                                encounter=TokenEncounterInfo(description='Querying zksync tokens mapping'),  # noqa: E501
                            )
                        except NotERC20Conformant:
                            log.warning(
                                f'ZKSync lite token id {token_id} with address {address} '
                                f'is unknown and as such will be ignored.',
                            )
                            continue

                    self.id_to_token[token_id] = asset
                    self.symbol_to_token[token_symbol] = asset

                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key {e!s}'
                    log.error(f'ZKSync lite token entry {entry} failed to be parsed due to {msg}')
                    continue

            # Check if we need to paginate further
            if len(result) < ZKSYNCLITE_MAX_LIMIT:
                break

            from_idx = result[-1]['id']  # result can't be empty here due to above

    def _get_token_by_id(self, token_id: int) -> CryptoAsset | None:
        if len(self.id_to_token) == 0:
            self._create_tokens_mapping()

        return self.id_to_token.get(token_id, None)

    def _get_token_by_symbol(self, token_symbol: str) -> CryptoAsset | None:
        if len(self.symbol_to_token) == 0:
            self._create_tokens_mapping()

        return self.symbol_to_token.get(token_symbol, None)

    def _deserialize_zksync_transaction(self, entry: dict[str, Any]) -> ZKSyncLiteTransaction | None:  # noqa: E501
        from_address = None
        try:
            if (status := entry.get('status', 'finalized')) != 'finalized':
                log.debug(f'Skipping zksynce lite transaction {entry} due to {status=}')
                return None

            tx_hash = deserialize_evm_tx_hash(entry['txHash'])
            tx_type = ZKSyncLiteTXType.deserialize(entry['op']['type'])
            block_number = entry['blockNumber']
            timestamp = iso8601ts_to_timestamp(entry['createdAt'])
            fee_str = entry['op'].get('fee')
            fee_raw = None
            if fee_str is not None:
                fee_raw = deserialize_int_from_str(
                    symbol=fee_str,
                    location='zksync transaction',
                )

            if tx_type == ZKSyncLiteTXType.DEPOSIT:
                asset_key = 'tokenId'
            elif tx_type == ZKSyncLiteTXType.CHANGEPUBKEY:
                asset_key = 'feeToken'
                from_address = deserialize_evm_address(entry['op']['account'])
            elif tx_type == ZKSyncLiteTXType.FORCEDEXIT:
                asset_key = 'token'
                from_address = deserialize_evm_address(entry['op']['target'])
            else:  # transfer/withdraw
                asset_key = 'token'

            asset = self._get_token_by_id(entry['op'][asset_key])
            if asset is None:
                log.error(
                    f'Skipping zksync lite transaction {entry} with unknown token id {entry["op"][asset_key]}',  # noqa: E501
                )
                return None

            to_address = None
            amount = ZERO
            if tx_type not in (ZKSyncLiteTXType.CHANGEPUBKEY, ZKSyncLiteTXType.FORCEDEXIT):
                from_address = deserialize_evm_address(entry['op']['from'])
                to_address = deserialize_evm_address(entry['op']['to'])
                amount_raw = deserialize_int_from_str(
                    symbol=entry['op']['amount'],
                    location='zksync transaction',
                )
                amount = asset_normalized_value(amount_raw, asset)

        except (DeserializationError, KeyError) as e:
            error = str(e)
            if isinstance(e, KeyError):
                error = f'missing key {e!s}'

            log.error(
                f'Could not deserialize zksync lite transaction {entry} due to {error}',
            )
        else:
            return ZKSyncLiteTransaction(
                tx_hash=tx_hash,
                tx_type=tx_type,
                timestamp=timestamp,
                block_number=block_number,
                from_address=from_address,
                to_address=to_address,
                asset=asset,
                amount=amount,
                fee=Fee(asset_normalized_value(fee_raw, asset)) if fee_raw else None,
            )

        return None

    def _query_zksync_api_transactions(
            self,
            address: ChecksumEvmAddress,
            from_hash: str,
            direction: Literal['older', 'newer'],
    ) -> Iterator[list[ZKSyncLiteTransaction]]:
        transactions = []
        last_tx_hash = ''
        while True:
            options = {'from': from_hash, 'limit': ZKSYNCLITE_MAX_LIMIT, 'direction': direction}
            response = self._query_api(
                url=f'accounts/{address}/transactions',
                options=options,
            )
            result = response.get('list', None)
            if result is None:
                msg = 'Unexpected zksync transactions response. Could not find result in the response.'  # noqa: E501
                log.error(f'{msg} Response: {response}')
                raise RemoteError(msg)

            for idx, entry in enumerate(result):
                if idx == 0 and entry['txHash'] == last_tx_hash:
                    continue  # at pagination first tx is last query's last

                tx = self._deserialize_zksync_transaction(entry)
                if tx:
                    transactions.append(tx)
                    last_tx_hash = entry['txHash']

            yield transactions
            if len(result) < ZKSYNCLITE_MAX_LIMIT:
                break  # no need to paginate further

            from_hash = result[-1]['txHash']
            transactions = []

    def _add_zksynctxs_db(
            self,
            write_cursor: 'DBCursor',
            transactions: Iterable[ZKSyncLiteTransaction],
    ) -> None:
        tuples = [x.serialize_for_db() for x in transactions]
        query = """INSERT INTO zksynclite_transactions(tx_hash, type, timestamp, block_number,
        from_address, to_address, token_identifier, amount, fee)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.database.write_tuples(
            write_cursor=write_cursor,
            tuple_type='zksynclite_transaction',
            query=query,
            tuples=tuples,
        )

    def _get_undecoded_transactions(self) -> list[ZKSyncLiteTransaction]:
        """Gets any zksynclite undecoded transactions from the DB"""
        transactions = []
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT tx_hash, type, timestamp, block_number, from_address, to_address, '
                'token_identifier, amount, fee FROM zksynclite_transactions '
                'WHERE is_decoded=?', (0,),
            )
            for entry in cursor:
                try:
                    transactions.append(ZKSyncLiteTransaction.deserialize_from_db(entry))
                except (DeserializationError, UnknownAsset) as e:
                    log.error(
                        f'Could not deserialize zksync lite transaction {entry} from the DB due to {e!s}',  # noqa: E501
                    )
                continue

        return transactions

    def fetch_transactions(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Fetch all zksync transactions for an address in the given time range and save in DB"""
        location = f'zksynctxs_{address}'
        min_tx_hash = max_tx_hash = 'latest'
        min_timestamp = start_ts
        max_timestamp = end_ts
        with self.database.conn.read_ctx() as cursor:
            queried_range = self.database.get_used_query_range(cursor, location)

            cursor.execute('SELECT tx_hash, min(timestamp) from zksynclite_transactions;')
            if (result := cursor.fetchone()) is not None and result[0] is not None:
                min_tx_hash = '0x' + result[0].hex()
                min_timestamp = result[1]

            cursor.execute('SELECT tx_hash, max(timestamp) from zksynclite_transactions;')
            result_hash = cursor.fetchone()[0]

            if result is not None and (result_hash := cursor.fetchone()) is not None and result_hash[0] is not None:  # noqa: E501
                max_tx_hash = '0x' + result_hash[0].hex()
                max_timestamp = result[1]

        try:
            if queried_range is None:  # no previous query, just go backwards
                self._query_and_save_transactions_for_range(
                    address=address,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    from_hash='latest',
                    direction='older',
                )
            elif queried_range[0] != 0:  # somehow oldest range is not 0, so go to zero
                self._query_and_save_transactions_for_range(
                    address=address,
                    start_ts=start_ts,
                    end_ts=min_timestamp,
                    from_hash=min_tx_hash,
                    direction='older',
                )
                self._query_and_save_transactions_for_range(
                    address=address,
                    start_ts=max_timestamp,
                    end_ts=end_ts,
                    from_hash=max_tx_hash,
                    direction='newer',
                )
            else:  # get the new transactions
                self._query_and_save_transactions_for_range(
                    address=address,
                    start_ts=max_timestamp,
                    end_ts=end_ts,
                    from_hash=max_tx_hash,
                    direction='newer',
                )
        except RemoteError as e:
            log.error(
                f'Got error "{e!s}" while querying zksync lite transactions '
                f'from zksync api. Transactions not added to the DB. '
                f'{address=}, {start_ts=}, {end_ts=} ',
            )

    def get_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """May raise:
           - RemoteError if there is a problem contacting the API
        """
        balances: defaultdict[ChecksumEvmAddress, dict[Asset, Balance]] = defaultdict(dict)
        for address in addresses:
            result = self._query_api(url=f'accounts/{address}')
            try:
                for symbol, raw_amount_str in result['finalized']['balances'].items():
                    if (asset := self._get_token_by_symbol(symbol)) is None:
                        log.error(f'Could not find asset for symbol {symbol} in zksync mapping')
                        continue

                    raw_amount = deserialize_int_from_str(
                        symbol=raw_amount_str,
                        location='zksync balances',
                    )
                    amount = asset_normalized_value(raw_amount, asset)
                    try:
                        usd_price = Inquirer.find_usd_price(asset)
                    except RemoteError as e:
                        log.error(
                            f'Error processing zksync lite balance entry due to inability to '
                            f'query USD price: {e!s}. Skipping balance entry',
                        )
                        continue

                    balances[address][asset] = Balance(amount, usd_price)

            except (KeyError, DeserializationError, RemoteError) as e:
                msg = str(e)  # Catching RemoteError here too due to self._get_token_by_symbol
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.error(f'Failed to query zksync balances for {address} due to {msg}')

        return dict(balances)

    def decode_undecoded_transactions(self) -> int:
        transactions = self._get_undecoded_transactions()
        decoded_num = 0
        dbevents = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            tracked_addresses = self.database.get_blockchain_accounts(cursor).zksync_lite

        for transaction in transactions:
            target = None
            tracked_from = transaction.from_address in tracked_addresses
            tracked_to = transaction.to_address in tracked_addresses
            match transaction.tx_type:
                case ZKSyncLiteTXType.DEPOSIT:

                    # This is a deposit from L1 to ZKSync Lite. from is in L1. to is in L2
                    if not tracked_to:
                        continue  # no need to track. Receiver in zksync lite is not ours
                    event_type = HistoryEventType.WITHDRAWAL
                    event_subtype = HistoryEventSubType.BRIDGE
                    suffix = ''
                    if transaction.from_address != transaction.to_address:
                        suffix = f' address {transaction.to_address}'
                    notes = f'Bridge {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} from Ethereum to ZKSync Lite{suffix}'  # noqa: E501
                    location_label = transaction.to_address
                case ZKSyncLiteTXType.WITHDRAW:
                    # This is a withdrawal from ZKSync lite to L1. from is in L2 to is in L1
                    if not tracked_from:
                        continue  # no need to track. Sender in zksync lite is not ours
                    event_type = HistoryEventType.DEPOSIT
                    event_subtype = HistoryEventSubType.BRIDGE
                    suffix = ''
                    target = transaction.to_address
                    if transaction.from_address != transaction.to_address:
                        suffix = f' address {transaction.to_address}'
                    notes = f'Bridge {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} from ZKSync Lite to Ethereum{suffix}'  # noqa: E501
                    location_label = transaction.from_address

                case ZKSyncLiteTXType.TRANSFER:
                    if not tracked_from and not tracked_to:
                        continue
                    # Similar to chain/evm/decoding/base.py. Can abstract somehow?
                    if tracked_from and tracked_to:
                        event_type = HistoryEventType.TRANSFER
                        event_subtype = HistoryEventSubType.NONE
                        location_label = transaction.from_address
                        target = transaction.to_address
                        verb = 'Transfer'
                        preposition = 'to'
                    elif tracked_from:
                        event_type = HistoryEventType.SPEND
                        event_subtype = HistoryEventSubType.NONE
                        location_label = transaction.from_address
                        target = transaction.to_address
                        verb = 'Send'
                        preposition = 'to'
                    else:  # can only be tracked_to
                        event_type = HistoryEventType.RECEIVE
                        event_subtype = HistoryEventSubType.NONE
                        location_label = transaction.to_address
                        target = transaction.from_address
                        verb = 'Receive'
                        preposition = 'from'

                    # TODO: I wanted to use HistoryEvent here since this is not a full
                    # EVM event and does not have a chain ID or product or counterparties.
                    # But HistoryEvents do not have "to" field for send/transfers. Without this
                    # we could not analyze where did a transfer go. So we use EvmEvent here.
                    # Perhaps we should create a new extension to HistoryEvent that
                    # simply adds a "to" field. As this will definitely be needed somewhere.
                    notes = f'{verb} {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} {preposition} {target}'  # noqa: E501

                case ZKSyncLiteTXType.FORCEDEXIT:
                    continue  # TODO
                case ZKSyncLiteTXType.CHANGEPUBKEY:
                    event_type = HistoryEventType.SPEND
                    event_subtype = HistoryEventSubType.FEE
                    if transaction.fee is None:
                        log.error(f'Found zksync lite ChangePubKey transaction {transaction} with no fee field. Skipping')  # noqa: E501
                        continue

                    transaction.amount = transaction.fee
                    transaction.fee = None  # to not double count fee with 2 events
                    notes = f'Spend {transaction.amount} ETH to ChangePubKey'
                    location_label = transaction.from_address
                    transaction.fee = None  # to not double count fee with 2 events

            events = []
            events.append(EvmEvent(
                event_identifier=f'zkl{transaction.tx_hash.hex()}',
                tx_hash=transaction.tx_hash,
                sequence_index=0,
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.ZKSYNC_LITE,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=transaction.asset,
                balance=Balance(amount=transaction.amount),
                location_label=location_label,
                address=target,
                notes=notes,
            ))
            if transaction.fee is not None and event_type != HistoryEventType.RECEIVE:  # sender pays  # noqa: E501
                notes = f'Bridging fee of {transaction.fee} {transaction.asset.resolve_to_asset_with_symbol().symbol}'  # noqa: E501
                if event_type in (HistoryEventType.SPEND, HistoryEventType.TRANSFER):
                    notes = f'Transfer fee of {transaction.fee} {transaction.asset.resolve_to_asset_with_symbol().symbol}'  # noqa: E501
                events.append(EvmEvent(
                    event_identifier=f'zkl{transaction.tx_hash.hex()}',
                    tx_hash=transaction.tx_hash,
                    sequence_index=1,
                    timestamp=ts_sec_to_ms(transaction.timestamp),
                    location=Location.ZKSYNC_LITE,
                    event_type=event_type,
                    # Combinations that can come up are:
                    # DEPOSIT/FEE, WITHDRAWAl/FEE, SPEND/FEE, TRANSFER/FEE
                    event_subtype=HistoryEventSubType.FEE,
                    asset=transaction.asset,
                    balance=Balance(amount=transaction.fee),
                    location_label=location_label,
                    address=target,
                    notes=notes,
                ))

            # save it in the DB and mark the zksync lite transaction as decoded
            with self.database.user_write() as write_cursor:
                for event in events:
                    decoded_num += 1
                    dbevents.add_history_event(write_cursor, event)

                write_cursor.execute(
                    'UPDATE zksynclite_transactions SET is_decoded=? WHERE tx_hash=?',
                    (1, transaction.tx_hash),
                )

        return decoded_num

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
