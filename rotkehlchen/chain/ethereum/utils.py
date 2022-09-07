import logging
from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple

from eth_utils import to_checksum_address
from web3 import Web3
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import ETH_MULTICALL, ETH_MULTICALL_2, ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.types import WeightedNode
    from rotkehlchen.chain.evm.contracts import EvmContract


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# TODO: remove this once web3.py updates ENS library for supporting multichain
# https://github.com/ethereum/web3.py/issues/1839
ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS = [
    {
        "constant": True,
        "inputs": [
            {
                "name": "node",
                "type": "bytes32",
            },
            {
                "name": "coinType",
                "type": "uint256",
            },
        ],
        "name": "addr",
        "outputs": [
            {
                "name": "ret",
                "type": "bytes",
            },
        ],
        "payable": False,
        "type": "function",
    },
]
MULTICALL_CHUNKS = 20


def token_normalized_value_decimals(token_amount: int, token_decimals: Optional[int]) -> FVal:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return token_amount / (FVal(10) ** FVal(token_decimals))


def token_raw_value_decimals(token_amount: FVal, token_decimals: Optional[int]) -> int:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return (token_amount * (FVal(10) ** FVal(token_decimals))).to_int(exact=False)


def token_normalized_value(
        token_amount: int,
        token: EvmToken,
) -> FVal:
    return token_normalized_value_decimals(token_amount, token.decimals)


def asset_normalized_value(amount: int, asset: Asset) -> FVal:
    """Takes in an amount and an asset and returns its normalized value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    if asset.identifier == 'ETH':
        decimals = 18
    else:
        token = EvmToken.from_asset(asset)
        if token is None:
            raise UnsupportedAsset(asset.identifier)
        decimals = token.decimals

    return token_normalized_value_decimals(amount, decimals)


def asset_raw_value(amount: FVal, asset: Asset) -> int:
    """Takes in an amount and an asset and returns its raw(wei equivalent) value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    if asset.identifier == 'ETH':
        decimals = 18
    else:
        token = EvmToken.from_asset(asset)
        if token is None:
            raise UnsupportedAsset(asset.identifier)
        decimals = token.decimals

    return token_raw_value_decimals(amount, decimals)


def multicall(
        ethereum: 'EthereumManager',
        calls: List[Tuple[ChecksumEvmAddress, str]],
        # only here to comply with multicall_2
        require_success: bool = True,  # pylint: disable=unused-argument
        call_order: Optional[Sequence['WeightedNode']] = None,
        block_identifier: BlockIdentifier = 'latest',
        calls_chunk_size: int = MULTICALL_CHUNKS,
) -> Any:
    """Uses MULTICALL contract. Failure of one call is a failure of the entire multicall.
    source: https://etherscan.io/address/0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441#code"""
    calls_chunked = list(get_chunks(calls, n=calls_chunk_size))
    output = []
    for call_chunk in calls_chunked:
        multicall_result = ETH_MULTICALL.call(
            manager=ethereum,
            method_name='aggregate',
            arguments=[call_chunk],
            call_order=call_order,
            block_identifier=block_identifier,
        )
        _, chunk_output = multicall_result
        output += chunk_output
    return output


def multicall_2(
        ethereum: 'EthereumManager',
        calls: List[Tuple[ChecksumEvmAddress, str]],
        require_success: bool,
        call_order: Optional[Sequence['WeightedNode']] = None,
        block_identifier: BlockIdentifier = 'latest',
        # only here to comply with multicall
        calls_chunk_size: int = MULTICALL_CHUNKS,  # pylint: disable=unused-argument
) -> List[Tuple[bool, bytes]]:
    """
    Uses MULTICALL_2 contract. If require_success
    is set to False any call in the list of calls is allowed to fail.
    source: https://etherscan.io/address/0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696#code"""
    return ETH_MULTICALL_2.call(
        manager=ethereum,
        method_name='tryAggregate',
        arguments=[require_success, calls],
        call_order=call_order,
        block_identifier=block_identifier,
    )


def multicall_specific(
        ethereum: 'EthereumManager',
        contract: 'EvmContract',
        method_name: str,
        arguments: List[Any],
        call_order: Optional[Sequence['WeightedNode']] = None,
        decode_result: bool = True,
) -> Any:
    calls = [(
        contract.address,
        contract.encode(method_name=method_name, arguments=i),
    ) for i in arguments]
    output = multicall(ethereum, calls, True, call_order)
    if decode_result is False:
        return output
    return [contract.decode(x, method_name, arguments[0]) for x in output]


def generate_address_via_create2(
        address: str,
        salt: str,
        init_code: str,
) -> ChecksumEvmAddress:
    """Python implementation of CREATE2 opcode.

    Given an address (deployer), a salt and an init code (contract creation
    bytecode), returns the expected contract address once it is deployed.

    Pseudocode:
        keccak256( 0xff ++ address ++ salt ++ keccak256(init_code))[12:]

    EIP-1014:
    https://github.com/ethereum/EIPs/blob/master/EIPS/eip-1014.md

    May raise:
    - DeserializationError
    """
    contract_address = Web3.keccak(
        hexstring_to_bytes('0xff') +
        hexstring_to_bytes(address) +
        hexstring_to_bytes(salt) +
        Web3.keccak(hexstring_to_bytes(init_code)),
    )[12:].hex()
    return to_checksum_address(contract_address)


def ethaddress_to_asset(address: ChecksumEvmAddress) -> Optional[Asset]:
    """Takes an ethereum address and returns a token/asset for it

    Checks for special cases like the special ETH address used in some protocols
    """
    if address == ETH_SPECIAL_ADDRESS:
        return A_ETH

    try:
        asset = EvmToken(ethaddress_to_identifier(address))
    except UnknownAsset:
        log.error(f'Could not find asset/token for address {address}')
        return None

    return asset
