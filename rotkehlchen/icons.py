import itertools
import logging
from pathlib import Path
from typing import Optional

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver, asset_type_mapping
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.typing import AssetType
from rotkehlchen.utils.hashing import file_md5

log = logging.getLogger(__name__)


class IconManager():
    """
    Manages the icons for all the assets of the application

    The get_icon() and the periodic task of query_uncached_icons_batch() may at
    a point query the same icon but that's fine and not worth of locking mechanism as
    it should be rather rare and worst case scenario once in a blue moon we waste
    an API call. In the end the right file would be written on disk.
"""

    def __init__(self, data_dir: Path, coingecko: Coingecko) -> None:
        self.icons_dir = data_dir / 'icons'
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)

    def iconfile_path(self, asset: Asset, size: Literal['thumb', 'small', 'large']) -> Path:
        return self.icons_dir / f'{asset.identifier}_{size}.png'

    def iconfile_md5(
            self,
            asset: Asset,
            size: Literal['thumb', 'small', 'large'],
    ) -> Optional[str]:
        path = self.iconfile_path(asset, size)
        if not path.is_file():
            return None

        return file_md5(path)

    def _query_coingecko_for_icon(self, asset: Asset) -> bool:
        """Queries coingecko for icons of an asset

        If query was okay it returns True, else False
        """
        try:
            data = self.coingecko.asset_data(asset)
        except RemoteError as e:
            log.warning(
                f'Problem querying coingecko for asset data of {asset.identifier}: {str(e)}',
            )

            return False

        for size in ('thumb', 'small', 'large'):
            url = getattr(data.images, size)
            try:
                response = requests.get(url)
            except requests.exceptions.RequestException:
                # Any problem getting the image skip it: https://github.com/rotki/rotki/issues/1370
                continue

            with open(self.iconfile_path(asset, size), 'wb') as f:  # type: ignore
                f.write(response.content)

        return True

    def get_icon(
            self,
            asset: Asset, given_size: Literal['thumb', 'small', 'large'],
    ) -> Optional[bytes]:
        """Returns the byte data of the requested icon

        If the icon can't be found it returns None.

        If the icon is found cached locally it's returned directly.

        If not,all icons of the asset are queried from coingecko and cached
        locally before the requested data are returned.
        """
        if not asset.has_coingecko():
            return None

        needed_path = self.iconfile_path(asset, given_size)
        if needed_path.is_file():
            with open(needed_path, 'rb') as f:
                image_data = f.read()
            return image_data

        # else query coingecko for the icons and cache all of them
        if self._query_coingecko_for_icon(asset) is False:
            return None

        with open(needed_path, 'rb') as f:
            image_data = f.read()
        return image_data

    def query_uncached_icons_batch(self, batch_size: int) -> bool:
        """Queries a batch of uncached icons for assets

        Returns true if there is more icons left to cache after this batch.
        """
        coingecko_integrated_assets = []

        for identifier, asset_data in AssetResolver().assets.items():
            asset_type = asset_type_mapping[asset_data['type']]
            if asset_type != AssetType.FIAT and asset_data['coingecko'] != '':
                coingecko_integrated_assets.append(identifier)

        cached_assets = [
            str(x.name)[:-10] for x in self.icons_dir.glob('*_thumb.png') if x.is_file()
        ]

        uncached_assets = set(coingecko_integrated_assets) - set(cached_assets)
        log.info(
            f'Periodic task to query coingecko for {batch_size} uncached asset icons. '
            f'Uncached assets: {len(uncached_assets)}. Cached assets: {len(cached_assets)}',
        )
        for asset_name in itertools.islice(uncached_assets, batch_size):
            self._query_coingecko_for_icon(Asset(asset_name))

        return len(uncached_assets) > batch_size

    def periodically_query_icons_until_all_cached(
            self,
            batch_size: int,
            sleep_time_secs: float,
    ) -> None:
        """Periodically query all uncached icons until we have icons cached for all
        of the known assets that have coingecko integration"""
        if batch_size == 0:
            return

        while True:
            carry_on = self.query_uncached_icons_batch(batch_size=batch_size)
            if not carry_on:
                break
            gevent.sleep(sleep_time_secs)
