import json
import logging
from typing import TYPE_CHECKING, Iterator

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, GeneralCacheType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def ilk_cache_foreach(cursor: 'DBCursor') -> Iterator[tuple[str, CryptoAsset, ChecksumEvmAddress]]:
    """Reads the ilk cache from the globalDB and yields at each iteration of the cursor"""
    cache_prefix = GeneralCacheType.MAKERDAO_VAULT_ILK.serialize()
    len_prefix = len(cache_prefix)
    cursor.execute(
        'SELECT key, value from general_cache WHERE key LIKE ?',
        (f'{cache_prefix}%',),
    )
    for cache_key, entry in cursor:
        ilk = cache_key[len_prefix:]
        try:
            info = json.loads(entry)
        except json.JSONDecodeError:
            log.error(f'Ilk {ilk} cache value {entry} could not be deserialized as json. Skipping')  # noqa: E501
            continue

        try:
            underlying_asset = Asset(info[0]).resolve_to_crypto_asset()
        except (WrongAssetType, UnknownAsset) as e:
            log.error(f'Ilk {ilk} asset {info[0]} could not be initialized due to {str(e)}. Skipping')  # noqa: E501
            continue

        yield ilk, underlying_asset, info[1]
