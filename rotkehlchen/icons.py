import hashlib
import logging
import shutil
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from fastapi import Response
from fastapi.responses import FileResponse

from rotkehlchen.assets.asset import Asset, AssetWithNameAndType
from rotkehlchen.constants.misc import (
    ALLASSETIMAGESDIR_NAME,
    ASSETIMAGESDIR_NAME,
    CUSTOMASSETIMAGESDIR_NAME,
    IMAGESDIR_NAME,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUSetCache
from rotkehlchen.utils.hashing import file_md5

if TYPE_CHECKING:
    from rotkehlchen.tasks.manager import TaskManager

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
        headers = _build_http_header_for_images(image_path)
        return Response(
            content=b'',
            status_code=HTTPStatus.NOT_MODIFIED,
            headers=headers,
        )

    return None


def create_image_response(image_path: Path) -> Response:
    """
    Returns a response with the image at image_path. It assumes that the file exists
    May raise:
    - OSError if the file doesn't exists
    """
    image_data = image_path.read_bytes()
    headers = _build_http_header_for_images(image_path)
    headers['etag'] = hashlib.md5(image_data).hexdigest()
    return Response(
        content=image_data,
        status_code=HTTPStatus.OK,
        headers=headers,
    )


def maybe_create_image_response(image_path: Path | None) -> Response:
    """Checks whether the file at `image_path` exists.

    Returns a response with the image if it exists, otherwise a NOT FOUND response.
    """
    if image_path is None or image_path.is_file() is False:
        return Response(
            content=b'',
            status_code=HTTPStatus.NOT_FOUND,
            headers={'mimetype': 'image/png', 'Content-Type': 'image/png'},
        )

    return create_image_response(image_path)


class IconManager:
    """Manages the icons for all the assets of the application. Partly moved to colibri"""

    def __init__(
            self,
            data_dir: Path,
            coingecko: Coingecko,
            task_manager: 'TaskManager',
    ) -> None:
        asset_images_dir = data_dir / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME
        self.icons_dir = asset_images_dir / ALLASSETIMAGESDIR_NAME
        self.custom_icons_dir = asset_images_dir / CUSTOMASSETIMAGESDIR_NAME
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        self.custom_icons_dir.mkdir(parents=True, exist_ok=True)
        self.failed_asset_ids: LRUSetCache[str] = LRUSetCache(maxsize=256)
        self.task_manager = task_manager

    def iconfile_path(self, asset: AssetWithNameAndType) -> Path:
        return self.icons_dir / f'{urllib.parse.quote_plus(asset.identifier)}_small.png'

    def custom_iconfile_path(self, asset: Asset) -> Path | None:
        asset_id_quoted = urllib.parse.quote_plus(asset.identifier)
        for suffix in ALLOWED_ICON_EXTENSIONS:
            icon_path = self.custom_icons_dir / f'{asset_id_quoted}{suffix}'
            if icon_path.is_file():
                return icon_path

        return None

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
