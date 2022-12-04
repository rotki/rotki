import json
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from eth_typing.abi import Decodable
from web3 import Web3
from web3._utils.abi import get_abi_output_types
from web3.types import BlockIdentifier

from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.types import ETHEREUM_KNOWN_ABI, ETHEREUM_KNOWN_CONTRACTS
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.evm.types import WeightedNode


WEB3 = Web3()


class EvmContract(NamedTuple):
    address: ChecksumEvmAddress
    abi: List[Dict[str, Any]]
    deployed_block: int

    def call(
            self,
            node_inquirer: 'EvmNodeInquirer',
            method_name: str,
            arguments: Optional[List[Any]] = None,
            call_order: Optional[Sequence['WeightedNode']] = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        return node_inquirer.call_contract(
            contract_address=self.address,
            abi=self.abi,
            method_name=method_name,
            arguments=arguments,
            call_order=call_order,
            block_identifier=block_identifier,
        )

    def get_logs_since_deployment(
            self,
            node_inquirer: 'EvmNodeInquirer',
            event_name: str,
            argument_filters: Dict[str, Any],
            to_block: Union[int, Literal['latest']] = 'latest',
            call_order: Optional[Sequence['WeightedNode']] = None,
    ) -> Any:
        return node_inquirer.get_logs(
            contract_address=self.address,
            abi=self.abi,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=self.deployed_block,
            to_block=to_block,
            call_order=call_order,
        )

    def get_logs(
            self,
            node_inquirer: 'EvmNodeInquirer',
            event_name: str,
            argument_filters: Dict[str, Any],
            from_block: int,
            to_block: Union[int, Literal['latest']] = 'latest',
            call_order: Optional[Sequence['WeightedNode']] = None,
    ) -> Any:
        return node_inquirer.get_logs(
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
            tx_log: 'EvmTxReceiptLog',
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


T = TypeVar('T', bound='ChainID')


class EvmContracts(Generic[T]):
    """A class allowing to query contract data for an Evm Chain. addresses and ABIs.

    Atm all evm chains need to have (may need to change this):
    - ERC20TOKEN
    - UNIV1_LP
    - ERC721TOKEN
    """

    def __init__(self, contracts_filename: str, abi_filename: str) -> None:
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.abi_entries: Dict[str, List[Dict[str, Any]]] = {}
        dir_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        with open(os.path.join(dir_path, 'data', contracts_filename)) as f:
            self.contracts = json.loads(f.read())

        with open(os.path.join(dir_path, 'data', abi_filename)) as f:
            self.abi_entries = json.loads(f.read())

    def contract_or_none(self, name: str) -> Optional[EvmContract]:
        """Gets details of an evm contract from the contracts json file

        Returns None if missing
        """
        contract = self.contracts.get(name, None)
        if contract is None:
            return None

        return EvmContract(
            address=contract['address'],
            abi=contract['abi'],
            deployed_block=contract['deployed_block'],
        )

    @overload
    def contract(self: 'EvmContracts[Literal[ChainID.ETHEREUM]]', name: 'ETHEREUM_KNOWN_CONTRACTS') -> EvmContract:  # noqa: E501
        ...

    @overload
    def contract(self: 'EvmContracts[Literal[ChainID.OPTIMISM]]', name: Literal['to', 'do', 'PICKLE_DILL']) -> EvmContract:  # noqa: E501
        ...

    def contract(self, name: str) -> EvmContract:
        """Gets details of an evm contract from the contracts json file

        Missing contract is a programming error and should never happen.
        """
        contract = self.contract_or_none(name)
        assert contract, f'No contract data for {name} found'
        return contract

    def abi_or_none(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Gets abi of an evm contract from the abi json file

        Returns None if missing
        """
        return self.abi_entries.get(name, None)

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.ETHEREUM]]', name: 'ETHEREUM_KNOWN_ABI') -> List[Dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.OPTIMISM]]', name: Literal['to', 'do', 'CTOKEN']) -> List[Dict[str, Any]]:  # noqa: E501
        ...

    def abi(self, name: str) -> List[Dict[str, Any]]:
        """Gets abi of an evm contract from the abi json file

        Missing abi is a programming error and should never happen
        """
        abi = self.abi_or_none(name)
        assert abi, f'No abi for {name} found'
        return abi
