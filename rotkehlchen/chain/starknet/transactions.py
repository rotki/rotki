import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.websockets.typedefs import (
    TransactionStatusStep,
    TransactionStatusSubType,
    WSMessageType,
)
from rotkehlchen.db.filtering import StarknetTransactionsFilterQuery
from rotkehlchen.db.starknettx import DBStarknetTx
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import ts_now

from .constants import ETH_TOKEN_ADDRESS, STRK_TOKEN_ADDRESS
from .types import StarknetTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.starknet.node_inquirer import StarknetInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.voyager import Voyager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

RPC_TX_BATCH_SIZE: Final = 10
# starknet_keccak("Transfer") — Transfer event selector on Starknet
TRANSFER_EVENT_SELECTOR: Final = '0x99cd8bde557814842a3121e8ddfd433a539b8c9f14bf31ebf108d12e6196e9'


class StarknetTransactions:

    def __init__(
            self,
            node_inquirer: 'StarknetInquirer',
            database: 'DBHandler',
            voyager: 'Voyager',
    ) -> None:
        self.node_inquirer = node_inquirer
        self.database = database
        self.voyager = voyager
        self.dbtx = DBStarknetTx(database=database)

    def get_or_create_transaction(
            self,
            tx_hash: str,
            relevant_address: StarknetAddress | None = None,
    ) -> StarknetTransaction:
        """Gets a transaction from the DB or fetches it via Voyager (with RPC fallback).

        May raise:
        - RemoteError if there is a problem with querying the external service.
        """
        with self.database.conn.read_ctx() as cursor:
            if len(txs := self.dbtx.get_transactions(
                cursor=cursor,
                filter_=StarknetTransactionsFilterQuery.make(transaction_hash=tx_hash),
            )) == 1:
                return txs[0]

        try:
            tx = self.voyager.get_transaction_object(tx_hash)
        except (MissingAPIKey, RemoteError) as e:
            log.debug(f'Voyager unavailable for tx {tx_hash}: {e}. Falling back to RPC.')
            tx = self.node_inquirer.get_transaction_for_hash(tx_hash=tx_hash)

        with self.database.conn.write_ctx() as write_cursor:
            self.dbtx.add_transactions(
                write_cursor=write_cursor,
                starknet_transactions=[tx],
                relevant_address=relevant_address,
            )

        return tx

    def _send_tx_status_message(
            self,
            address: StarknetAddress,
            period: tuple[Timestamp, Timestamp],
            status: TransactionStatusStep,
    ) -> None:
        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.TRANSACTION_STATUS,
            data={
                'address': address,
                'chain': SupportedBlockchain.STARKNET.value,
                'subtype': str(TransactionStatusSubType.STARKNET),
                'period': period,
                'status': str(status),
            },
        )

    def query_transactions_for_address(self, address: StarknetAddress) -> None:
        """Query the transactions for the given address and save them to the DB.

        Note: Starknet RPC does not natively support querying transactions by address.
        This method uses starknet_getEvents to discover transaction hashes, then
        fetches full transaction data for each.

        May raise RemoteError if there is a problem with querying the external service.
        """
        start_ts, end_ts = Timestamp(0), ts_now()
        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )

        try:
            all_txs = self.voyager.get_transactions_for_address(address)
            log.debug(f'Voyager fetched {len(all_txs)} transactions for Starknet address {address}')  # noqa: E501
            # Filter out existing hashes
            with self.database.conn.read_ctx() as cursor:
                existing = self.dbtx.get_existing_tx_hashes(
                    cursor=cursor,
                    tx_hashes=[tx.transaction_hash for tx in all_txs],
                )
            new_txs = [tx for tx in all_txs if tx.transaction_hash not in existing]
            if new_txs:
                with self.database.conn.write_ctx() as write_cursor:
                    self.dbtx.add_transactions(
                        write_cursor=write_cursor,
                        starknet_transactions=new_txs,
                        relevant_address=address,
                    )
        except (MissingAPIKey, RemoteError) as e:
            log.debug(f'Voyager unavailable for {address}: {e}. Falling back to RPC.')
            self._fetch_transactions_via_rpc(address=address, start_ts=start_ts, end_ts=end_ts)

        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )

    def _fetch_transactions_via_rpc(
            self,
            address: StarknetAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Fallback: discover tx hashes via RPC events, then fetch full tx data via RPC."""
        try:
            tx_hashes = self._get_tx_hashes_for_address(address)
        except RemoteError as e:
            log.error(f'Failed to query Starknet transaction hashes for {address}: {e}')
            self._send_tx_status_message(
                address=address,
                period=(start_ts, end_ts),
                status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
            )
            return

        with self.database.conn.read_ctx() as cursor:
            existing = self.dbtx.get_existing_tx_hashes(cursor=cursor, tx_hashes=tx_hashes)

        new_hashes = [h for h in tx_hashes if h not in existing]
        for i in range(0, len(new_hashes), RPC_TX_BATCH_SIZE):
            batch = new_hashes[i:i + RPC_TX_BATCH_SIZE]
            txs: list[StarknetTransaction] = []
            for tx_hash in batch:
                try:
                    tx = self.node_inquirer.get_transaction_for_hash(tx_hash)
                    txs.append(tx)
                except RemoteError as e:
                    log.error(
                        f'Failed to query Starknet transaction {tx_hash}: {e}. Skipping.',
                    )
                    continue

            if txs:
                with self.database.conn.write_ctx() as write_cursor:
                    self.dbtx.add_transactions(
                        write_cursor=write_cursor,
                        starknet_transactions=txs,
                        relevant_address=address,
                    )

    def _get_tx_hashes_for_address(self, address: StarknetAddress) -> list[str]:
        """Get transaction hashes for an address using starknet_getEvents.

        On current Starknet mainnet (pre-SNIP-13), standard ERC20 Transfer events
        store from/to in the `data` array, not in `keys`. So we cannot filter by
        address using the keys parameter alone. Instead we:

        1. Query Transfer events from known token contracts (ETH, STRK)
        2. Post-filter by checking if the address is in data[0] (from) or data[1] (to)

        May raise:
        - RemoteError if there is a problem with querying the RPC
        """
        from rotkehlchen.chain.starknet.utils import normalize_starknet_address
        normalized = normalize_starknet_address(address)
        seen: set[str] = set()
        tx_hashes: list[str] = []

        # Query Transfer events from known token contracts
        token_contracts = [STRK_TOKEN_ADDRESS, ETH_TOKEN_ADDRESS]
        for token_address in token_contracts:
            self._collect_transfer_tx_hashes_for_address(
                token_address=token_address,
                normalized_address=normalized,
                seen=seen,
                tx_hashes=tx_hashes,
            )

        log.debug(
            f'Discovered {len(tx_hashes)} unique transaction hashes '
            f'for Starknet address {address}',
        )
        return tx_hashes

    def _collect_transfer_tx_hashes_for_address(
            self,
            token_address: str,
            normalized_address: str,
            seen: set[str],
            tx_hashes: list[str],
    ) -> None:
        """Query Transfer events from a token contract and collect tx hashes
        where normalized_address appears as sender (data[0]) or recipient (data[1]).

        On current Starknet mainnet (pre-SNIP-13), Transfer event layout:
        - keys[0]: Transfer event selector
        - data[0]: from address
        - data[1]: to address
        - data[2]: amount low (uint128)
        - data[3]: amount high (uint128)

        May raise:
        - RemoteError if there is a problem with querying the RPC
        """
        continuation_token: str | None = None

        while True:
            params: dict = {
                'from_block': {'block_number': 0},
                'to_block': 'latest',
                'address': token_address,
                'keys': [[TRANSFER_EVENT_SELECTOR]],
                'chunk_size': 100,
            }
            if continuation_token is not None:
                params['continuation_token'] = continuation_token

            try:
                result = self.node_inquirer._rpc_call(
                    'starknet_getEvents', {'filter': params},
                )
            except RemoteError as e:
                log.error(
                    f'Failed to query Transfer events from {token_address}: {e}',
                )
                break

            if result is None:
                break

            for event in result.get('events', []):
                data = event.get('data', [])
                if len(data) < 2:
                    continue

                # Normalize addresses from event data for comparison.
                # RPC may return unpadded hex (e.g. 0x4718f5a... vs 0x04718f5a...)
                from rotkehlchen.chain.starknet.utils import normalize_starknet_address
                from_addr = normalize_starknet_address(data[0])
                to_addr = normalize_starknet_address(data[1])

                # Check if our address is the sender or recipient
                if from_addr == normalized_address or to_addr == normalized_address:
                    tx_hash = event.get('transaction_hash')
                    if tx_hash and tx_hash not in seen:
                        seen.add(tx_hash)
                        tx_hashes.append(tx_hash)

            continuation_token = result.get('continuation_token')
            if continuation_token is None:
                break
