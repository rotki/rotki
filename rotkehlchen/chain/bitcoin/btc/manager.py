import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.chain.bitcoin.btc.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKCYPHER_BASE_URL,
    BLOCKCYPHER_BATCH_SIZE,
    BLOCKCYPHER_TX_IO_LIMIT,
    BLOCKCYPHER_TX_LIMIT,
    BLOCKSTREAM_BASE_URL,
    BTC_EVENT_IDENTIFIER_PREFIX,
    MEMPOOL_SPACE_BASE_URL,
)
from rotkehlchen.chain.bitcoin.manager import BitcoinCommonManager
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcApiCallback, BtcTxIO, BtcTxIODirection
from rotkehlchen.chain.bitcoin.utils import (
    query_blockstream_like_balances,
    query_blockstream_like_has_transactions,
)
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_int,
    deserialize_timestamp,
    deserialize_timestamp_from_date,
    ensure_type,
)
from rotkehlchen.types import BTCAddress, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks, satoshis_to_btc
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
            asset=A_BTC,
            event_identifier_prefix=BTC_EVENT_IDENTIFIER_PREFIX,
            cache_key=DBCacheDynamic.LAST_BTC_TX_BLOCK,
            api_callbacks=[BtcApiCallback(
                name='blockchain.info',
                balances_fn=self._query_blockchain_info_balances,
                has_transactions_fn=self._query_blockchain_info_has_transactions,
                transactions_fn=self._query_blockchain_info_transactions,
            ), BtcApiCallback(
                name='blockstream.info',
                balances_fn=lambda accounts: query_blockstream_like_balances(base_url=BLOCKSTREAM_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: query_blockstream_like_has_transactions(base_url=BLOCKSTREAM_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=None,  # this API doesn't handle p2pk txs properly
            ), BtcApiCallback(
                name='mempool.space',
                balances_fn=lambda accounts: query_blockstream_like_balances(base_url=MEMPOOL_SPACE_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: query_blockstream_like_has_transactions(base_url=MEMPOOL_SPACE_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=None,  # this API doesn't handle p2pk txs properly
            ), BtcApiCallback(
                name='blockcypher.com',
                balances_fn=None,  # TODO implement blockcypher for all actions
                has_transactions_fn=None,
                transactions_fn=self._query_blockcypher_transactions,
            )],
        )

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
            processing_fn=self.deserialize_tx_from_blockchain_info,
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
        return self.deserialize_tx_from_blockcypher(processed_data)

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

    def deserialize_tx_from_blockcypher(self, data: dict[str, Any]) -> 'BitcoinTx':
        """Deserialize a transaction from a blockcypher.
        May raise DeserializationError, KeyError, ValueError.
        """
        return BitcoinTx(
            tx_id=data['hash'],
            timestamp=deserialize_timestamp_from_date(
                date=data['confirmed'],
                formatstr='iso8601',
                location='blockcypher bitcoin tx',
            ),
            block_height=deserialize_int(data['block_height']),
            fee=satoshis_to_btc(deserialize_int(data['fees'])),
            inputs=BtcTxIO.deserialize_list(
                data_list=data['inputs'],
                direction=BtcTxIODirection.INPUT,
                deserialize_fn=self.deserialize_tx_io_from_blockcypher,
            ),
            outputs=BtcTxIO.deserialize_list(
                data_list=data['outputs'],
                direction=BtcTxIODirection.OUTPUT,
                deserialize_fn=self.deserialize_tx_io_from_blockcypher,
            ),
        )

    def deserialize_tx_from_blockchain_info(self, data: dict[str, Any]) -> 'BitcoinTx':
        """Deserialize a transaction from a blockchain.info.
        May raise DeserializationError, KeyError, ValueError.
        """
        inputs = [vin['prev_out'] for vin in data['inputs']]
        outputs = data['out']
        multi_io = False
        if (
            (vin_sz := data['vin_sz']) > 1 and
            (vout_sz := data['vout_sz']) > 1 and
            (len(inputs) != vin_sz or len(outputs) != vout_sz)
        ):
            # This api omits some TxIOs if they don't directly affect the addresses queried.
            # Set multi_io to ensure proper many-to-many decoding if some TxIOs are missing.
            multi_io = True

        return BitcoinTx(
            tx_id=data['hash'],
            timestamp=deserialize_timestamp(data['time']),
            block_height=deserialize_int(data['block_height']),
            fee=satoshis_to_btc(deserialize_int(data['fee'])),
            inputs=BtcTxIO.deserialize_list(
                data_list=inputs,
                direction=BtcTxIODirection.INPUT,
                deserialize_fn=self.deserialize_tx_io_from_blockchain_info,
            ),
            outputs=BtcTxIO.deserialize_list(
                data_list=outputs,
                direction=BtcTxIODirection.OUTPUT,
                deserialize_fn=self.deserialize_tx_io_from_blockchain_info,
            ),
            multi_io=multi_io,
        )

    @staticmethod
    def deserialize_tx_io_from_blockcypher(
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        """Deserialize a TxIO from blockcypher.
        May raise DeserializationError, KeyError, ValueError.
        """
        return BtcTxIO(
            value=satoshis_to_btc(deserialize_int(
                data.get('value', 0) if direction == BtcTxIODirection.OUTPUT
                else data.get('output_value', 0),
            )),
            script=bytes.fromhex(script) if (script := data.get('script')) is not None else None,
            address=addresses[0] if (addresses := data['addresses']) is not None else None,
            direction=direction,
        )

    @staticmethod
    def deserialize_tx_io_from_blockchain_info(
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        """Deserialize a TxIO from blockchain.info.
        May raise DeserializationError, KeyError, ValueError.
        """
        return BtcTxIO(
            value=satoshis_to_btc(deserialize_int(data['value'])),
            script=bytes.fromhex(data['script']),
            address=data.get('addr'),
            direction=direction,
        )
