import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from web3 import Web3
from web3.exceptions import Web3Exception

from rotkehlchen.chain.ethereum.utils import asset_raw_value
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.types import Web3Node
    from rotkehlchen.types import ChecksumEvmAddress, FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ActiveManager:

    def __init__(self, node_inquirer: 'EvmNodeInquirer'):
        self.node_inquirer = node_inquirer

    def addresses_interacted(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
    ) -> bool:
        """Check if from address interacted before with to_address"""
        with self.node_inquirer.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM history_events JOIN evm_events_info ON '
                'history_events.identifier=evm_events_info.identifier WHERE '
                'location_label=? AND address=?',
                (from_address, to_address),
            )
            return cursor.fetchone()[0] > 0

    def _query_gas(self, web3: Web3) -> dict[str, int]:
        return {
            'maxFeePerGas': web3.eth.get_block('latest')['baseFeePerGas'],
            'maxPriorityFeePerGas': web3.eth.max_priority_fee,
        }

    def _query_with_nodes(self, func: Callable, **kwargs: Any) -> dict[str, Any]:
        """
        Wrapper function that tries to connect to web3 nodes and extracts the Web3.py object
        to build transactions. Handles errors from web3.py.

        May raise:
            - RemoteError
        """
        for node in self.node_inquirer.default_call_order(skip_etherscan=True):
            connected, _ = self.node_inquirer.attempt_connect(node.node_info)
            if not connected:
                continue

            if (web3node := self.node_inquirer.web3_mapping.get(node.node_info, None)) is None:
                continue

            try:
                return func(web3node=web3node, **kwargs)
            except Web3Exception as e:
                log.error(f'Failed to create token transfer transaction due to {e}')

        raise RemoteError(f'Failed to call {func.__name__} after trying available nodes')

    def _create_token_transfer(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            token: 'EvmToken',
            amount: 'FVal',
            web3node: 'Web3Node',
    ) -> dict[str, Any]:
        """Build transaction to transfer erc20 tokens"""
        contract = web3node.web3_instance.eth.contract(
            address=token.evm_address,
            abi=self.node_inquirer.contracts.erc20_abi,
        )

        tx_data = dict(contract.functions.transfer(
            to_address,
            asset_raw_value(amount=amount, asset=token),
        ).build_transaction({
            'from': from_address,
            'nonce': web3node.web3_instance.eth.get_transaction_count(from_address),
        }))

        tx_data |= self._query_gas(web3node.web3_instance)
        return tx_data

    def create_token_transfer(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            token: 'EvmToken',
            amount: 'FVal',
    ) -> dict[str, Any]:
        """Wrapper for _create_token_transfer that tries different nodes to create
        the transaction handling errors.

        May raise:
            - RemoteError: If no web3 node is available
        """
        return self._query_with_nodes(
            func=self._create_token_transfer,
            from_address=from_address,
            to_address=to_address,
            token=token,
            amount=amount,
        )

    def _transfer_native_token(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            amount: 'FVal',
            web3node: 'Web3Node',
    ) -> dict[str, Any]:
        """Build transaction to transfer erc20 tokens"""
        return {
            'from': from_address,
            'to': to_address,
            'value': asset_raw_value(amount=amount, asset=self.node_inquirer.native_token),
            'nonce': web3node.web3_instance.eth.get_transaction_count(from_address),
            **self._query_gas(web3node.web3_instance),
        }

    def transfer_native_token(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            amount: 'FVal',
    ) -> dict[str, Any]:
        return self._query_with_nodes(
            func=self._transfer_native_token,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
        )
