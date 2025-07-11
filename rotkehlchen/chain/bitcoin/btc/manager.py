import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.chain.bitcoin.btc.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKCYPHER_BASE_URL,
    BLOCKCYPHER_BATCH_SIZE,
    BLOCKCYPHER_TX_IO_LIMIT,
    BLOCKCYPHER_TX_LIMIT,
    BLOCKSTREAM_BASE_URL,
    MEMPOOL_SPACE_BASE_URL,
)
from rotkehlchen.chain.bitcoin.manager import BitcoinCommonManager
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcApiCallback
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks, satoshis_to_btc, ts_now
from rotkehlchen.utils.network import request_get, request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitcoinManager(BitcoinCommonManager):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(
            database=database,
            blockchain=SupportedBlockchain.BITCOIN,
            api_callbacks=[BtcApiCallback(
                name='blockchain.info',
                balances_fn=self._query_blockchain_info_balances,
                has_transactions_fn=self._query_blockchain_info_has_transactions,
                transactions_fn=self._query_blockchain_info_transactions,
            ), BtcApiCallback(
                name='blockstream.info',
                balances_fn=lambda accounts: self._query_blockstream_or_mempool_balances(base_url=BLOCKSTREAM_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: self._query_blockstream_or_mempool_has_transactions(base_url=BLOCKSTREAM_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=None,  # this API doesn't handle p2pk txs properly
            ), BtcApiCallback(
                name='mempool.space',
                balances_fn=lambda accounts: self._query_blockstream_or_mempool_balances(base_url=MEMPOOL_SPACE_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: self._query_blockstream_or_mempool_has_transactions(base_url=MEMPOOL_SPACE_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=None,  # this API doesn't handle p2pk txs properly
            ), BtcApiCallback(
                name='blockcypher.com',
                balances_fn=None,  # TODO implement blockcypher for all actions
                has_transactions_fn=None,
                transactions_fn=self._query_blockcypher_transactions,
            )],
        )

    @staticmethod
    def _query_blockstream_or_mempool_account_info(
            base_url: str,
            account: BTCAddress,
    ) -> tuple[FVal, int]:
        """Query account info from blockstream.info or mempool.space (APIs are nearly identical)
        Returns the account balance and tx count in a tuple.
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        - DeserializationError if got unexpected json values
        """
        response_data = request_get_dict(
            url=f'{base_url}/address/{account}',
            handle_429=True,
            backoff_in_seconds=4,
        )
        stats = response_data['chain_stats']
        funded_txo_sum = satoshis_to_btc(ensure_type(
            symbol=stats['funded_txo_sum'],
            expected_type=int,
            location='blockstream funded_txo_sum',
        ))
        spent_txo_sum = satoshis_to_btc(ensure_type(
            symbol=stats['spent_txo_sum'],
            expected_type=int,
            location='blockstream spent_txo_sum',
        ))
        return funded_txo_sum - spent_txo_sum, stats['tx_count']

    def _query_blockstream_or_mempool_balances(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        balances = {}
        for account in accounts:
            balance, _ = self._query_blockstream_or_mempool_account_info(base_url, account)
            balances[account] = balance
        return balances

    def _query_blockstream_or_mempool_has_transactions(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        have_transactions = {}
        for account in accounts:
            balance, tx_count = self._query_blockstream_or_mempool_account_info(base_url, account)
            have_transactions[account] = ((tx_count != 0), balance)
        return have_transactions

    @staticmethod
    def _query_blockchain_info(
            accounts: Sequence[BTCAddress],
            key: Literal['addresses', 'txs'] = 'addresses',
    ) -> list[dict[str, Any]]:
        """Queries blockchain.info for the specified accounts.
        The response from blockchain.info is a dict with two keys: addresses and txs, each of which
        contains a list of dicts. Returns the full list of dicts for the specified key.
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        """
        results: list[dict[str, Any]] = []
        # the docs suggest 10 seconds for 429 (https://blockchain.info/q)
        kwargs: Any = {'handle_429': True, 'backoff_in_seconds': 10}
        for i in range(0, len(accounts), 80):
            base_url = f"{BLOCKCHAIN_INFO_BASE_URL}/multiaddr?active={'|'.join(accounts[i:i + 80])}"  # noqa: E501
            if key == 'addresses':
                results.extend(request_get_dict(url=base_url, **kwargs)[key])
            else:  # key == 'txs'
                offset, limit = 0, 50
                while True:
                    results.extend(chunk := request_get_dict(
                        url=f'{base_url}&n={limit}&offset={offset}',
                        **kwargs,
                    )[key])
                    if len(chunk) < limit:
                        break  # all txs have been queried

                    offset += limit

        return results

    def _query_blockchain_info_balances(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        balances: dict[BTCAddress, FVal] = {}
        for entry in self._query_blockchain_info(accounts):
            balances[entry['address']] = satoshis_to_btc(ensure_type(
                symbol=entry['final_balance'],
                expected_type=int,
                location='blockchain.info "final_balance"',
            ))
        return balances

    def _query_blockchain_info_has_transactions(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        have_transactions = {}
        for entry in self._query_blockchain_info(accounts):
            balance = satoshis_to_btc(ensure_type(
                symbol=entry['final_balance'],
                expected_type=int,
                location='blockchain.info "final_balance"',
            ))
            have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)
        return have_transactions

    def _process_raw_tx_lists(
            self,
            raw_tx_lists: list[list[dict[str, Any]]],
            options: dict[str, Any],
            processing_fn: Callable[[dict[str, Any]], BitcoinTx],
    ) -> tuple[int, list[BitcoinTx]]:
        """Convert raw txs into BitcoinTxs using the specified deserialize_fn.
        The tx lists must be ordered newest to oldest (the order used by the current APIs).

        If `queried_block_height` is set in options, deserialization will stop when that
        block height is reached.

        If `to_timestamp` is set in options, any transactions newer than that will be skipped.
        But we cannot use a `from_timestamp` since the txs are returned newest to oldest.
        If we were to quit before querying to the oldest tx, the next query would stop at the
        cached queried_block_height and the skipped older txs would never be queried.

        Returns the latest queried block height (cached and referenced in subsequent queries)
        and the list of deserialized BitcoinTxs in a tuple.
        """
        tx_list: list[BitcoinTx] = []
        last_queried_block = options.get('last_queried_block', 0)
        to_timestamp = options.get('to_timestamp', ts_now())
        new_block_height = 0
        for raw_tx_list in raw_tx_lists:
            for entry in raw_tx_list:
                try:
                    tx = processing_fn(entry)
                except (
                    DeserializationError,
                    KeyError,
                    RemoteError,
                    UnableToDecryptRemoteData,
                ) as e:
                    msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
                    log.error(f'Failed to process bitcoin transaction {entry} due to {msg}')
                    continue

                if tx.timestamp > to_timestamp:
                    continue  # Haven't reached the requested range yet. Skip tx.

                if tx.block_height <= last_queried_block:
                    break  # All new txs have been queried. Skip tx and return.

                tx_list.append(tx)

            block_height = tx_list[0].block_height if len(tx_list) > 0 else last_queried_block
            new_block_height = max(new_block_height, block_height)

        return new_block_height, tx_list

    def _query_blockchain_info_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query blockchain.info for transactions.
        Returns a tuple containing the latest queried block height and the list of txs.
        """
        return self._process_raw_tx_lists(
            raw_tx_lists=[self._query_blockchain_info(accounts=accounts, key='txs')],
            options=options,
            processing_fn=BitcoinTx.deserialize_from_blockchain_info,
        )

    def _process_raw_tx_from_blockcypher(
            self,
            data: dict[str, Any],
    ) -> BitcoinTx:
        """Convert a raw tx dict from blockcypher into a BitcoinTx.
        If the tx has a large number of TxIOs, the remaining TxIOs will be queried using the urls
        provided in the API response.
        May raise DeserializationError, KeyError, RemoteError, UnableToDecryptRemoteData.
        """
        inputs: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        for side, tx_io_list in (('inputs', inputs), ('outputs', outputs)):
            next_data = data.copy()
            while True:
                tx_io_list.extend(list_chunk := next_data[side])
                if (
                    (next_url := next_data.get(f'next_{side}')) is None or
                    len(list_chunk) < BLOCKCYPHER_TX_IO_LIMIT
                ):
                    break  # all TxIOs for this side have been queried

                next_data = request_get_dict(url=next_url, handle_429=True, backoff_in_seconds=1)

        processed_data = data.copy()  # avoid modifying the passed data dict
        processed_data['inputs'] = inputs
        processed_data['outputs'] = outputs
        return BitcoinTx.deserialize_from_blockcypher(processed_data)

    def _query_blockcypher_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query blockcypher for transactions.
        Txs from the api are ordered newest to oldest, with pagination via block_height.
        Returns a tuple containing the latest queried block height and the list of txs.
        """
        accounts_tx_lists: dict[BTCAddress, list[dict[str, Any]]] = defaultdict(list)
        limits = f'limit={BLOCKCYPHER_TX_LIMIT}&txlimit={BLOCKCYPHER_TX_IO_LIMIT}'
        for accounts_chunk in get_chunks(list(accounts), BLOCKCYPHER_BATCH_SIZE):
            before_height = None
            while len(accounts_chunk) > 0:
                url = f"{BLOCKCYPHER_BASE_URL}/addrs/{';'.join(accounts_chunk)}/full?{limits}"
                if before_height is not None:
                    url += f'&before={before_height}'

                response = request_get(
                    url=url,
                    handle_429=True,
                    backoff_in_seconds=1,  # the free rate limit is 3 requests per second
                )
                for entry in [response] if isinstance(response, dict) else response:  # dict/list depending on single/multiple accounts  # noqa: E501
                    accounts_tx_lists[address := BTCAddress(entry['address'])].extend(txs := entry['txs'])  # noqa: E501
                    if len(txs) > 0:
                        earliest_block_height = txs[-1]['block_height']
                        before_height = (
                            earliest_block_height if before_height is None
                            else min(before_height, earliest_block_height)
                        )
                    if not entry.get('hasMore', False):
                        accounts_chunk.remove(address)

        return self._process_raw_tx_lists(
            raw_tx_lists=list(accounts_tx_lists.values()),
            options=options,
            processing_fn=self._process_raw_tx_from_blockcypher,
        )
