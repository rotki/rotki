from typing import TYPE_CHECKING, List, Tuple

from rotkehlchen.assets.asset import CustomAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.db.filtering import CustomAssetsFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb import GlobalDBHandler

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBCustomAssets:
    def __init__(self, db_handler: 'DBHandler') -> None:
        self.db = db_handler

    @staticmethod
    def _get_custom_assets(filter_query: CustomAssetsFilterQuery) -> List[CustomAsset]:
        """
        Queries the custom_assets table using the filter query and returns a list of `CustomAsset`.
        May raise:
        - DeserializationError
        """
        query, bindings = filter_query.prepare()
        query = 'SELECT B.identifier, B.name, A.type as custom_asset_type, A.notes from custom_assets `A` JOIN assets `B` ON A.identifier = B.identifier ' + query  # noqa: E501
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            # never raises an error as identifier is always a string in DB.
            return [CustomAsset.deserialize_from_db(entry) for entry in cursor]

    def get_custom_assets_and_limit_info(
            self,
            filter_query: CustomAssetsFilterQuery,
    ) -> Tuple[List[CustomAsset], int, int]:
        """
        Returns a list of `CustomAsset`, a count of the assets that match
        the query and the count of custom assets in the DB.
        """
        entries = self._get_custom_assets(filter_query=filter_query)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            query, bindings = filter_query.prepare(with_pagination=False)
            query = 'SELECT COUNT(A.type) AS custom_asset_type from custom_assets AS A JOIN assets AS B ON A.identifier = B.identifier ' + query  # noqa: E501
            entries_found = cursor.execute(query, bindings).fetchone()[0]
            entries_total = cursor.execute('SELECT COUNT(*) FROM custom_assets;').fetchone()[0]
            return entries, entries_found, entries_total

    def add_custom_asset(self, custom_asset: CustomAsset) -> str:
        """
        Adds a custom new custom asset into `assets` and `custom_assets` table.
        May raise:
        - InputError if the combination of the name & type / asset with identifier already exist.
        """
        self._raise_if_custom_asset_exists(custom_asset)
        with GlobalDBHandler().conn.write_ctx() as global_db_write_cursor:
            global_db_write_cursor.execute(
                'INSERT INTO assets(identifier, name, type) VALUES (?, ?, ?)',
                (
                    custom_asset.identifier,
                    custom_asset.name,
                    AssetType.CUSTOM_ASSET.serialize_for_db(),
                ),
            )
            global_db_write_cursor.execute(
                'INSERT INTO custom_assets(identifier, type, notes) VALUES(?, ?, ?)',
                custom_asset.serialize_for_db(),
            )
            with self.db.user_write() as db_write_cursor:
                self.db.add_asset_identifiers(db_write_cursor, [custom_asset.identifier])
        return custom_asset.identifier

    def edit_custom_asset(self, custom_asset: CustomAsset) -> None:
        """
        Edits a custom asset.
        May raise:
        - InputError if editing a custom asset that does not exist or combination
        of name and type is already present.
        """
        self._raise_if_custom_asset_exists(custom_asset)
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'UPDATE assets SET name=? WHERE identifier=?',
                (custom_asset.name, custom_asset.identifier),
            )
            write_cursor.execute(
                'UPDATE custom_assets SET notes=?, type=? WHERE identifier=?',
                (custom_asset.notes, custom_asset.custom_asset_type, custom_asset.identifier),
            )
            # this checks if the identifier exists in the db unlike `_raise_if_custom_asset_exists`
            # that checks for the existence of the combination of name & type.
            if write_cursor.rowcount == 0:
                raise InputError(
                    f'Tried to edit custom asset with identifier {custom_asset.identifier} and name '  # noqa: E501
                    f'{custom_asset.name} but it was not found',
                )

    @staticmethod
    def _raise_if_custom_asset_exists(custom_asset: CustomAsset) -> None:
        """
        This function checks if the custom asset's name & type are not already used in the DB.
        Raises InputError if match exists.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT A.identifier, B.name, A.type FROM custom_assets AS A JOIN assets B ON A.identifier = B.identifier WHERE A.type=? AND B.name=? AND A.identifier!=?;',  # noqa: E501
                (custom_asset.custom_asset_type, custom_asset.name, custom_asset.identifier),
            ).fetchone()
            if result is not None:
                raise InputError(
                    f'Custom asset with name "{custom_asset.name}" and type '
                    f'"{custom_asset.custom_asset_type}" already present in the database',
                )

    @staticmethod
    def get_custom_asset_types() -> List[str]:
        """Returns a list custom asset types used in the DB."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute('SELECT DISTINCT type FROM custom_assets ORDER BY type;')
            return [entry[0] for entry in cursor]
