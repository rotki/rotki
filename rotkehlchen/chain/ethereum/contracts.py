from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from eth_typing.abi import Decodable
from web3 import Web3
from web3._utils.abi import get_abi_output_types
from web3.types import BlockIdentifier

from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
    from rotkehlchen.chain.ethereum.types import WeightedNode

WEB3 = Web3()


class EthereumContract(NamedTuple):
    address: ChecksumEvmAddress
    abi: List[Dict[str, Any]]
    deployed_block: int

    def call(
            self,
            ethereum: 'EthereumManager',
            method_name: str,
            arguments: Optional[List[Any]] = None,
            call_order: Optional[Sequence['WeightedNode']] = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        return ethereum.call_contract(
            contract_address=self.address,
            abi=self.abi,
            method_name=method_name,
            arguments=arguments,
            call_order=call_order,
            block_identifier=block_identifier,
        )

    def get_logs(
            self,
            ethereum: 'EthereumManager',
            event_name: str,
            argument_filters: Dict[str, Any],
            from_block: int,
            to_block: Union[int, Literal['latest']] = 'latest',
            call_order: Optional[Sequence['WeightedNode']] = None,
    ) -> Any:
        return ethereum.get_logs(
            contract_address=self.address,
            abi=self.abi,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
            call_order=call_order,
        )

    def encode(self, method_name: str, arguments: Optional[List[Any]] = None) -> str:
        contract = WEB3.eth.contract(address=self.address, abi=self.abi)
        return contract.encodeABI(method_name, args=arguments if arguments else [])

    def decode(
            self,
            result: Decodable,
            method_name: str,
            arguments: Optional[List[Any]] = None,
    ) -> Tuple[Any, ...]:
        contract = WEB3.eth.contract(address=self.address, abi=self.abi)
        fn_abi = contract._find_matching_fn_abi(
            fn_identifier=method_name,
            args=arguments if arguments else [],
        )
        output_types = get_abi_output_types(fn_abi)
        return WEB3.codec.decode_abi(output_types, result)

    def decode_event(
            self,
            tx_log: 'EthereumTxReceiptLog',
            event_name: str,
            argument_names: Sequence[str],
    ) -> Tuple[List, List]:
        """Decodes an event by finding the event ABI in the given contract's abi

        Perhaps we can have a faster version of this method where instead of name
        and argument names we just give the index of event abi in the list if we know it
        """
        contract = WEB3.eth.contract(address=self.address, abi=self.abi)
        event_abi = contract._find_matching_event_abi(
            event_name=event_name,
            argument_names=argument_names,
        )
        return decode_event_data_abi(tx_log=tx_log, event_abi=event_abi)  # type: ignore
