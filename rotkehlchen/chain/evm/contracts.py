import json
import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypeVar, overload

from eth_abi.exceptions import DecodingError
from eth_utils import to_checksum_address
from eth_utils.abi import get_abi_output_types
from web3 import Web3
from web3._utils.contracts import find_matching_event_abi
from web3.exceptions import Web3ValueError

from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eth_typing.abi import ABI, Decodable
    from web3.contract.base_contract import BaseContractFunction
    from web3.types import BlockIdentifier

    from rotkehlchen.chain.ethereum.types import ETHEREUM_KNOWN_ABI
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.chain.optimism.types import OPTIMISM_KNOWN_ABI
    from rotkehlchen.types import ChainID, ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
WEB3 = Web3()


_WEB3_CONTRACT_CACHE: dict[tuple[ChecksumEvmAddress, int], Any] = {}


@lru_cache(maxsize=1024)
def _split_tuple_components(tuple_type: str) -> list[str]:
    """Split a collapsed abi tuple type into the types of its components.

    '(bool,address,(uint256,string))' -> ['bool', 'address', '(uint256,string)']

    Cached since an array of structs re-splits the same type once per element and the
    types come from a fixed set of abis. The result is only ever read, never mutated.
    """
    components: list[str] = []
    depth, start, inner = 0, 0, tuple_type[1:-1]
    for idx, char in enumerate(inner):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            components.append(inner[start:idx])
            start = idx + 1

    if len(last := inner[start:]) != 0:
        components.append(last)

    return components


def _checksum_address_output(value: Any, output_type: str) -> Any:
    """Checksum the address typed parts of one decoded output value.

    Recurses through arrays of any dimension and through tuples (structs) at any nesting
    depth, since either can hold addresses.
    """
    if output_type == 'address':
        return to_checksum_address(value)

    if output_type.endswith(']'):
        # an abi array type spells its outermost dimension last, so stripping the trailing
        # [] or [n] gives the element type. Keep whatever container the codec produced
        inner_type = output_type[:output_type.rindex('[')]
        return type(value)(_checksum_address_output(item, inner_type) for item in value)

    return tuple(  # a tuple (struct), which the codec decodes into a plain python tuple
        _checksum_address_output(item, component_type) if 'address' in component_type else item
        for item, component_type in zip(
            value,
            _split_tuple_components(output_type),
            strict=True,
        )
    )


def checksum_decoded_addresses(
        values: tuple[Any, ...],
        output_types: list[str],
) -> tuple[Any, ...]:
    """Checksum any address typed value decoded from a contract call.

    web3's raw abi codec returns addresses lowercased, unlike its higher level contract api.
    Decoders feed these straight into token creation and asset identifiers are compared
    exactly, so a lowercased address here builds an identifier that never matches the
    canonical one. Everything downstream is annotated ChecksumEvmAddress already.

    An address can sit at any nesting depth of an array or a tuple (struct), so all of those
    are walked. `address` only ever appears in an abi type as the elementary type itself, so
    a substring check is enough to tell an output that needs walking from one that does not.
    """
    if not any('address' in output_type for output_type in output_types):
        return values  # nothing to do, which is the common case

    return tuple(
        _checksum_address_output(value, output_type)
        if 'address' in output_type else value
        for value, output_type in zip(values, output_types, strict=False)
    )


def _get_web3_contract(address: ChecksumEvmAddress, abi: ABI) -> Any:
    """Get or create a cached Web3 contract object keyed by (address, id(abi)).
    ABI objects are long-lived constants so id() is a stable key."""
    if (cached := _WEB3_CONTRACT_CACHE.get(key := (address, id(abi)))) is not None:
        return cached

    contract = WEB3.eth.contract(address=address, abi=abi)
    _WEB3_CONTRACT_CACHE[key] = contract
    return contract


