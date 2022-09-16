import logging
from typing import Optional

from eth_utils import to_checksum_address
from web3 import Web3

from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

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
        try:
            token = EvmToken(asset.identifier)
        except UnknownAsset as e:
            raise UnsupportedAsset(asset.identifier) from e
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
        try:
            token = EvmToken(asset.identifier)
        except UnknownAsset as e:
            raise UnsupportedAsset(asset.identifier) from e
        decimals = token.decimals

    return token_raw_value_decimals(amount, decimals)


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


def ethaddress_to_asset(address: ChecksumEvmAddress) -> Optional[CryptoAsset]:
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
