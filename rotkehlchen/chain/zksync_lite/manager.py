import logging
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import gevent
import requests
from pysqlcipher3.dbapi2 import IntegrityError

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.manager import ChainManagerWithTransactions
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int_from_str
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmlikeChain,
    EVMTxHash,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

from .constants import ZKL_IDENTIFIER, ZKSYNCLITE_MAX_LIMIT
from .structures import ZKSyncLiteSwapData, ZKSyncLiteTransaction, ZKSyncLiteTXType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZksyncLiteManager(ChainManagerWithTransactions[ChecksumEvmAddress]):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
    ) -> None:
        self.database = database
        self.session = create_session()
        set_user_agent(self.session)
        self.id_to_token: dict[int, CryptoAsset] = {}
        self.symbol_to_token: dict[str, CryptoAsset] = {}
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.ethereum_inquirer = ethereum_inquirer

    def _get_token_and_amount_by_id_or_log(
            self,
            entry: dict,
            asset_key: str,
            amount_key: str | None = 'amount',
    ) -> tuple[CryptoAsset, FVal] | None:
        """Helper function. May raise KeyError"""
        if (asset := self._get_token_by_id(entry['op'][asset_key])) is None:
            log.error(  # also happens for all NFT transfers -- since we ignore nfts in lite
                f'Skipping zksync lite transaction {entry} with unknown token id {entry["op"][asset_key]}',  # noqa: E501
            )
            return None

        amount = ZERO
        if amount_key:
            amount_raw = deserialize_int_from_str(
                symbol=entry['op'][amount_key],
                location='zksync transaction',
            )
            amount = asset_normalized_value(amount_raw, asset)

        return asset, amount

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
        timeout = timeout or CachedSettings().get_timeout_tuple()
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
                backoff *= 2
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

    def _query_and_save_transactions_from_hash(
            self,
            address: ChecksumEvmAddress,
            from_hash: str,
            direction: Literal['older', 'newer'],
    ) -> None:
        """Query and save transactions before or since the transaction specified with from_hash."""
        input_transactions: set[ZKSyncLiteTransaction] = set()
        for new_transactions in self._query_zksync_api_transactions(
                address=address,
                from_hash=from_hash,
                direction=direction,
        ):
            if (
                from_hash != 'latest' and
                len(new_transactions) != 0 and
                new_transactions[0].tx_hash.hex() == from_hash
            ):
                # When there are already transactions in the database, and new ones are queried
                # using from_hash, the API includes the from_hash transaction in its response,
                # so it must be removed to avoid adding duplicate entries to the database.
                new_transactions.pop(0)

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
                                encounter=TokenEncounterInfo(description='Querying zksync lite tokens mapping'),  # noqa: E501
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

    def _deserialize_zksync_transaction(
            self,
            entry: dict[str, Any],
            concerning_address: ChecksumEvmAddress,
    ) -> ZKSyncLiteTransaction | None:
        from_address = None
        to_address = None
        swap_data = None
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
            amount = ZERO
            if fee_str is not None:
                fee_raw = deserialize_int_from_str(
                    symbol=fee_str,
                    location='zksync transaction',
                )

            if tx_type == ZKSyncLiteTXType.DEPOSIT:
                from_address = deserialize_evm_address(entry['op']['from'])
                to_address = deserialize_evm_address(entry['op']['to'])
                if (asset_amount := self._get_token_and_amount_by_id_or_log(entry, 'tokenId')) is None:  # noqa: E501
                    return None
                asset, amount = asset_amount

            elif tx_type == ZKSyncLiteTXType.CHANGEPUBKEY:
                from_address = deserialize_evm_address(entry['op']['account'])
                if (asset_amount := self._get_token_and_amount_by_id_or_log(
                        entry=entry,
                        asset_key='feeToken',
                        amount_key='fee',
                )) is None:
                    return None
                asset = asset_amount[0]  # there is no amount. Just fee

            elif tx_type == ZKSyncLiteTXType.FORCEDEXIT:
                from_address = concerning_address  # like FULLEXIT the amount is missing in the API
                to_address = deserialize_evm_address(entry['op']['target'])
                if (asset_amount := self._get_token_and_amount_by_id_or_log(
                        entry=entry,
                        asset_key='token',
                        amount_key=None,
                )) is None:
                    return None
                asset, amount = asset_amount

            elif tx_type == ZKSyncLiteTXType.FULLEXIT:
                from_address = concerning_address
                to_address = concerning_address
                # for some reason the transaction hash for full exit is in op and their
                # one under entry is not corresponding to anything in zkscan.
                # also amount is missing
                tx_hash = deserialize_evm_tx_hash(entry['op']['ethHash'])
                if (asset_amount := self._get_token_and_amount_by_id_or_log(
                        entry=entry,
                        asset_key='tokenId',
                        amount_key=None,
                )) is None:
                    return None
                asset, amount = asset_amount

            elif tx_type == ZKSyncLiteTXType.SWAP:
                from_address = concerning_address
                to_address = concerning_address
                if (asset_amount := self._get_token_and_amount_by_id_or_log(
                        entry=entry,
                        asset_key='feeToken',
                        amount_key='fee',
                )) is None:
                    return None
                asset, amount = asset_amount  # for swaps this is the fee/fee token

                swap_asset_data = []
                for idx in (0, 1):
                    if (swap_asset := self._get_token_by_id(entry['op']['orders'][idx]['tokenSell'])) is None:  # noqa: E501
                        log.error(f'Could not deserialize zksync lite swap entry sell token at idx {idx} of {entry}')  # noqa: E501
                        return None

                    amount_raw = deserialize_int_from_str(
                        symbol=entry['op']['orders'][idx]['amount'],
                        location='zksync swap transaction',
                    )
                    swap_amount = asset_normalized_value(amount_raw, swap_asset)
                    swap_asset_data.append((swap_asset, swap_amount))

                swap_data = ZKSyncLiteSwapData(
                    from_asset=swap_asset_data[0][0],
                    from_amount=swap_asset_data[0][1],
                    to_asset=swap_asset_data[1][0],
                    to_amount=swap_asset_data[1][1],
                )

            else:  # transfer/withdraw
                from_address = deserialize_evm_address(entry['op']['from'])
                to_address = deserialize_evm_address(entry['op']['to'])
                if (asset_amount := self._get_token_and_amount_by_id_or_log(entry, 'token')) is None:  # noqa: E501
                    return None
                asset, amount = asset_amount

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
                fee=asset_normalized_value(fee_raw, asset) if fee_raw else None,
                swap_data=swap_data,
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

                tx = self._deserialize_zksync_transaction(entry, concerning_address=address)
                if tx:
                    transactions.append(tx)
                    last_tx_hash = entry['txHash']

            yield transactions
            if len(result) < ZKSYNCLITE_MAX_LIMIT:
                break  # no need to paginate further

            from_hash = result[-1]['txHash']
            transactions = []

    def query_single_transaction(
            self,
            tx_hash: EVMTxHash,
            concerning_address: ChecksumEvmAddress,
    ) -> ZKSyncLiteTransaction | None:
        """Queries zksync lite api for a single transaction, saves it
        in the DB and returns it if existing

        In case of error returns None and logs the error.
        """
        try:
            response = self._query_api(url=f'transactions/{tx_hash.hex()}/data')
        except RemoteError as e:
            log.error(f'Could not find {tx_hash.hex()} transaction from zksync lite api due to {e!s}')  # noqa: E501
            return None

        if (tx_entry := response.get('tx', None)) is None:
            log.error(f'Could not find {tx_hash.hex()} transaction from zksync lite api. Response: {response}')  # noqa: E501
            return None

        if (tx := self._deserialize_zksync_transaction(entry=tx_entry, concerning_address=concerning_address)) is None:  # noqa: E501
            log.error(f'Could not deserialize {tx_hash.hex()} transaction. Got None')
            return None

        with self.database.user_write() as write_cursor:
            self._add_zksynctxs_db(write_cursor=write_cursor, transactions=[tx])

        return tx

    def _add_zksynctxs_db(
            self,
            write_cursor: 'DBCursor',
            transactions: Iterable[ZKSyncLiteTransaction],
    ) -> None:
        for transaction in transactions:
            try:
                write_cursor.execute(
                    'INSERT INTO zksynclite_transactions(tx_hash, type, timestamp, block_number, '
                    'from_address, to_address, asset, amount, fee) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING identifier',
                    transaction.serialize_for_db(),
                )
                if transaction.tx_type == ZKSyncLiteTXType.SWAP:
                    identifier = write_cursor.fetchone()[0]
                    write_cursor.execute(
                        'INSERT INTO zksynclite_swaps(tx_id, from_asset, from_amount, '
                        'to_asset, to_amount) VALUES(?, ?, ?, ?, ?)',
                        transaction.swap_data.serialize_for_db(identifier),  # type: ignore  # swap_data exists for swap
                    )
            except IntegrityError as e:
                log.error(f'Did not add zksync transaction {transaction} to the DB due to {e!s}')
                continue

    def get_db_transactions(
            self,
            queryfilter: str = '',
            bindings: tuple = (),
    ) -> list[ZKSyncLiteTransaction]:
        """Gets any zksynclite transactions from the DB depending on the given filter"""
        transactions = []
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                f'SELECT tx_id, from_asset, from_amount, to_asset, to_amount '
                f'FROM zksynclite_swaps WHERE tx_id IN '
                f'(SELECT identifier FROM zksynclite_transactions{queryfilter})',
                bindings,
            )
            swap_data = {row[0]: row[1:] for row in cursor}

            cursor.execute(
                f'SELECT identifier, tx_hash, type, timestamp, block_number, from_address, '
                f'to_address, asset, amount, fee FROM zksynclite_transactions{queryfilter}',
                bindings,
            )
            for entry in cursor:
                swap_result = None
                try:
                    tx = ZKSyncLiteTransaction.deserialize_from_db(entry[1:])
                    if tx.tx_type == ZKSyncLiteTXType.SWAP:
                        if (tx_data := swap_data.get(entry[0])) is None:
                            log.error(f'Could not deserialize zksync lite transaction from the DB due to not finding swap data for tx_id: {entry[0]}')  # noqa: E501
                            continue

                        tx.swap_data = ZKSyncLiteSwapData.deserialize_from_db(tx_data)

                    transactions.append(tx)
                except (DeserializationError, UnknownAsset) as e:
                    log.error(
                        f'Could not deserialize zksync lite transaction {entry} with {swap_result=} from the DB due to {e!s}',  # noqa: E501
                    )
                continue

        return transactions

    def fetch_transactions(
            self,
            address: ChecksumEvmAddress,
    ) -> None:
        """Fetch zksync transactions for an address and save in DB.
        Get only new transactions if there are existing ones, otherwise get all transactions.
        """
        max_tx_hash = None
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('SELECT tx_hash, max(timestamp) from zksynclite_transactions;')
            if (max_result := cursor.fetchone()) is not None and max_result[0] is not None:
                max_tx_hash = '0x' + max_result[0].hex()

        try:
            if max_tx_hash is None:  # no existing entries, query all
                self._query_and_save_transactions_from_hash(
                    address=address,
                    from_hash='latest',
                    direction='older',
                )
            else:  # get the new transactions
                self._query_and_save_transactions_from_hash(
                    address=address,
                    from_hash=max_tx_hash,
                    direction='newer',
                )
        except RemoteError as e:
            log.error(
                f'Got error "{e!s}" while querying zksync lite transactions '
                f'from zksync api. Transactions not added to the DB. {address=}',
            )

    def query_transactions(
            self,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        for address in addresses:
            self.fetch_transactions(address=address)

    def query_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, BalanceSheet]:
        """Get ZKSync Lite balances

        May raise:
        - RemoteError
        """
        balances: defaultdict[ChecksumEvmAddress, BalanceSheet] = defaultdict(BalanceSheet)
        for address in addresses:
            result = self._query_api(url=f'accounts/{address}')
            if (finalized_result := result.get('finalized', None)) is None:
                balances[address] = BalanceSheet()
                continue

            try:
                for symbol, raw_amount_str in finalized_result.get('balances', {}).items():
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

                    balances[address].assets[asset][DEFAULT_BALANCE_LABEL] = Balance(
                        amount=amount,
                        usd_value=usd_price * amount,
                    )

            except (KeyError, DeserializationError, RemoteError) as e:
                msg = str(e)  # Catching RemoteError here too due to self._get_token_by_symbol
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.error(f'Failed to query zksync balances for {address} due to {msg}')

        return dict(balances)

    def decode_transaction(
            self,
            transaction: ZKSyncLiteTransaction,
            tracked_addresses: Sequence[ChecksumEvmAddress],
    ) -> None:
        """Decodes a zksync lite transaction, creating any events that may be needed for it"""
        target = None
        tracked_from = transaction.from_address in tracked_addresses
        tracked_to = transaction.to_address in tracked_addresses
        event_identifier = ZKL_IDENTIFIER.format(tx_hash=transaction.tx_hash.hex())
        events = []
        event_data: list[tuple[int, HistoryEventType, HistoryEventSubType, Asset, FVal, ChecksumEvmAddress, ChecksumEvmAddress | None, str]] = []  # noqa: E501
        match transaction.tx_type:
            case ZKSyncLiteTXType.DEPOSIT:

                # This is a deposit from L1 to ZKSync Lite. from is in L1. to is in L2
                if tracked_to:  # decode only if receiver in zksync lite is ours
                    suffix = ''
                    if transaction.from_address != transaction.to_address:
                        suffix = f' address {transaction.to_address}'
                    notes = f'Bridge {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} from Ethereum to ZKSync Lite{suffix}'  # noqa: E501
                    event_data.append((
                        0,
                        HistoryEventType.WITHDRAWAL,
                        HistoryEventSubType.BRIDGE,
                        transaction.asset,
                        transaction.amount,
                        transaction.to_address,  # type:ignore [arg-type]  # to_address should exist here
                        None,
                        notes,
                    ))

            case ZKSyncLiteTXType.WITHDRAW:
                # This is a withdrawal from ZKSync lite to L1. from is in L2 to is in L1
                if tracked_from:  # decode only if sender in zksync lite is ours
                    suffix = ''
                    if transaction.from_address != transaction.to_address:
                        suffix = f' address {transaction.to_address}'
                    notes = f'Bridge {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} from ZKSync Lite to Ethereum{suffix}'  # noqa: E501
                    event_data.append((
                        0,
                        HistoryEventType.DEPOSIT,
                        HistoryEventSubType.BRIDGE,
                        transaction.asset,
                        transaction.amount,
                        transaction.from_address,
                        transaction.to_address,
                        notes,
                    ))

            case ZKSyncLiteTXType.TRANSFER:
                # Similar to chain/evm/decoding/base.py. Can abstract somehow?
                if tracked_from and tracked_to:
                    event_data.append((
                        0,
                        HistoryEventType.TRANSFER,
                        HistoryEventSubType.NONE,
                        transaction.asset,
                        transaction.amount,
                        transaction.from_address,
                        transaction.to_address,
                        f'Transfer {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} to {transaction.to_address}',  # noqa: E501
                    ))
                elif tracked_from:
                    event_data.append((
                        0,
                        HistoryEventType.SPEND,
                        HistoryEventSubType.NONE,
                        transaction.asset,
                        transaction.amount,
                        transaction.from_address,
                        transaction.to_address,
                        f'Send {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} to {transaction.to_address}',  # noqa: E501
                    ))
                elif tracked_to:
                    event_data.append((  # type: ignore[arg-type] # to_address exists here
                        0,
                        HistoryEventType.RECEIVE,
                        HistoryEventSubType.NONE,
                        transaction.asset,
                        transaction.amount,
                        transaction.to_address,
                        transaction.from_address,
                        f'Receive {transaction.amount} {transaction.asset.resolve_to_asset_with_symbol().symbol} from {transaction.from_address}',  # noqa: E501
                    ))

            case ZKSyncLiteTXType.FULLEXIT | ZKSyncLiteTXType.FORCEDEXIT:
                event_data.append((
                    0,
                    HistoryEventType.INFORMATIONAL,
                    HistoryEventSubType.NONE,
                    transaction.asset,
                    transaction.amount,
                    transaction.from_address,
                    transaction.to_address,
                    f'{"Full" if transaction.tx_type == ZKSyncLiteTXType.FULLEXIT else "Forced"} exit to Ethereum{"" if transaction.from_address == transaction.to_address else f" address {transaction.to_address}"}',  # noqa: E501
                ))

            case ZKSyncLiteTXType.CHANGEPUBKEY:
                if transaction.fee:
                    event_type = HistoryEventType.SPEND
                    event_subtype = HistoryEventSubType.FEE
                    transaction.amount = transaction.fee
                    transaction.fee = None  # to not double count fee with 2 events
                    notes = f'Spend {transaction.amount} ETH to ChangePubKey'
                    location_label = transaction.from_address
                    transaction.fee = None  # to not double count fee with 2 events
                    event_data.append((
                        0,
                        HistoryEventType.SPEND,
                        HistoryEventSubType.FEE,
                        transaction.asset,
                        transaction.amount,
                        transaction.from_address,
                        transaction.to_address,
                        f'Spend {transaction.amount} ETH to ChangePubKey',
                    ))

                else:
                    log.error(f'Found zksync lite ChangePubKey transaction {transaction} with no fee field. Skipping')  # noqa: E501

            case ZKSyncLiteTXType.SWAP:
                assert transaction.swap_data, 'Swap data exist for SWAP type'
                from_asset = transaction.swap_data.from_asset.resolve_to_asset_with_symbol()
                to_asset = transaction.swap_data.to_asset.resolve_to_asset_with_symbol()
                event_data.extend([(
                    0,
                    HistoryEventType.TRADE,
                    HistoryEventSubType.SPEND,
                    from_asset,
                    transaction.swap_data.from_amount,
                    transaction.from_address,
                    transaction.to_address,
                    f'Swap {transaction.swap_data.from_amount} {from_asset.symbol} via ZKSync Lite',  # noqa: E501
                ), (
                    1,
                    HistoryEventType.TRADE,
                    HistoryEventSubType.RECEIVE,
                    to_asset,
                    transaction.swap_data.to_amount,
                    transaction.from_address,
                    transaction.to_address,
                    f'Receive {transaction.swap_data.to_amount} {to_asset.symbol} as the result of a swap via ZKSync Lite',  # noqa: E501
                )])

        for sequence_index, event_type, event_subtype, asset, amount, location_label, target, notes in event_data:  # noqa: E501
            events.append(EvmEvent(
                event_identifier=event_identifier,
                tx_ref=transaction.tx_hash,
                sequence_index=sequence_index,
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.ZKSYNC_LITE,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=amount,
                location_label=location_label,
                address=target,
                notes=notes,
            ))

        if transaction.fee is not None and len(events) != 0 and events[0].event_type != HistoryEventType.RECEIVE:  # sender pays  # noqa: E501
            if events[0].event_type in (HistoryEventType.SPEND, HistoryEventType.TRANSFER):
                fee_type = 'Transfer'
            elif events[0].event_type == HistoryEventType.TRADE:
                fee_type = 'Swap'
            else:
                fee_type = 'Bridging'

            events.append(EvmEvent(
                event_identifier=event_identifier,
                tx_ref=transaction.tx_hash,
                sequence_index=events[-1].sequence_index + 1,
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.ZKSYNC_LITE,
                event_type=events[0].event_type,
                # Combinations that can come up are:
                # DEPOSIT/FEE, WITHDRAWAl/FEE, SPEND/FEE, TRANSFER/FEE
                event_subtype=HistoryEventSubType.FEE,
                asset=transaction.asset,
                amount=transaction.fee,
                location_label=events[0].location_label,
                address=target,
                notes=f'{fee_type} fee of {transaction.fee} {transaction.asset.resolve_to_asset_with_symbol().symbol}',  # noqa: E501,
            ))

        # save it in the DB and mark the zksync lite transaction as decoded
        dbevents = DBHistoryEvents(self.database)
        with self.database.user_write() as write_cursor:
            for event in events:
                dbevents.add_history_event(write_cursor, event)

            write_cursor.execute(
                'UPDATE zksynclite_transactions SET is_decoded=? WHERE tx_hash=?',
                (1, transaction.tx_hash),
            )

    def decode_undecoded_transactions(
            self,
            force_redecode: bool,
            send_ws_notifications: bool = False,
    ) -> int:
        """Decodes undecoded zksync lite transactions. If force redecode is True
        then all transactions are redecoded. If send_ws_notifications is True then the decoding
        progress is broadcasted via websocket messages.
        Returns the number of decoded transactions (not events in transactions)
        """
        queryfilter, bindings = '', ()
        if not force_redecode:
            queryfilter, bindings = ' WHERE is_decoded=?', (0,)  # type: ignore

        transactions = self.get_db_transactions(queryfilter, bindings)
        with self.database.conn.read_ctx() as cursor:
            tracked_addresses = self.database.get_blockchain_accounts(cursor).zksync_lite

        total_transactions = len(transactions)
        for tx_index, transaction in enumerate(transactions):
            with self.database.user_write() as write_cursor:  # delete old tx events
                write_cursor.execute(
                    'DELETE FROM history_events WHERE event_identifier=?',
                    (ZKL_IDENTIFIER.format(tx_hash=transaction.tx_hash.hex()),),
                )

            self.decode_transaction(transaction, tracked_addresses)

            if send_ws_notifications and tx_index % 10 == 0:
                self.database.msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'chain': EvmlikeChain.ZKSYNC_LITE,
                        'subtype': str(ProgressUpdateSubType.UNDECODED_TRANSACTIONS),
                        'total': total_transactions,
                        'processed': tx_index,
                    },
                )

        if send_ws_notifications:
            self.database.msg_aggregator.add_message(
                message_type=WSMessageType.PROGRESS_UPDATES,
                data={
                    'chain': EvmlikeChain.ZKSYNC_LITE,
                    'subtype': str(ProgressUpdateSubType.UNDECODED_TRANSACTIONS),
                    'total': total_transactions,
                    'processed': total_transactions,
                },
            )

        return len(transactions)