class EvmContract(NamedTuple):
    address: ChecksumEvmAddress
    abi: ABI
    deployed_block: int = 0  # many times this is not needed

    def call(
            self,
            node_inquirer: EvmNodeInquirer,
            method_name: str,
            arguments: list[Any] | None = None,
            call_order: Sequence[WeightedNode] | None = None,
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

    def get_logs(
            self,
            node_inquirer: EvmNodeInquirer,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            call_order: Sequence[WeightedNode] | None = None,
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
        contract = _get_web3_contract(address=self.address, abi=self.abi)
        return contract.encode_abi(method_name, args=arguments or [])

    def decode(
            self,
            result: Decodable,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> tuple[Any, ...]:
        """Decodes the result of a contract call given the method name and arguments

        May raise:
            DeserializationError: If the decoding fails
        """
        contract = _get_web3_contract(address=self.address, abi=self.abi)
        fn_abi = contract._find_matching_fn_abi(
            method_name,
            *(arguments or []),
        )
        output_types = get_abi_output_types(fn_abi)
        try:
            values = WEB3.codec.decode(output_types, result)
        except DecodingError as e:
            raise DeserializationError(
                f'Failed to decode the {method_name} result of contract {self.address} '
                f'as {output_types} due to {e!s}',
            ) from e

        return checksum_decoded_addresses(values=values, output_types=output_types)

    def decode_event(
            self,
            tx_log: EvmTxReceiptLog,
            event_name: str,
            argument_names: Sequence[str] | None,
    ) -> tuple[list, list]:
        """Decodes an event by finding the event ABI in the given contract's abi

        Perhaps we can have a faster version of this method where instead of name
        and argument names we just give the index of event abi in the list if we know it

        TODO: Look at this method too as the more standard way: https://web3py.readthedocs.io/en/stable/web3.contract.html#web3.contract.ContractEvents.myEvent
        """
        event_abi = find_matching_event_abi(
            abi=self.abi,
            event_name=event_name,
            argument_names=argument_names,
        )
        return decode_event_data_abi(tx_log=tx_log, event_abi=event_abi)

    def decode_input_data(self, input_data: bytes) -> tuple[BaseContractFunction, dict[str, Any]]:
        """Decodes the input data of a contract call. Returns a tuple of the function
        selector and the decoded arguments.

        May raise:
            DeserializationError: If the decoding fails
        """
        contract = _get_web3_contract(address=self.address, abi=self.abi)
        try:
            return contract.decode_function_input(input_data)
        except Web3ValueError as e:
            raise DeserializationError(f'Failed to decode contract input data {input_data!r} due to {e!s}') from e  # noqa: E501


T = TypeVar('T', bound='ChainID')


class EvmContracts[T: 'ChainID']:
    """A class allowing to query contract data for an Evm Chain. addresses and ABIs.

    Some very frequently used abis are saved as class attributes in order to avoid
    multiple DB reads and json importing. Class attributes to not duplicate across all evm chains
    """

    erc20_abi: ABI
    erc721_abi: ABI
    univ1lp_abi: ABI

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
                    deployed_block=result[1] or 0,
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
            deployed_block=result[2] or 0,
        )

    def contract(self, address: ChecksumEvmAddress) -> EvmContract:
        """Gets details of an evm contract from the global DB by address

        Missing contract is a programming error and should never happen.
        """
        contract = self.contract_by_address(address=address, fallback_to_packaged_db=True)
        assert contract, f'No contract data for {address} found at chain {self.chain_id.to_name()}'
        return contract

    @classmethod
    def abi_or_none(
            cls,
            name: str,
            fallback_to_packaged_db: bool = False,
    ) -> ABI | None:
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
    def abi(self: EvmContracts[Literal[ChainID.ETHEREUM]], name: ETHEREUM_KNOWN_ABI) -> ABI:
        ...

    @overload
    def abi(self: EvmContracts[Literal[ChainID.OPTIMISM]], name: OPTIMISM_KNOWN_ABI) -> ABI:
        ...

    @overload
    def abi(self: EvmContracts[Literal[ChainID.POLYGON_POS, ChainID.ARBITRUM_ONE, ChainID.BASE, ChainID.HYPERLIQUID, ChainID.GNOSIS, ChainID.SCROLL, ChainID.BINANCE_SC, ChainID.MONAD, ChainID.SONIC, ChainID.ROBINHOOD]], name: Literal['']) -> ABI:  # noqa: E501
        ...

    def abi(self, name: str) -> ABI:
        """Gets abi of an evm contract from the abi json file

        Missing abi is a programming error and should never happen
        """
        abi = self.abi_or_none(name=name, fallback_to_packaged_db=True)
        assert abi, f'No abi for {name} found'
        return abi
