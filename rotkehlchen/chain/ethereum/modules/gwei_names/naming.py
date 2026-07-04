import logging
from typing import TYPE_CHECKING

import ens
from eth_abi import decode as decode_abi
from eth_utils import to_checksum_address

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import get_chunks

from .constants import ADDR_ABI, GWEI_NAMES_ADDRESS, REVERSE_RESOLVE_METHOD

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_ADDRESSES_IN_REVERSE_GNS_QUERY = 80


def gns_reverse_lookup(
        inquirer: 'EthereumInquirer',
        addresses: list['ChecksumEvmAddress'],
) -> dict['ChecksumEvmAddress', str | None]:
    """Performs a reverse gwei name lookup on a list of addresses via multicall.

    reverseResolve returns the primary name of an address and performs the
    forward check on-chain, returning an empty string if there is no valid name.
    Returns a mapping of addresses to either a string name or None if there
    is no gwei name to be found.

    May raise:
    - RemoteError if there is a problem querying the blockchain
    """
    names: dict[ChecksumEvmAddress, str | None] = {}
    for chunk in get_chunks(lst=addresses, n=MAX_ADDRESSES_IN_REVERSE_GNS_QUERY):
        calls = [(
            GWEI_NAMES_ADDRESS,
            '0x' + (REVERSE_RESOLVE_METHOD + bytes.fromhex(address.removeprefix('0x')).rjust(32, b'\x00')).hex(),  # noqa: E501
        ) for address in chunk]
        results = inquirer.multicall_2(calls=calls, require_success=False)
        for address, result in zip(chunk, results, strict=True):
            if result[0] is False or len(result[1]) == 0:
                names[address] = None
                continue

            try:
                name = decode_abi(['string'], result[1])[0]
            except DeserializationError as e:
                log.error('Failed to decode gns reverse lookup result for %s due to %s', address, e)  # noqa: E501
                name = ''

            names[address] = name if name != '' else None

    return names


def gns_resolve(inquirer: 'EthereumInquirer', name: str) -> 'ChecksumEvmAddress | None':
    """Resolve a gwei name to an address using the ENS-compatible addr(bytes32) method.

    The token id of a name equals the uint256 of its EIP-137 namehash, so the node
    can be computed offline. Returns None if the name does not resolve.

    May raise:
    - RemoteError if there is a problem querying the blockchain
    - InputError if the given name is not a valid, normalizable name
    """
    try:
        node = ens.ENS.namehash(name)
    except ens.exceptions.InvalidName as e:
        raise InputError(f'Invalid gwei name {name}: {e!s}') from e

    try:
        address = inquirer.call_contract(
            contract_address=GWEI_NAMES_ADDRESS,
            abi=ADDR_ABI,
            method_name='addr',
            arguments=[node],
        )
    except RemoteError as e:
        log.error('Failed to resolve gwei name %s due to %s', name, e)
        return None

    if not address or address == ZERO_ADDRESS:
        return None

    return to_checksum_address(address)
