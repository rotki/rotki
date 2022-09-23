import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION, GlobalDBHandler
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
    globaldb = GlobalDBHandler()
    with open(path) as f:
        data = ExportedAssetsSchema().loads(f.read())

    if int(data['version']) != GLOBAL_DB_VERSION:
        raise InputError(
            f'Provided file is for a different version of rotki. File version: '
            f'{data["version"]} rotki version: {GLOBAL_DB_VERSION}',
        )
    if data['assets'] is None:
        raise InputError('The imported file is missing a valid list of assets')

    identifiers = []
    for asset_data in data['assets']:
        # Check if we already have the asset with that name and symbol. It is possible that
        # we have added a missing asset. Using check_asset_exists for non ethereum tokens and
        # for ethereum tokens comparing by identifier. The edge case of a non-ethereum token
        # with same name and symbol will make this fail.
        asset_type = asset_data['asset_type']
        asset_ref: Union[Optional[List[str]], Optional[AssetData]]
        if asset_type == AssetType.EVM_TOKEN:
            asset_ref = globaldb.get_asset_data(
                identifier=asset_data['identifier'],
                form_with_incomplete_data=True,
            )
        else:
            asset_ref = globaldb.check_asset_exists(
                asset_type=asset_type,
                name=asset_data['name'],
                symbol=asset_data['symbol'],
            )
        if asset_ref is not None:
            msg_aggregator.add_warning(
                f'Tried to import existing asset {asset_data["identifier"]} with '
                f'name {asset_data["name"]}',
            )
            continue

        try:
            globaldb.add_asset(
                asset_id=asset_data['identifier'],
                asset_type=asset_type,
                data=asset_data['extra_information'],
            )
        except InputError as e:
            log.error(
                f'Failed to import asset with {asset_data["identifier"]=}',
                f'{asset_type=} and {asset_data=}. {str(e)}',
            )
            msg_aggregator.add_error(
                f'Failed to save import with identifier '
                f'{asset_data["identifier"]}. Check logs for more details',
            )
            continue
        identifiers.append(asset_data['identifier'])

    with db_handler.user_write() as cursor:
        db_handler.add_asset_identifiers(cursor, identifiers)


def export_assets_from_file(
    dirpath: Optional[Path],
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

    with db_handler.user_write() as cursor:
        with globaldb.conn.read_ctx() as gdb_cursor:
            assets = globaldb.get_user_added_assets(gdb_cursor, cursor, user_db=db_handler)
    serialized = []
    for asset_identifier in assets:
        try:
            asset = Asset(asset_identifier).resolve()
            serialized.append(asset.to_dict())
        except UnknownAsset as e:
            log.error(e)

    with globaldb.conn.read_ctx() as gdb_cursor:
        query = gdb_cursor.execute('SELECT value from settings WHERE name="version";')
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
