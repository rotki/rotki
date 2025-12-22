import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_raw_value
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from web3 import Web3

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress, FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ActiveManager:

    def __init__(self, node_inquirer: 'EvmNodeInquirer'):
        self.node_inquirer = node_inquirer

    def _create_token_transfer(
            self,
            rpc_client: 'Web3',
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            token: 'EvmToken',
            amount: 'FVal',
    ) -> dict[str, Any]:
        """Build transaction to transfer erc20 tokens"""
        contract = rpc_client.eth.contract(
            address=token.evm_address,
            abi=self.node_inquirer.contracts.erc20_abi,
        )
        payload = dict(contract.functions.transfer(
            to_address,
            asset_raw_value(amount=amount, asset=token),
        ).build_transaction({
            'from': from_address,
            'nonce': rpc_client.eth.get_transaction_count(from_address),
        }))

        # ensure that information about gas is not sent in the payload
        # since the consumer adjusts it
        payload.pop('gas', None)
        payload.pop('maxFeePerGas', None)
        payload.pop('maxPriorityFeePerGas', None)
        return payload

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
        return self.node_inquirer._query(
            method=self._create_token_transfer,
            call_order=self.node_inquirer.default_call_order(skip_indexers=True),
            from_address=from_address,
            to_address=to_address,
            token=token,
            amount=amount,
        )

    def _transfer_native_token(
            self,
            rpc_client: 'Web3',
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            amount: 'FVal',
    ) -> dict[str, Any]:
        """Build transaction to transfer the native asset of the blockchain"""
        return {
            'from': from_address,
            'to': to_address,
            'value': asset_raw_value(amount=amount, asset=self.node_inquirer.native_token),
            'nonce': rpc_client.eth.get_transaction_count(from_address),
        }

    def transfer_native_token(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            amount: 'FVal',
    ) -> dict[str, Any]:
        """Wrapper for _transfer_native_token that tries different nodes to query the required
        information and handles errors.

        May raise:
            - RemoteError: If no web3 node is available
        """
        return self.node_inquirer._query(
            method=self._transfer_native_token,
            call_order=self.node_inquirer.default_call_order(skip_indexers=True),
            from_address=from_address,
            to_address=to_address,
            amount=amount,
        )
