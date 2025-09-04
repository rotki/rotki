import logging
from collections.abc import Sequence
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests
from ens.abis import PUBLIC_RESOLVER_2 as ENS_RESOLVER_ABI
from ens.utils import normal_name_to_hash
from eth_utils import to_checksum_address
from requests.exceptions import RequestException
from web3 import Web3

from rotkehlchen.assets.asset import CryptoAsset, EvmToken, SolanaToken
from rotkehlchen.constants.assets import A_BSC_BNB, A_ETH, A_XDAI
from rotkehlchen.constants.resolver import EVM_CHAIN_DIRECTIVE
from rotkehlchen.constants.timing import ETH_PROTOCOLS_CACHE_REFRESH, HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_last_queried_ts_by_key,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import UNIQUE_CACHE_KEYS, CacheType, ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.opensea import Opensea


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ENS_METADATA_URL = 'https://metadata.ens.domains/mainnet'
MULTICALL_CHUNKS = 20


def token_normalized_value_decimals(token_amount: int, token_decimals: int | None) -> FVal:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return token_amount / (FVal(10) ** FVal(token_decimals))


def normalized_fval_value_decimals(amount: FVal, decimals: int) -> FVal:
    return amount / (FVal(10) ** FVal(decimals))


def token_raw_value_decimals(token_amount: FVal, token_decimals: int | None) -> int:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return (token_amount * (FVal(10) ** FVal(token_decimals))).to_int(exact=False)


def token_normalized_value(
        token_amount: int,
        token: EvmToken | SolanaToken,
) -> FVal:
    return token_normalized_value_decimals(token_amount, token.decimals)


def get_decimals(asset: CryptoAsset) -> int:
    """
    May raise:
    - UnsupportedAsset if the given asset is not a native token or an ERC20 token
    """
    if asset in (A_ETH, A_XDAI, A_BSC_BNB):
        return 18
    try:
        token = asset.resolve_to_evm_token()
    except UnknownAsset as e:
        raise UnsupportedAsset(asset.identifier) from e

    return token.get_decimals()


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


def should_update_protocol_cache(
        userdb: 'DBHandler',
        cache_key: CacheType,
        args: Sequence[str] | None = None,
) -> bool:
    """
    Checks if the last time the cache_key was queried is far enough to trigger
    the process of querying it again.
    """
    args = args if args is not None else []
    now = ts_now()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if cache_key in UNIQUE_CACHE_KEYS:
            last_update_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
                cursor=cursor,
                key_parts=(cache_key, *args),  # type: ignore  # cache_key needs type specification here
            )
        else:
            last_update_ts = globaldb_get_general_cache_last_queried_ts_by_key(
                cursor=cursor,
                key_parts=(cache_key, *args),  # type: ignore  # cache_key needs type specification here
            )

    if last_update_ts == Timestamp(0):
        return True  # Update new protocols regardless of whether we just had a db upgrade.

    with userdb.conn.read_ctx() as cursor:
        if (
            (last_upgrade_ts := userdb.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.LAST_DB_UPGRADE,
            )) is not None and
            (now - last_upgrade_ts) < HOUR_IN_SECONDS * 3
        ):
            return False  # if we had recent DB upgrade don't refresh

    return now - last_update_ts >= ETH_PROTOCOLS_CACHE_REFRESH


def _get_response_image(response: requests.adapters.Response) -> bytes:
    """
    Check the response contains an image content type.
    If not raises a RemoteError. If yes it returns the image bytes
    """
    if response.status_code != HTTPStatus.OK:
        raise RemoteError(f'{response.url} failed with {response.status_code}')
    content_type = response.headers.get('Content-Type')
    if (
        content_type is None or
        (content_type != 'null' and content_type.startswith('image') is False)  # cloudflare removes the content type and sets it to null  # noqa: E501
    ):
        raise RemoteError(f'{response.url} return non-image content type {content_type}')

    return response.content


def try_download_ens_avatar(
        eth_inquirer: 'EthereumInquirer',
        opensea: Optional['Opensea'],
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
    resolver_addr, _ = eth_inquirer.get_ens_resolver_addr(ens_name)
    if resolver_addr is None:
        log.error(f'Could not find ENS resolver address for {ens_name}')
        return

    avatar_url = eth_inquirer.call_contract(
        contract_address=resolver_addr,
        abi=ENS_RESOLVER_ABI,
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

    avatar = None
    if avatar_url.startswith(EVM_CHAIN_DIRECTIVE):  # an NFT is set
        try:  # Let's try first ENS app's own metadata
            response = requests.get(f'{ENS_METADATA_URL}/avatar/{ens_name}', timeout=CachedSettings().get_timeout_tuple())  # noqa: E501
            avatar = _get_response_image(response)
        except (RequestException, RemoteError) as e:  # Try opensea -- if we got it
            log.error(f'Got error {e!s} during querying ENS app for NFT avatar for {ens_name}. May fall back to opensea')  # noqa: E501
            if opensea is None:
                return  # no opensea
            avatar_url = opensea.get_nft_image(avatar_url)
            if avatar_url is None:
                return  # no luck with opensea
            # proceed to query the new avatar url

    if avatar is None:  # we have not populated it via an NFT query above yet
        try:
            response = requests.get(avatar_url, timeout=CachedSettings().get_timeout_tuple())
            avatar = _get_response_image(response)
        except (RequestException, RemoteError) as e:
            log.error(f'Got error {e!s} while querying ens avatar {avatar_url} for {ens_name}.')
            return

    avatars_dir.mkdir(exist_ok=True)  # Ensure that the avatars directory exists
    Path(avatars_dir / f'{ens_name}.png').write_bytes(avatar)
