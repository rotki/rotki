import hashlib
import itertools
import logging
import shutil
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import gevent
import requests
from flask import Response, make_response

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUSetCache
from rotkehlchen.utils.hashing import file_md5

if TYPE_CHECKING is True:
    from rotkehlchen.greenlets.manager import GreenletManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ALLOWED_ICON_EXTENSIONS = ('.png', '.svg', '.jpeg', '.jpg', '.webp')


def check_if_image_is_cached(image_path: Path, match_header: Optional[str]) -> Optional[Response]:
    """Checks whether the file at `image_path` is an already cached image.

    Returns a response indicating the image has not been modified if that's the case,
    otherwise None.
    """
    md5_hash = file_md5(image_path)
    if md5_hash and match_header and match_header == md5_hash:
        # Response content unmodified
        return make_response(
            (
                b'',
                HTTPStatus.NOT_MODIFIED,
                {'mimetype': 'image/png', 'Content-Type': 'image/png'},
            ),
        )

    return None


def create_image_response(image_path: Path) -> Response:
    """
    Returns a response with the image at image_path. It assumes that the file exists
    May raise:
    - OSError if the file doesn't exists
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()

    response = make_response(
        (
            image_data,
            HTTPStatus.OK, {'mimetype': 'image/png', 'Content-Type': 'image/png'}),
    )
    response.set_etag(hashlib.md5(image_data).hexdigest())
    return response


def maybe_create_image_response(image_path: Optional[Path]) -> Response:
    """Checks whether the file at `image_path` exists.

    Returns a response with the image if it exists, otherwise a NOT FOUND response.
    """
    if image_path is None or image_path.is_file() is False:
        return make_response(
            (
                b'',
                HTTPStatus.NOT_FOUND, {'mimetype': 'image/png', 'Content-Type': 'image/png'},
            ),
        )

    return create_image_response(image_path)


class IconManager:
    """
    Manages the icons for all the assets of the application

    The get_icon() and the periodic task of query_uncached_icons_batch() may at
    a point query the same icon but that's fine and not worth of locking mechanism as
    it should be rather rare and worst case scenario once in a blue moon we waste
    an API call. In the end the right file would be written on disk.
    """

    def __init__(
            self,
            data_dir: Path,
            coingecko: Coingecko,
            greenlet_manager: 'GreenletManager',
    ) -> None:
        self.icons_dir = data_dir / 'icons'
        self.custom_icons_dir = self.icons_dir / 'custom'
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        self.custom_icons_dir.mkdir(parents=True, exist_ok=True)
        self.failed_asset_ids: LRUSetCache[str] = LRUSetCache(maxsize=256)
        self.greenlet_manager = greenlet_manager

    def iconfile_path(self, asset: Asset) -> Path:
        return self.icons_dir / f'{urllib.parse.quote_plus(asset.identifier)}_small.png'

    def custom_iconfile_path(self, asset: Asset) -> Optional[Path]:
        for suffix in ALLOWED_ICON_EXTENSIONS:
            asset_id_quoted = urllib.parse.quote_plus(asset.identifier)
            icon_path = self.custom_icons_dir / f'{asset_id_quoted}{suffix}'
            if icon_path.is_file():
                return icon_path

        return None

    def asset_icon_path(
            self,
            asset: Asset,
    ) -> Optional[Path]:
        # First try with the custom icon path
        custom_icon_path = self.custom_iconfile_path(asset)
        if custom_icon_path is not None:
            return custom_icon_path

        path = self.iconfile_path(asset)
        if not path.is_file():
            return None

        return path

    def query_coingecko_for_icon(self, asset: Asset, coingecko_id: str) -> bool:
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
            data = self.coingecko.asset_data(coingecko_id)
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
    ) -> tuple[Optional[Path], bool]:
        """
        Returns the file path of the requested icon and whether it has been scheduled to be
        queried if the file is not in the system and is possible to obtain it from coingecko.

        If the icon can't be found it returns None.

        If the icon is found cached locally it's returned directly.

        If not, all icons of the asset are queried from coingecko and cached
        locally before the requested data are returned.
        """
        if asset.identifier in self.failed_asset_ids:
            return None, False

        # check if the asset is in a collection
        collection_main_asset_id = GlobalDBHandler().get_collection_main_asset(asset.identifier)
        asset_to_query_icon = asset

        if collection_main_asset_id is not None:
            # get the asset with the lowest lex order
            asset_to_query_icon = Asset(collection_main_asset_id)

        needed_path = self.iconfile_path(asset_to_query_icon)
        if needed_path.is_file() is True:
            return needed_path, False

        # Then our only chance is coingecko
        # If we don't have the image check if this is a valid coingecko asset
        try:
            asset_to_query_icon = asset_to_query_icon.resolve_to_asset_with_oracles()
            coingecko_id = asset_to_query_icon.to_coingecko()
        except (UnknownAsset, WrongAssetType, UnsupportedAsset):
            return None, False

        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Coingecko icon query',
            exception_is_error=False,
            method=self.query_coingecko_for_icon,
            asset=asset_to_query_icon,
            coingecko_id=coingecko_id,
        )
        return None, True

    def _assets_with_coingecko_id(self) -> dict[str, str]:
        """Create a mapping of all the assets identifiers to their coingecko id if it is set"""
        querystr = """
        SELECT A.identifier, B.coingecko from assets as A JOIN common_asset_details as B
        ON B.identifier = A.identifier WHERE A.type != ? AND B.coingecko IS NOT NULL AND B.coingecko != ""
        """  # noqa: E501
        assets_mappings: dict[str, str] = {}
        with GlobalDBHandler().conn.read_ctx() as cursor:
            fiat_type = AssetType.FIAT.serialize_for_db()
            cursor.execute(querystr, [fiat_type])
            for entry in cursor:
                assets_mappings[entry[0]] = entry[1]
        return assets_mappings

    def query_uncached_icons_batch(self, batch_size: int) -> bool:
        """Queries a batch of uncached icons for assets

        Returns true if there is more icons left to cache after this batch.
        """
        coingecko_integrated_asset = self._assets_with_coingecko_id()
        coingecko_integrated_asset_ids = set(coingecko_integrated_asset.keys())
        cached_asset_ids = [
            str(x.name)[:-10] for x in self.icons_dir.glob('*_small.png') if x.is_file()
        ]
        uncached_asset_ids = (
            coingecko_integrated_asset_ids - set(cached_asset_ids) - self.failed_asset_ids.get_values()  # noqa: E501
        )
        log.info(
            f'Periodic task to query coingecko for {batch_size} uncached asset icons. '
            f'Uncached assets: {len(uncached_asset_ids)}. Cached assets: {len(cached_asset_ids)}',
        )
        assets_to_query = [(asset_id, coingecko_id) for asset_id, coingecko_id in coingecko_integrated_asset.items() if asset_id in uncached_asset_ids]  # noqa: E501
        for asset_id, coingecko_id in itertools.islice(assets_to_query, batch_size):
            self.query_coingecko_for_icon(asset=Asset(asset_id), coingecko_id=coingecko_id)

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
