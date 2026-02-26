import json
import logging
import operator
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any, Final

import gevent
import requests

from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import (
    TRANSACTIONS_BATCH_NUM,
    EvmIndexerInterface,
    HasChainActivity,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
)
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import set_user_agent
from rotkehlchen.utils.network import create_session

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# SQD recommends keeping queries to 10k-50k blocks per request
# https://beta.docs.sqd.dev/en/portal/evm/api#3-optimal-batch-sizes
BLOCK_CHUNK_SIZE: Final = 50_000
ERC20_TRANSFER_TOPIC: Final = f'0x{ERC20_OR_ERC721_TRANSFER.hex()}'
# Network names from https://beta.docs.sqd.dev/en/data/networks/evm
SQD_CHAIN_NAMES: Final[dict[ChainID, str]] = {
    ChainID.ETHEREUM: 'ethereum-mainnet',
    ChainID.ARBITRUM_ONE: 'arbitrum-one',
    ChainID.OPTIMISM: 'optimism-mainnet',
    ChainID.BASE: 'base-mainnet',
    ChainID.POLYGON_POS: 'polygon-mainnet',
    ChainID.BINANCE_SC: 'binance-mainnet',
    ChainID.GNOSIS: 'gnosis-mainnet',
    ChainID.SCROLL: 'scroll-mainnet',
}


def _pad_address_to_topic(address: ChecksumEvmAddress) -> str:
    """Pad a 20-byte address to a 32-byte topic value for log filtering."""
    return '0x' + '0' * 24 + address[2:].lower()


