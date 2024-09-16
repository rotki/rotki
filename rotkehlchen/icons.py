import hashlib
import logging
import shutil
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from flask import Response, make_response

from rotkehlchen.assets.asset import Asset, AssetWithNameAndType
from rotkehlchen.constants.assets import A_WETH
from rotkehlchen.constants.misc import (
    ALLASSETIMAGESDIR_NAME,
    ASSETIMAGESDIR_NAME,
    CUSTOMASSETIMAGESDIR_NAME,
    IMAGESDIR_NAME,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUSetCache
from rotkehlchen.utils.hashing import file_md5

if TYPE_CHECKING:
    from rotkehlchen.greenlets.manager import GreenletManager

if TYPE_CHECKING is True:
    pass

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ALLOWED_ICON_EXTENSIONS = ('.png', '.svg', '.jpeg', '.jpg', '.webp')


def _build_http_header_for_images(image_path: Path) -> dict[str, str]:
    """Given a path to an image return the headers to be used when sending it in a http request"""
    http_type = image_path.suffix[1:]
    if http_type == 'svg':
        http_type = 'svg+xml'

    return {'mimetype': f'image/{http_type}', 'Content-Type': f'image/{http_type}'}


def check_if_image_is_cached(image_path: Path, match_header: str | None) -> Response | None:
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
                _build_http_header_for_images(image_path),
            ),
        )

    return None


def create_image_response(image_path: Path) -> Response:
    """
    Returns a response with the image at image_path. It assumes that the file exists
    May raise:
    - OSError if the file doesn't exists
    """
    image_data = image_path.read_bytes()
    response = make_response(
        (
            image_data,
            HTTPStatus.OK,
            _build_http_header_for_images(image_path),
        ),
    )
    response.set_etag(hashlib.md5(image_data).hexdigest())
    return response


def maybe_create_image_response(image_path: Path | None) -> Response:
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
        asset_images_dir = data_dir / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME
        self.icons_dir = asset_images_dir / ALLASSETIMAGESDIR_NAME
        self.custom_icons_dir = asset_images_dir / CUSTOMASSETIMAGESDIR_NAME
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        self.custom_icons_dir.mkdir(parents=True, exist_ok=True)
        self.failed_asset_ids: LRUSetCache[str] = LRUSetCache(maxsize=256)
        self.greenlet_manager = greenlet_manager

    def iconfile_path(self, asset: AssetWithNameAndType) -> Path:
        return self.icons_dir / f'{urllib.parse.quote_plus(asset.identifier)}_small.png'

    def custom_iconfile_path(self, asset: Asset) -> Path | None:
        asset_id_quoted = urllib.parse.quote_plus(asset.identifier)
        for suffix in ALLOWED_ICON_EXTENSIONS:
            icon_path = self.custom_icons_dir / f'{asset_id_quoted}{suffix}'
            if icon_path.is_file():
                return icon_path

        return None

    def asset_icon_path(
            self,
            asset: AssetWithNameAndType,
    ) -> Path | None:
        # First try with the custom icon path
        custom_icon_path = self.custom_iconfile_path(asset)
        if custom_icon_path is not None:
            return custom_icon_path

        path = self.iconfile_path(asset)
        if not path.is_file():
            return None

        return path

    def query_coingecko_for_icon(self, asset: AssetWithNameAndType, coingecko_id: str) -> bool:
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
                f'Problem querying coingecko for asset data of {asset.identifier}: {e!s}',
            )
            # If a query fails (99% of fails will be 404s) don't repeat them
            self.failed_asset_ids.add(asset.identifier)
            return False

        try:
            response = self.coingecko.session.get(data.image_url, timeout=CachedSettings().get_timeout_tuple())  # noqa: E501
        except requests.exceptions.RequestException:
            # Any problem getting the image skip it: https://github.com/rotki/rotki/issues/1370
            return False

        if response.status_code != HTTPStatus.OK:
            return False

        self.iconfile_path(asset).write_bytes(response.content)
        return True

    def get_icon(
            self,
            asset: AssetWithNameAndType,
    ) -> tuple[Path | None, bool]:
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
        collection_main_asset_id: str | None
        if asset.identifier in (
            'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'eip155:10/erc20:0x4200000000000000000000000000000000000006',
            'eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1',
            'eip155:8453/erc20:0x4200000000000000000000000000000000000006',
            'eip155:534352/erc20:0x5300000000000000000000000000000000000004',
            'eip155:137/erc20:0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
            'eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
        ):
            # handle weth as special case since it is in the ethereum group
            collection_main_asset_id = A_WETH.identifier
        else:
            collection_main_asset_id = GlobalDBHandler.get_collection_main_asset(asset.identifier)
        asset_to_query_icon = asset

        if collection_main_asset_id is not None:
            # get the asset with the lowest lex order
            asset_to_query_icon = AssetWithNameAndType(collection_main_asset_id)

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

    def add_icon(self, asset: Asset, icon_path: Path) -> None:
        """Adds the icon in the custom icons directory for the asset

        Completely replaces what was there before
        """
        quoted_identifier = urllib.parse.quote_plus(asset.identifier)

        # delete possible old uploads
        for extension in ALLOWED_ICON_EXTENSIONS:
            (self.custom_icons_dir / f'{quoted_identifier}{extension}').unlink(missing_ok=True)

        shutil.copyfile(
            icon_path,
            self.custom_icons_dir / f'{quoted_identifier}{icon_path.suffix}',
        )

    def delete_icon(self, asset: AssetWithNameAndType) -> None:
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
