import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests
from ens.utils import normal_name_to_hash
from eth_utils import to_checksum_address
from requests.exceptions import RequestException
from web3 import Web3

from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, ETH_PROTOCOLS_CACHE_REFRESH
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_last_queried_ts_by_key
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, GeneralCacheType
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# TODO: remove this once web3.py updates ENS library for supporting multichain
# https://github.com/ethereum/web3.py/issues/1839
ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS = [
    {
        'constant': True,
        'inputs': [
            {
                'name': 'node',
                'type': 'bytes32',
            },
            {
                'name': 'coinType',
                'type': 'uint256',
            },
        ],
        'name': 'addr',
        'outputs': [
            {
                'name': 'ret',
                'type': 'bytes',
            },
        ],
        'payable': False,
        'type': 'function',
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


def get_decimals(asset: CryptoAsset) -> int:
    """
    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    if asset.identifier == 'ETH':
        return 18
    try:
        token = asset.resolve_to_evm_token()
    except UnknownAsset as e:
        raise UnsupportedAsset(asset.identifier) from e

    return token.decimals


def asset_normalized_value(amount: int, asset: CryptoAsset) -> FVal:
    """Takes in an amount and an asset and returns its normalized value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    return token_normalized_value_decimals(amount, get_decimals(asset))


def asset_raw_value(amount: FVal, asset: CryptoAsset) -> int:
    """Takes in an amount and an asset and returns its raw(wei equivalent) value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    return token_raw_value_decimals(amount, get_decimals(asset))


def generate_address_via_create2(
        address: str,
        salt: str,
        init_code: str,
        is_init_code_hashed: bool = False,
) -> ChecksumEvmAddress:
    """
    Python implementation of CREATE2 opcode.

    Given an address (deployer), a salt and an init code (contract creation
    bytecode), returns the expected contract address once it is deployed.

    If `is_init_code_hashed` is True, keccak hashing is not performed on `init_code`.

    Pseudocode:
        keccak256(0xff ++ address ++ salt ++ keccak256(init_code))[12:]

    EIP-1014:
    https://github.com/ethereum/EIPs/blob/master/EIPS/eip-1014.md

    May raise:
    - DeserializationError
    """
    computed_init_code = hexstring_to_bytes(init_code) if is_init_code_hashed is True else Web3.keccak(hexstring_to_bytes(init_code))  # noqa: E501
    contract_address = Web3.keccak(
        hexstring_to_bytes('0xff') +
        hexstring_to_bytes(address) +
        hexstring_to_bytes(salt) +
        computed_init_code,
    )[12:].hex()
    return to_checksum_address(contract_address)


def ethaddress_to_asset(address: ChecksumEvmAddress) -> Optional[CryptoAsset]:
    """Takes an ethereum address and returns a token/asset for it

    Checks for special cases like the special ETH address used in some protocols
    """
    if address == ETH_SPECIAL_ADDRESS:
        return A_ETH.resolve_to_crypto_asset()

    try:
        asset = EvmToken(ethaddress_to_identifier(address))
    except (UnknownAsset, WrongAssetType):
        log.error(f'Could not find asset/token for address {address}')
        return None

    return asset


def should_update_protocol_cache(cache_key: GeneralCacheType, *args: str) -> bool:
    """
    Checks if the last time the cache_key was queried is far enough to trigger
    the process of querying it again.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        last_update_ts = globaldb_get_general_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=[cache_key, *args],
        )
    return ts_now() - last_update_ts >= ETH_PROTOCOLS_CACHE_REFRESH


def try_download_ens_avatar(
        eth_inquirer: 'EthereumInquirer',
        avatars_dir: Path,
        ens_name: str,
) -> None:
    """
    Handles ens avatar downloading.
    1. Checks whether given ens name has an avatar set
    2. If it does, downloads the avatar and saves it in `avatars_dir`
    3. Updates last avatar and checks timestamp for the given ens name

    May raise:
    - RemoteError if failed to query chain
    """
    avatar_url = eth_inquirer.contracts.contract('ENS_PUBLIC_RESOLVER_2').call(
        node_inquirer=eth_inquirer,
        method_name='text',
        arguments=[normal_name_to_hash(ens_name), 'avatar'],
    )
    with eth_inquirer.database.conn.write_ctx() as cursor:
        cursor.execute(  # Set timestamp of the last update of the avatar
            'UPDATE ens_mappings SET last_avatar_update=? WHERE ens_name=?',
            (ts_now(), ens_name),
        )
    if avatar_url == '':
        return  # Avatar is not set

    try:
        avatar = requests.get(avatar_url, timeout=DEFAULT_TIMEOUT_TUPLE).content
    except RequestException as e:
        log.error(f'Got error {str(e)} during querying ens avatar for {ens_name}.')
        return

    avatars_dir.mkdir(exist_ok=True)  # Ensure that the avatars directory exists
    with open(avatars_dir / f'{ens_name}.png', 'wb') as f:
        f.write(avatar)
