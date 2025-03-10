import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.assets.asset import Asset, AssetWithNameAndType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.schemas import ExportedAssetsSchema

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def import_assets_from_file(
        path: Path,
        msg_aggregator: 'MessagesAggregator',
        db_handler: 'DBHandler',
) -> None:
    """
    Import assets from the file at the defined path.
    This function can raise:
    - ValidationError: If the format of the file is not correct
    - InputError: If the version of the file is not valid for the current
    globaldb version
    """
    try:
        data = ExportedAssetsSchema().loads(Path(path).read_text(encoding='utf8'))
    except UnicodeDecodeError as e:
        raise InputError(f'Provided file at {path} could not be decoded as utf-8 properly') from e

    if int(data['version']) not in ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS:
        raise InputError(
            f'Provided file is for a different version of rotki. GlobalDB File version: '
            f'{data["version"]} Accepted GlobalDB version by rotki: {ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS}',  # noqa: E501
        )
    if data['assets'] is None:
        raise InputError('The imported file is missing a valid list of assets')

    identifiers = []
    for asset_data in data['assets']:
        asset: AssetWithNameAndType = asset_data['asset']
        if asset.exists():
            log.warning(
                f'Tried to import existing asset {asset.identifier} with '
                f'name {asset.name}',
            )
            continue

        try:
            GlobalDBHandler.add_asset(asset)
        except InputError as e:
            log.error(
                f'Failed to import asset {asset=}. {e!s}',
            )
            msg_aggregator.add_error(
                f'Failed to import asset with identifier '
                f'{asset.identifier}. Check logs for more details',
            )
            continue
        identifiers.append(asset.identifier)

    with db_handler.user_write() as cursor:
        db_handler.add_asset_identifiers(cursor, identifiers)


def export_assets_from_file(
        dirpath: Path | None,
        db_handler: 'DBHandler',
) -> Path:
    """
    Creates a zip file with a json file containing the assets added by the user.
    May raise:
    - PermissionError if the temp file can't be created
    """
    if dirpath is None:
        dirpath = Path(tempfile.TemporaryDirectory().name)
        dirpath.mkdir(parents=True, exist_ok=True)

    globaldb = GlobalDBHandler()

    with db_handler.user_read_write() as write_cursor, globaldb.conn.read_ctx() as gdb_cursor:
        assets = globaldb.get_user_added_assets(
            cursor=gdb_cursor,
            user_db_cursor=write_cursor,
            user_db=db_handler,
        )
    serialized = []
    for asset_identifier in assets:
        try:
            asset = Asset(asset_identifier).resolve()
            serialized.append(asset.to_dict())
        except UnknownAsset as e:
            log.error(e)

    with globaldb.conn.read_ctx() as gdb_cursor:
        query = gdb_cursor.execute("SELECT value from settings WHERE name='version';")
        version = query.fetchone()[0]
        data = {
            'version': version,
            'assets': serialized,
        }

    zip_path = dirpath / 'assets.zip'
    with ZipFile(file=zip_path, mode='w', compression=ZIP_DEFLATED) as assets_zip:
        assets_zip.writestr(
            zinfo_or_arcname='assets.json',
            data=json.dumps(data),
        )

    return zip_path
