import itertools
import logging
import shutil
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import Optional, Set

import gevent
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.hashing import file_md5

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ALLOWED_ICON_EXTENSIONS = ('.png', '.svg', '.jpeg', '.jpg', '.webp')


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
        self.custom_icons_dir = data_dir / 'icons' / 'custom'
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        self.custom_icons_dir.mkdir(parents=True, exist_ok=True)
        self.failed_asset_ids: Set[str] = set()

    def iconfile_path(self, asset: Asset) -> Path:
        return self.icons_dir / f'{urllib.parse.quote_plus(asset.identifier)}_small.png'

    def custom_iconfile_path(self, asset: Asset) -> Optional[Path]:
        for suffix in ALLOWED_ICON_EXTENSIONS:
            asset_id_quoted = urllib.parse.quote_plus(asset.identifier)
            icon_path = self.custom_icons_dir / f'{asset_id_quoted}{suffix}'
            if icon_path.is_file():
                return icon_path

        return None

    def iconfile_md5(
            self,
            asset: Asset,
    ) -> Optional[str]:
        # First try with the custom icon path
        custom_icon_path = self.custom_iconfile_path(asset)
        if custom_icon_path is not None:
            return file_md5(custom_icon_path)

        path = self.iconfile_path(asset)
        if not path.is_file():
            return None

        return file_md5(path)

    def query_coingecko_for_icon(self, asset: Asset) -> bool:
        """Queries coingecko for icons of an asset

        If query was okay it returns True, else False
        """
        # Do not bother querying if asset is delisted. Nothing is returned.
        # we only keep delisted asset coingecko mappings since historical prices
        # can still be queried.
        if asset.identifier in DELISTED_ASSETS:
            self.failed_asset_ids.add(asset.identifier)
            return False

        try:
            data = self.coingecko.asset_data(asset)
        except (UnsupportedAsset, RemoteError) as e:
            log.warning(
                f'Problem querying coingecko for asset data of {asset.identifier}: {str(e)}',
            )
            # If a query fails (99% of fails will be 404s) don't repeat them
            self.failed_asset_ids.add(asset.identifier)
            return False

        try:
            response = self.coingecko.session.get(data.image_url, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException:
            # Any problem getting the image skip it: https://github.com/rotki/rotki/issues/1370
            return False

        if response.status_code != HTTPStatus.OK:
            return False

        with open(self.iconfile_path(asset), 'wb') as f:
            f.write(response.content)

        return True

    def get_icon(
            self,
            asset: Asset,
    ) -> Optional[bytes]:
        """Returns the byte data of the requested icon

        If the icon can't be found it returns None.

        If the icon is found cached locally it's returned directly.

        If not, all icons of the asset are queried from coingecko and cached
        locally before the requested data are returned.
        """
        # First search custom icons
        custom_icon_path = self.custom_iconfile_path(asset)
        if custom_icon_path is not None:
            with open(custom_icon_path, 'rb') as f:
                image_data = f.read()
            return image_data

        # Then our only chance is coingecko
        if not asset.has_coingecko():
            return None

        needed_path = self.iconfile_path(asset)
        if needed_path.is_file():
            with open(needed_path, 'rb') as f:
                image_data = f.read()
            return image_data

        # else query coingecko for the icons and cache all of them
        if self.query_coingecko_for_icon(asset) is False:
            return None

        if not needed_path.is_file():
            return None

        with open(needed_path, 'rb') as f:
            image_data = f.read()
        return image_data

    def query_uncached_icons_batch(self, batch_size: int) -> bool:
        """Queries a batch of uncached icons for assets

        Returns true if there is more icons left to cache after this batch.
        """
        coingecko_integrated_asset_ids = GlobalDBHandler().assets_with_coingecko_id()
        cached_asset_ids = [
            str(x.name)[:-10] for x in self.icons_dir.glob('*_small.png') if x.is_file()
        ]
        uncached_asset_ids = (
            set(coingecko_integrated_asset_ids) - set(cached_asset_ids) - self.failed_asset_ids
        )
        log.info(
            f'Periodic task to query coingecko for {batch_size} uncached asset icons. '
            f'Uncached assets: {len(uncached_asset_ids)}. Cached assets: {len(cached_asset_ids)}',
        )
        for asset_name in itertools.islice(uncached_asset_ids, batch_size):
            self.query_coingecko_for_icon(Asset(asset_name))

        return len(uncached_asset_ids) > batch_size

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

    def add_icon(self, asset: Asset, icon_path: Path) -> None:
        """Adds the icon in the custom icons directory for the asset

        Completely replaces what was there before
        """
        quoted_identifier = urllib.parse.quote_plus(asset.identifier)
        shutil.copyfile(
            icon_path,
            self.custom_icons_dir / f'{quoted_identifier}{icon_path.suffix}',
        )

    def delete_icon(self, asset: Asset) -> None:
        """
        Tries to find and delete the cache of an icon in both the custom icons
        and default icons directory.
        """
        icon_path = self.custom_iconfile_path(asset)
        if icon_path is not None:
            icon_path.unlink()

        icon_path = self.iconfile_path(asset)
        if icon_path.is_file():
            icon_path.unlink()