class Sqd(EvmIndexerInterface):
    """SQD Portal API handler.

    Queries the SQD (Subsquid) Portal finalized-stream endpoint for EVM blockchain data.
    Uses POST with JSON body and NDJSON responses. No API key required.
    See https://beta.docs.sqd.dev/en/portal/evm/api
    """
    name: Final = 'SQD'
    base_url: Final = 'https://portal.sqd.dev/datasets'

    def __init__(self) -> None:
        self.session = create_session()
        set_user_agent(self.session)

    @staticmethod
    def _get_network(chain_id: ChainID) -> str:
        """Map ChainID to SQD dataset name.

        May raise:
        - ChainNotSupported if SQD does not index the given chain
        """
        if (network := SQD_CHAIN_NAMES.get(chain_id)) is None:
            raise ChainNotSupported(f'SQD does not support {chain_id.name}')
        return network

    def _query_stream(
            self,
            chain_id: ChainID,
            from_block: int,
            to_block: int,
            fields: dict[str, dict[str, bool]],
            transactions: list[dict[str, Any]] | None = None,
            logs: list[dict[str, Any]] | None = None,
            traces: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Query the SQD Portal finalized-stream endpoint for blockchain data.

        The finalized-stream endpoint returns partial results per request, so we
        keep requesting from the last returned block until the full range is covered.

        May raise:
        - RemoteError if there are problems contacting SQD or parsing the response
        - ChainNotSupported if the chain is not available in SQD
        """
        url = f'{self.base_url}/{self._get_network(chain_id)}/finalized-stream'
        body: dict[str, Any] = {
            'type': 'evm',
            'fromBlock': from_block,
            'toBlock': to_block,
            'fields': fields,
        }
        if transactions is not None:
            body['transactions'] = transactions
        if logs is not None:
            body['logs'] = logs
        if traces is not None:
            body['traces'] = traces

        cached_settings = CachedSettings()
        backoff_limit = cached_settings.get_query_retry_limit()
        timeout = cached_settings.get_timeout_tuple()

        all_blocks: list[dict[str, Any]] = []
        current_from = from_block

        while current_from <= to_block:
            body['fromBlock'] = current_from
            backoff = 1

            while backoff < backoff_limit:
                log.debug(
                    f'Querying SQD {chain_id.name} blocks {current_from}-{to_block} '
                    f'with tx_filters={transactions}, log_filters={logs}, trace_filters={traces}',
                )
                try:
                    response = self.session.post(url=url, json=body, timeout=timeout)
                except requests.exceptions.RequestException as e:
                    raise RemoteError(f'SQD API request failed due to {e!s}') from e

                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    retry_after = int(response.headers.get('Retry-After', backoff))
                    backoff = max(backoff * 2, retry_after + 1)
                    if backoff >= backoff_limit:
                        raise RemoteError(
                            f'SQD rate limit exceeded even after backing off '
                            f'while querying {chain_id.name}',
                        )
                    log.debug(
                        f'Got rate limited by SQD for {chain_id.name}. '
                        f'Sleeping for {retry_after} seconds.',
                    )
                    gevent.sleep(retry_after)
                    continue

                if response.status_code != HTTPStatus.OK:
                    raise RemoteError(
                        f'SQD API request to {url} failed with HTTP status code '
                        f'{response.status_code} and text {response.text}',
                    )

                last_block_number = current_from
                for line in response.text.strip().split('\n'):
                    if not line:
                        continue
                    try:
                        block = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise RemoteError(
                            f'SQD returned invalid JSON in NDJSON response: {line[:200]}...',
                        ) from e
                    all_blocks.append(block)
                    last_block_number = block.get('header', {}).get('number', last_block_number)

                log.debug(
                    f'SQD {chain_id.name} blocks {current_from}-{to_block} '
                    f'returned up to block {last_block_number}',
                )
                current_from = last_block_number + 1
                break  # success, move to next page

            else:
                raise RemoteError(
                    f'SQD API request failed due to backing off longer than '
                    f'the max backoff of {backoff_limit} seconds for {chain_id.name}',
                )

        return all_blocks

    def _query_chunked(
            self,
            chain_id: ChainID,
            from_block: int,
            to_block: int,
            fields: dict[str, dict[str, bool]],
            transactions: list[dict[str, Any]] | None = None,
            logs: list[dict[str, Any]] | None = None,
            traces: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Query SQD in block range chunks to avoid oversized responses.
        Splits large block ranges into BLOCK_CHUNK_SIZE chunks and queries them sequentially
        """
        all_blocks: list[dict[str, Any]] = []
        current_from = from_block
        while current_from <= to_block:
            current_to = min(current_from + BLOCK_CHUNK_SIZE - 1, to_block)
            all_blocks.extend(self._query_stream(
                chain_id=chain_id,
                from_block=current_from,
                to_block=current_to,
                fields=fields,
                transactions=transactions,
                logs=logs,
                traces=traces,
            ))
            current_from = current_to + 1

        return all_blocks

    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            internal: bool,
            period: TimestampOrBlockRange | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Get transactions from SQD Portal.

        For normal transactions: queries where the account is sender or receiver.
        For internal transactions: queries traces for the account.

        May raise:
        - RemoteError if SQD can't handle this query type or has connection issues
        - ChainNotSupported if SQD doesn't index this chain
        """
        if period is None:
            query_from, query_to = 0, self.get_latest_block_number(chain_id)
        elif period.range_type == 'blocks':
            query_from, query_to = period.from_value, period.to_value
        else:
            raise RemoteError('SQD only supports block-range queries for transactions')

        account_lower = account.lower() if account else None

        if internal:
            yield from self._get_internal_transactions(
                chain_id=chain_id,
                account_lower=account_lower,
                from_block=query_from,
                to_block=query_to,
            )
        else:
            yield from self._get_normal_transactions(
                chain_id=chain_id,
                account=account,
                account_lower=account_lower,
                from_block=query_from,
                to_block=query_to,
            )

    def _get_normal_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            account_lower: str | None,
            from_block: int,
            to_block: int,
    ) -> Iterator[list[EvmTransaction]]:
        """Query and yield normal transactions from SQD."""
        tx_filters: list[dict[str, Any]] = []
        if account_lower:
            tx_filters = [
                {'from': [account_lower]},
                {'to': [account_lower]},
            ]

        transactions: list[EvmTransaction] = []
        last_ts = Timestamp(0)
        for block in self._query_chunked(
            chain_id=chain_id,
            from_block=from_block,
            to_block=to_block,
            fields={
                'block': {'number': True, 'timestamp': True},
                'transaction': {
                    'hash': True, 'from': True, 'to': True, 'value': True,
                    'input': True, 'gas': True, 'gasUsed': True, 'nonce': True,
                    'status': True, 'gasPrice': True, 'transactionIndex': True,
                },
            },
            transactions=tx_filters or None,
        ):
            header = block['header']
            block_number = header['number']
            block_timestamp = Timestamp(header['timestamp'])

            for tx in block.get('transactions', []):
                tx['blockNumber'] = block_number
                tx['timeStamp'] = block_timestamp
                try:
                    evm_tx, _ = deserialize_evm_transaction(
                        data=tx,
                        internal=False,
                        chain_id=chain_id,
                        evm_inquirer=None,
                    )
                except DeserializationError as e:
                    log.warning(
                        f'{e!s}. Skipping transaction {tx.get("hash", "")} '
                        f'on {chain_id.to_name()} for {account}',
                    )
                    continue

                if block_timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = block_timestamp
                    transactions = []
                transactions.append(evm_tx)

        yield transactions

    def _get_internal_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account_lower: str | None,
            from_block: int,
            to_block: int,
    ) -> Iterator[list[EvmInternalTransaction]]:
        """Query and yield internal transactions (traces) from SQD."""
        trace_filters: list[dict[str, Any]] = []
        if account_lower:
            trace_filters = [
                {'callFrom': [account_lower]},
                {'callTo': [account_lower]},
            ]

        transactions: list[EvmInternalTransaction] = []
        last_ts = Timestamp(0)
        for block in self._query_chunked(
            chain_id=chain_id,
            from_block=from_block,
            to_block=to_block,
            fields={
                'block': {'number': True, 'timestamp': True},
                'transaction': {'hash': True, 'transactionIndex': True},
                'trace': {
                    'transactionIndex': True,
                    'from': True, 'to': True, 'value': True,
                    'gas': True, 'gasUsed': True, 'error': True,
                },
            },
            traces=trace_filters or None,
            transactions=[{}],  # request all transactions to map traces to tx hashes
        ):
            header = block['header']
            block_timestamp = Timestamp(header['timestamp'])

            # build a map of transactionIndex -> tx hash for this block
            tx_hash_by_index: dict[int, str] = {}
            for tx in block.get('transactions', []):
                tx_hash_by_index[tx['transactionIndex']] = tx['hash']

            for trace_idx, trace in enumerate(block.get('traces', [])):
                if (tx_index := trace.get('transactionIndex')) is None:
                    log.warning(
                        f'Missing transactionIndex in SQD trace for block '
                        f'{header["number"]} on {chain_id.to_name()}',
                    )
                    continue

                if not (parent_hash := tx_hash_by_index.get(tx_index, '')):
                    continue  # can't link trace to transaction

                trace['blockNumber'] = header['number']
                trace['timeStamp'] = block_timestamp
                trace['traceId'] = trace_idx
                try:
                    internal_tx, _ = deserialize_evm_transaction(
                        data=trace,
                        internal=True,
                        chain_id=chain_id,
                        evm_inquirer=None,
                        parent_tx_hash=deserialize_evm_tx_hash(parent_hash),
                    )
                except DeserializationError as e:
                    log.warning(
                        f'{e!s}. Skipping internal transaction in block '
                        f'{header["number"]} on {chain_id.to_name()}',
                    )
                    continue

                if block_timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = block_timestamp
                    transactions = []
                transactions.append(internal_tx)

        yield transactions

    def get_token_transaction_hashes(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        """Get transaction hashes involving ERC20 token transfers for an account.

        Queries SQD for Transfer event logs where the account is sender (topic1)
        or receiver (topic2), then extracts unique transaction hashes.
        """
        query_from = from_block if from_block is not None else 0
        query_to = to_block if to_block is not None else self.get_latest_block_number(chain_id)
        padded_account = _pad_address_to_topic(account)

        hashes: dict[EVMTxHash, Timestamp] = {}
        last_ts: Timestamp | None = None
        for block in self._query_chunked(
            chain_id=chain_id,
            from_block=query_from,
            to_block=query_to,
            fields={
                'block': {'number': True, 'timestamp': True},
                'log': {'transactionHash': True},
            },
            logs=[
                {'topic0': [ERC20_TRANSFER_TOPIC], 'topic1': [padded_account]},
                {'topic0': [ERC20_TRANSFER_TOPIC], 'topic2': [padded_account]},
            ],
        ):
            header = block['header']
            block_timestamp = Timestamp(header['timestamp'])

            for log_entry in block.get('logs', []):
                try:
                    tx_hash = deserialize_evm_tx_hash(log_entry['transactionHash'])
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction hash {log_entry.get('transactionHash')} "
                        f'from {chain_id.name} SQD for {account}. {e!s}',
                    )
                    continue

                if last_ts is not None and block_timestamp > last_ts and len(hashes) >= TRANSACTIONS_BATCH_NUM:  # noqa: E501
                    yield [h for h, _ in sorted(hashes.items(), key=operator.itemgetter(1))]
                    hashes = {}
                last_ts = block_timestamp
                hashes[tx_hash] = block_timestamp

        yield [h for h, _ in sorted(hashes.items(), key=operator.itemgetter(1))]

    def get_logs(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            contract_address: ChecksumEvmAddress,
            topics: list[str | None],
            from_block: int,
            to_block: int | str = 'latest',
            existing_events: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Get event logs from SQD Portal.

        Queries logs by contract address and topics, converting the SQD response
        to the format expected by the node_inquirer log processing pipeline.

        May raise:
        - RemoteError if there are problems contacting SQD or parsing the response
        """
        if isinstance(to_block, int):
            query_to = to_block
        else:
            query_to = self.get_latest_block_number(chain_id)

        # build SQD log filter from topics
        log_filter: dict[str, Any] = {'address': [contract_address.lower()]}
        for idx, topic in enumerate(topics):
            if topic is not None:
                log_filter[f'topic{idx}'] = [topic]

        events: list[dict[str, Any]] = []
        for block in self._query_chunked(
            chain_id=chain_id,
            from_block=from_block,
            to_block=query_to,
            fields={
                'block': {'number': True, 'timestamp': True},
                'log': {
                    'address': True, 'topics': True, 'data': True,
                    'logIndex': True, 'transactionIndex': True,
                    'transactionHash': True,
                },
            },
            logs=[log_filter],
        ):
            header = block['header']
            block_number = header['number']
            block_timestamp = header['timestamp']

            for log_entry in block.get('logs', []):
                try:
                    events.append({
                        'address': deserialize_evm_address(log_entry['address']),
                        'blockNumber': block_number,
                        'logIndex': log_entry['logIndex'],
                        'transactionHash': log_entry['transactionHash'],
                        'transactionIndex': log_entry['transactionIndex'],
                        'data': log_entry['data'],
                        'topics': log_entry['topics'],
                        'timeStamp': block_timestamp,
                        'gasPrice': 0,
                        'gasUsed': 0,
                    })
                except (KeyError, DeserializationError) as e:
                    log.warning(
                        f'{e!s}. Skipping log entry in block '
                        f'{block_number} on {chain_id.to_name()}',
                    )
                    continue

        return events

    def get_latest_block_number(self, chain_id: SUPPORTED_CHAIN_IDS) -> int:
        """Get the latest finalized block number from SQD finalized-head endpoint.

        Returns the 'number' field from the response JSON:
        {"number": 24499836, "hash": "0x..."}

        May raise:
        - RemoteError if there are problems contacting SQD
        - ChainNotSupported if SQD doesn't index this chain
        """
        try:
            response = self.session.get(
                url=f'{self.base_url}/{self._get_network(chain_id)}/finalized-head',
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'SQD latest block request failed due to {e!s}') from e

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'SQD latest block request failed with HTTP '
                f'{response.status_code}: {response.text}',
            )

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError(
                f'SQD latest block returned invalid JSON: {response.text}',
            ) from e

        if isinstance(data, dict) and isinstance(data.get('number'), int):
            return data['number']

        raise RemoteError(
            f'Could not extract block number from SQD latest block response: {data}',
        )

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """Check if an account has any activity by querying SQD for transactions and logs.

        Splits the block range into chunks and queries them sequentially from
        newest to oldest. Returns as soon as a chunk finds transactions.

        NOTE: SQD cannot detect ETH withdrawals or block production rewards.

        May raise:
        - RemoteError if SQD can't be reached
        - ChainNotSupported if SQD doesn't index this chain
        """
        latest_block = self.get_latest_block_number(chain_id)
        account_lower = account.lower()
        padded = _pad_address_to_topic(account)

        current_to = latest_block
        while current_to >= 0:
            current_from = max(current_to - BLOCK_CHUNK_SIZE + 1, 0)
            result = self._query_stream(
                chain_id=chain_id,
                from_block=current_from,
                to_block=current_to,
                fields={'block': {'number': True}},
                transactions=[
                    {'from': [account_lower]},
                    {'to': [account_lower]},
                ],
                logs=[
                    {'topic0': [ERC20_TRANSFER_TOPIC], 'topic1': [padded]},
                    {'topic0': [ERC20_TRANSFER_TOPIC], 'topic2': [padded]},
                ],
            )
            current_to = current_from - 1

            for block in result:
                if block.get('transactions'):
                    return HasChainActivity.TRANSACTIONS
                if block.get('logs'):
                    return HasChainActivity.TOKENS

        return HasChainActivity.NONE
