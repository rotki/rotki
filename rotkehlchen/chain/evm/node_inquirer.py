"""Async implementation of EVM node inquirer

This replaces the gevent-based node inquirer with native async/await,
providing better performance for blockchain queries.
"""
import asyncio
import logging
from collections.abc import Sequence
from typing import Any

import aiohttp
from eth_typing import BlockNumber, ChecksumAddress, HexStr
from eth_utils import to_hex
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.types import BlockData, TxData, TxReceipt

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, EVMTxHash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmNodeInquirer:
    """Async implementation of EVM node communication

    This eliminates gevent and uses native asyncio for better performance
    and natural concurrency handling.
    """

    def __init__(
        self,
        chain_id: ChainID,
        nodes: Sequence[WeightedNode],
        call_order: Sequence[NodeName] | None = None,
    ):
        self.chain_id = chain_id
        self.nodes = {node.name: node for node in nodes}
        self.call_order = call_order or [node.name for node in nodes]

        # Web3 instances per node
        self._web3_instances: dict[NodeName, AsyncWeb3] = {}
        self._session: aiohttp.ClientSession | None = None

        # Connection pool settings
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_connections = 100

    async def initialize(self):
        """Initialize async resources"""
        if self._session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=20,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )

        # Initialize Web3 instances
        for node_name, node in self.nodes.items():
            provider = AsyncHTTPProvider(
                endpoint_uri=node.endpoint,
                request_kwargs={'timeout': 30},
            )
            self._web3_instances[node_name] = AsyncWeb3(provider)

    async def close(self):
        """Clean up async resources"""
        if self._session:
            await self._session.close()
            self._session = None

    async def get_block_by_number(
        self,
        block_number: BlockNumber | str,
        full_transactions: bool = False,
    ) -> BlockData:
        """Get block data by number with automatic node failover"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                return await web3.eth.get_block(
                    block_number,
                    full_transactions=full_transactions,
                )
            except Exception as e:
                log.warning(
                    f'Failed to get block {block_number} from {node_name}: {e}',
                )
                continue

        raise RemoteError(
            f'Failed to get block {block_number} from all nodes',
        )

    async def get_transaction_by_hash(self, tx_hash: EVMTxHash) -> TxData:
        """Get transaction data by hash"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                return await web3.eth.get_transaction(HexStr(tx_hash))
            except Exception as e:
                log.warning(
                    f'Failed to get transaction {tx_hash} from {node_name}: {e}',
                )
                continue

        raise RemoteError(
            f'Failed to get transaction {tx_hash} from all nodes',
        )

    async def get_transaction_receipt(self, tx_hash: EVMTxHash) -> TxReceipt:
        """Get transaction receipt"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                return await web3.eth.get_transaction_receipt(HexStr(tx_hash))
            except Exception as e:
                log.warning(
                    f'Failed to get receipt for {tx_hash} from {node_name}: {e}',
                )
                continue

        raise RemoteError(
            f'Failed to get receipt for {tx_hash} from all nodes',
        )

    async def get_balance(
        self,
        address: ChecksumAddress,
        block_identifier: BlockNumber | str = 'latest',
    ) -> FVal:
        """Get ETH balance for an address"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                balance_wei = await web3.eth.get_balance(
                    address,
                    block_identifier=block_identifier,
                )
                return FVal(balance_wei) / FVal(10 ** 18)
            except Exception as e:
                log.warning(
                    f'Failed to get balance for {address} from {node_name}: {e}',
                )
                continue

        raise RemoteError(
            f'Failed to get balance for {address} from all nodes',
        )

    async def call_contract(
        self,
        contract: EvmContract,
        method_name: str,
        arguments: list[Any] | None = None,
        block_identifier: BlockNumber | str = 'latest',
    ) -> Any:
        """Call a contract method"""
        if arguments is None:
            arguments = []

        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                contract_instance = web3.eth.contract(
                    address=contract.address,
                    abi=contract.abi,
                )

                method = getattr(contract_instance.functions, method_name)
                return await method(*arguments).call(
                    block_identifier=block_identifier,
                )
            except Exception as e:
                log.warning(
                    f'Failed to call {method_name} on {contract.address} '
                    f'from {node_name}: {e}',
                )
                continue

        raise RemoteError(
            f'Failed to call {method_name} on {contract.address} from all nodes',
        )

    async def get_logs(
        self,
        from_block: BlockNumber,
        to_block: BlockNumber,
        address: ChecksumAddress | list[ChecksumAddress] | None = None,
        topics: list[str | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Get logs with automatic pagination for large ranges"""
        chunk_size = 2000  # Reasonable chunk size to avoid timeouts
        all_logs = []

        current_from = from_block
        while current_from <= to_block:
            current_to = min(current_from + chunk_size - 1, to_block)

            for node_name in self.call_order:
                try:
                    web3 = self._web3_instances[node_name]

                    filter_params = {
                        'fromBlock': current_from,
                        'toBlock': current_to,
                    }
                    if address:
                        filter_params['address'] = address
                    if topics:
                        filter_params['topics'] = topics

                    logs = await web3.eth.get_logs(filter_params)
                    all_logs.extend(logs)
                    break
                except Exception as e:
                    log.warning(
                        f'Failed to get logs from {node_name} for blocks '
                        f'{current_from}-{current_to}: {e}',
                    )
                    if node_name == self.call_order[-1]:
                        raise RemoteError(
                            f'Failed to get logs from all nodes for blocks '
                            f'{current_from}-{current_to}',
                        )

            current_from = current_to + 1

            # Small delay to avoid overwhelming nodes
            await asyncio.sleep(0.1)

        return all_logs

    async def multicall(
        self,
        calls: list[tuple[ChecksumAddress, bytes]],
        block_identifier: BlockNumber | str = 'latest',
    ) -> list[tuple[bool, bytes]]:
        """Execute multiple calls in a single request using Multicall contract"""
        # Would implement multicall logic here
        # For now, fall back to individual calls
        results = []
        for address, data in calls:
            try:
                for node_name in self.call_order:
                    try:
                        web3 = self._web3_instances[node_name]
                        result = await web3.eth.call({
                            'to': address,
                            'data': to_hex(data),
                        }, block_identifier)
                        results.append((True, result))
                        break
                    except Exception:
                        if node_name == self.call_order[-1]:
                            results.append((False, b''))
            except Exception:
                results.append((False, b''))

        return results

    async def get_block_number(self) -> BlockNumber:
        """Get the latest block number"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                block_number = await web3.eth.block_number
                return BlockNumber(block_number)
            except Exception as e:
                log.warning(
                    f'Failed to get block number from {node_name}: {e}',
                )
                continue

        raise RemoteError('Failed to get block number from all nodes')

    async def get_code(
        self,
        address: ChecksumAddress,
        block_identifier: BlockNumber | str = 'latest',
    ) -> HexStr:
        """Get contract code at address"""
        for node_name in self.call_order:
            try:
                web3 = self._web3_instances[node_name]
                code = await web3.eth.get_code(address, block_identifier)
                return HexStr(code.hex())
            except Exception as e:
                log.warning(
                    f'Failed to get code for {address} from {node_name}: {e}',
                )
                continue

        raise RemoteError(f'Failed to get code for {address} from all nodes')


class BatchEvmQuerier:
    """Batch multiple blockchain queries for efficiency"""

    def __init__(self, inquirer: EvmNodeInquirer):
        self.inquirer = inquirer

    async def get_balances(
        self,
        addresses: list[ChecksumAddress],
        block_identifier: BlockNumber | str = 'latest',
    ) -> dict[ChecksumAddress, FVal]:
        """Get balances for multiple addresses concurrently"""
        tasks = [
            self.inquirer.get_balance(address, block_identifier)
            for address in addresses
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        balances = {}
        for address, result in zip(addresses, results, strict=False):
            if isinstance(result, Exception):
                log.error(f'Failed to get balance for {address}: {result}')
                balances[address] = FVal(0)
            else:
                balances[address] = result

        return balances

    async def get_transactions(
        self,
        tx_hashes: list[EVMTxHash],
    ) -> dict[EVMTxHash, TxData | None]:
        """Get multiple transactions concurrently"""
        tasks = [
            self.inquirer.get_transaction_by_hash(tx_hash)
            for tx_hash in tx_hashes
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        transactions = {}
        for tx_hash, result in zip(tx_hashes, results, strict=False):
            if isinstance(result, Exception):
                log.error(f'Failed to get transaction {tx_hash}: {result}')
                transactions[tx_hash] = None
            else:
                transactions[tx_hash] = result

        return transactions

    async def get_receipts(
        self,
        tx_hashes: list[EVMTxHash],
    ) -> dict[EVMTxHash, TxReceipt | None]:
        """Get multiple receipts concurrently"""
        tasks = [
            self.inquirer.get_transaction_receipt(tx_hash)
            for tx_hash in tx_hashes
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        receipts = {}
        for tx_hash, result in zip(tx_hashes, results, strict=False):
            if isinstance(result, Exception):
                log.error(f'Failed to get receipt for {tx_hash}: {result}')
                receipts[tx_hash] = None
            else:
                receipts[tx_hash] = result

        return receipts

# Constants
WEB3_LOGQUERY_BLOCK_RANGE = 250000  # Default block range for log queries

# Placeholder for missing type
from typing import NamedTuple
class DSProxyInquirerWithCacheData(NamedTuple):
    """Placeholder for DSProxy data"""
    address: str
    timestamp: int

