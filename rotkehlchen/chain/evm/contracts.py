import json
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Generic, Literal, NamedTuple, TypeVar, overload

from eth_typing.abi import Decodable
from web3 import Web3
from web3._utils.abi import get_abi_output_types
from web3.types import BlockIdentifier

from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.types import ETHEREUM_KNOWN_ABI
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.chain.optimism.types import OPTIMISM_KNOWN_ABI

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
WEB3 = Web3()


class EvmContract(NamedTuple):
    address: ChecksumEvmAddress
    abi: list[dict[str, Any]]
    deployed_block: int

    def call(
            self,
            node_inquirer: 'EvmNodeInquirer',
            method_name: str,
            arguments: list[Any] | None = None,
            call_order: Sequence['WeightedNode'] | None = None,
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
            argument_filters: dict[str, Any],
            to_block: int | Literal['latest'] = 'latest',
            call_order: Sequence['WeightedNode'] | None = None,
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
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            call_order: Sequence['WeightedNode'] | None = None,
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

    def encode(self, method_name: str, arguments: list[Any] | None = None) -> str:
        contract = WEB3.eth.contract(address=self.address, abi=self.abi)
        return contract.encodeABI(method_name, args=arguments if arguments else [])

    def decode(
            self,
            result: Decodable,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> tuple[Any, ...]:
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
            argument_names: Sequence[str] | None,
    ) -> tuple[list, list]:
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

    Some very frequently used abis are saved as class attributes in order to avoid
    multiple DB reads and json importing. Class attributes to not duplicate across all evm chains
    """

    erc20_abi: list[dict[str, Any]]
    erc721_abi: list[dict[str, Any]]
    univ1lp_abi: list[dict[str, Any]]

    def __init__(self, chain_id: T) -> None:
        self.chain_id = chain_id

    @classmethod
    def initialize_common_abis(cls) -> None:
        """Initialize common abi class attributes. Should be called only once at initialization"""
        cls.erc20_abi = cls.abi_or_none(name='ERC20_TOKEN', fallback_to_packaged_db=True)  # type: ignore  # abi should exist in the DB # noqa: E501, RUF100
        cls.erc721_abi = cls.abi_or_none('ERC721_TOKEN', fallback_to_packaged_db=True)  # type: ignore  # abi should exist in the DB # noqa: E501, RUF100
        cls.univ1lp_abi = cls.abi_or_none('UNIV1_LP', fallback_to_packaged_db=True)  # type: ignore  # abi should exist in the DB # noqa: E501, RUF100

    def contract_by_address(
            self,
            address: ChecksumEvmAddress,
            fallback_to_packaged_db: bool = True,
    ) -> EvmContract | None:
        """
        Returns contract data by address if found. Can fall back to packaged global db if
        not found in the normal global DB
        """
        globaldb = GlobalDBHandler()
        with globaldb.conn.read_ctx() as cursor:
            bindings = (self.chain_id.serialize_for_db(), address)
            result = cursor.execute(
                'SELECT contract_abi.value, contract_data.deployed_block FROM '
                'contract_data LEFT JOIN contract_abi ON contract_data.abi=contract_abi.id '
                'WHERE contract_data.chain_id=? AND contract_data.address=?',
                bindings,
            ).fetchone()
            if result is not None:
                return EvmContract(
                    address=address,
                    abi=json.loads(result[0]),  # not handling json error -- assuming DB consistency  # noqa: E501
                    deployed_block=result[1] if result[1] else 0,
                )

            if fallback_to_packaged_db is False:
                return None

        # Try to find the contract in the packaged db
        with globaldb.packaged_db_conn().read_ctx() as packaged_cursor:
            log.debug(f'Using packaged globaldb to get contract {address} information')
            result = packaged_cursor.execute(
                'SELECT contract_data.address, contract_data.chain_id, '
                'contract_data.deployed_block, contract_abi.name, contract_abi.value FROM '
                'contract_data LEFT JOIN contract_abi ON '
                'contract_data.abi=contract_abi.id WHERE contract_data.chain_id=? AND '
                'contract_data.address=?',
                bindings,
            ).fetchone()

        if result is None:
            log.debug(f"Couldn't find contract {address} in the packaged globaldb")
            return None

        # Copy the contract to the global db
        abi_id = globaldb.get_or_write_abi(
            serialized_abi=result[4],
            abi_name=result[3],
        )
        with globaldb.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR IGNORE INTO contract_data(address, chain_id, abi, deployed_block) '
                'VALUES (?, ?, ?, ?)',
                (result[0], result[1], abi_id, result[2]),
            )
            log.debug(f'Saved contract {address} in the globaldb')
        return EvmContract(
            address=address,
            abi=json.loads(result[4]),  # not handling json error -- assuming DB consistency
            deployed_block=result[2] if result[2] else 0,
        )

    def contract(self, address: ChecksumEvmAddress) -> EvmContract:
        """Gets details of an evm contract from the global DB by address

        Missing contract is a programming error and should never happen.
        """
        contract = self.contract_by_address(address=address, fallback_to_packaged_db=True)
        assert contract, f'No contract data for {address} found'
        return contract

    @classmethod
    def abi_or_none(
            cls,
            name: str,
            fallback_to_packaged_db: bool = False,
    ) -> list[dict[str, Any]] | None:
        """Gets abi of an evm contract from the abi json file and optionally falls back to
        the packaged db if the abi is not found.

        Returns None if missing
        """
        globaldb = GlobalDBHandler()
        with globaldb.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT value FROM contract_abi WHERE name=?',
                (name,),
            ).fetchone()
            if result is not None:
                return json.loads(result[0])

            if fallback_to_packaged_db is False:
                return None

        # Try to find the ABI in the packaged db
        with globaldb.packaged_db_conn().read_ctx() as packaged_cursor:
            log.debug(f'Using packaged globaldb to get abi {name=} information')
            result = packaged_cursor.execute(
                'SELECT value FROM contract_abi WHERE name=?',
                (name,),
            ).fetchone()
            if result is None:
                return None

        globaldb.get_or_write_abi(
            serialized_abi=result[0],
            abi_name=name,
        )

        return json.loads(result[0])

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.ETHEREUM]]', name: 'ETHEREUM_KNOWN_ABI') -> list[dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.OPTIMISM]]', name: 'OPTIMISM_KNOWN_ABI') -> list[dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.POLYGON_POS]]', name: Literal['']) -> list[dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.ARBITRUM_ONE]]', name: Literal['']) -> list[dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.BASE]]', name: Literal['']) -> list[dict[str, Any]]:  # noqa: E501
        ...

    @overload
    def abi(self: 'EvmContracts[Literal[ChainID.GNOSIS]]', name: Literal['']) -> list[dict[str, Any]]:  # noqa: E501
        ...

    def abi(self, name: str) -> list[dict[str, Any]]:
        """Gets abi of an evm contract from the abi json file

        Missing abi is a programming error and should never happen
        """
        abi = self.abi_or_none(name=name, fallback_to_packaged_db=True)
        assert abi, f'No abi for {name} found'
        return abi
