from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from eth_typing.abi import Decodable
from web3 import Web3
from web3._utils.abi import get_abi_output_types

from rotkehlchen.typing import ChecksumEthAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName

WEB3 = Web3()


class EthereumContract(NamedTuple):
    address: ChecksumEthAddress
    abi: List[Dict[str, Any]]
    deployed_block: int

    def call(
            self,
            ethereum: 'EthereumManager',
            method_name: str,
            arguments: Optional[List[Any]] = None,
            call_order: Optional[Sequence['NodeName']] = None,
    ) -> Any:
        return ethereum.call_contract(
            contract_address=self.address,
            abi=self.abi,
            method_name=method_name,
            arguments=arguments,
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
