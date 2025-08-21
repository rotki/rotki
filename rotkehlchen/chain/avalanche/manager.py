import logging
from collections.abc import Sequence
from typing import Any

from web3 import HTTPProvider, Web3
from web3.datastructures import MutableAttributeDict
from web3.exceptions import Web3Exception

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.errors.misc import BlockchainQueryError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

WEB3_LOGQUERY_BLOCK_RANGE = 250000


class AvalancheManager:
    def __init__(
            self,
            avaxrpc_endpoint: str,
            msg_aggregator: MessagesAggregator,
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Avalanche Manager with own rpc endpoint: {avaxrpc_endpoint}')
        self.rpc_timeout = rpc_timeout
        self.w3 = Web3(
            HTTPProvider(
                endpoint_uri=avaxrpc_endpoint,
                request_kwargs={'timeout': self.rpc_timeout},
            ),
        )
        self.msg_aggregator = msg_aggregator

    def connected_to_any_web3(self) -> bool:
        return self.w3.is_connected()

    def get_latest_block_number(self) -> int:
        return self.w3.eth.block_number

    def get_avax_balance(self, account: ChecksumEvmAddress) -> FVal:
        """
        Gets the balance of the given account in AVAX.
        May raise:
        - Web3Exception: if there is any error querying the AVAX rpc node.
        """
        return from_wei(FVal(self.w3.eth.get_balance(account)))

    def get_multiavax_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Returns a dict with keys being accounts and balances in AVAX"""
        balances = {}
        for account in accounts:
            balances[account] = self.get_avax_balance(account)
        return balances

    def get_block_by_number(self, num: int) -> dict[str, Any]:
        """Returns the block object corresponding to the given block number

        May raise:
        - BlockNotFound if number used to lookup the block can't be found. Raised
        by web3.eth.get_block().
        """
        block_data: MutableAttributeDict = MutableAttributeDict(self.w3.eth.get_block(num))  # type: ignore # pylint: disable=no-member
        block_data['hash'] = block_data['hash'].to_0x_hex()
        return dict(block_data)

    def get_code(self, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address as a 0x hex string"""
        return self.w3.eth.get_code(account).to_0x_hex()

    def call_contract(
            self,
            contract_address: ChecksumEvmAddress,
            abi: list,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> Any:
        """Performs an eth_call to an ethereum contract

        May raise:
        - BlockchainQueryError if web3 is used and there is a VM execution error
        """

        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        try:
            method = getattr(contract.caller, method_name)
            result = method(*arguments or [])
        except (ValueError, Web3Exception) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {e!s}',
            ) from e
        return result
