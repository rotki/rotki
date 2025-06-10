"""Repository for managing asset operations in the database."""
import logging
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.constants import TABLES_WITH_ASSETS
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import SPAM_PROTOCOL, BalanceType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


class AssetsRepository:
    """Repository for handling all asset-related operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the assets repository."""
        self.msg_aggregator = msg_aggregator

    def add_to_ignored(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        """Add a new asset to the set of ignored assets. If the asset was already marked as
        ignored then we don't do anything. Also ignore history events with this asset.
        """
        write_cursor.execute(
            'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
            ('ignored_asset', asset.identifier),
        )
        write_cursor.execute(
            'UPDATE history_events SET ignored=? WHERE asset=?',
            (1, asset.identifier),
        )

    def ignore_multiple(self, write_cursor: 'DBCursor', assets: list[str]) -> None:
        """Add the provided identifiers to the list of ignored assets. If any asset was already
        marked as ignored then we don't do anything. Also ignore history events with these assets.
        """
        for chunk, placeholders in get_query_chunks(data=assets):
            ms_placeholders = ','.join(["('ignored_asset', ?)"] * len(chunk))
            write_cursor.execute(
                f'INSERT OR IGNORE INTO multisettings(name, value) VALUES {ms_placeholders}',
                chunk,
            )
            write_cursor.execute(
                f'UPDATE history_events SET ignored=1 WHERE asset IN ({placeholders})',
                chunk,
            )

    def remove_from_ignored(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        """Remove an asset from the ignored assets and un-ignore history events with this asset."""
        write_cursor.execute(
            "DELETE FROM multisettings WHERE name='ignored_asset' AND value=?;",
            (asset.identifier,),
        )
        write_cursor.execute(
            'UPDATE history_events SET ignored=? WHERE asset=?',
            (0, asset.identifier),
        )

    def get_ignored_ids(self, cursor: 'DBCursor', only_nfts: bool = False) -> set[str]:
        """Gets the ignored asset ids without converting each one of them to an asset object

        We used to have a heavier version which converted them to an asset but removed
        it due to unnecessary roundtrips to the global DB for each asset initialization
        """
        bindings = []
        query = "SELECT value FROM multisettings WHERE name='ignored_asset' "
        if only_nfts is True:
            query += 'AND value LIKE ?'
            bindings.append(f'{NFT_DIRECTIVE}%')
        cursor.execute(query, bindings)
        return {x[0] for x in cursor}

    def query_owned(self, cursor: 'DBCursor') -> list[Asset]:
        """Query the DB for a list of all assets ever owned

        The assets are taken from:
        - Balance snapshots
        - Manual balances
        """
        # but think on the performance. This is a synchronous api call so if
        # it starts taking too much time the calling logic needs to change
        results = set()
        for table_entry in TABLES_WITH_ASSETS:
            table_name = table_entry[0]
            columns = table_entry[1:]
            columns_str = ', '.join(columns)
            bindings: tuple | tuple[str] = ()
            condition = ''
            if table_name in {'manually_tracked_balances', 'timed_balances'}:
                bindings = (BalanceType.LIABILITY.serialize_for_db(),)
                condition = ' WHERE category!=?'

            try:
                cursor.execute(
                    f'SELECT DISTINCT {columns_str} FROM {table_name} {condition};',
                    bindings,
                )
            except sqlcipher.OperationalError as e:    # pylint: disable=no-member
                log.error(f'Could not fetch assets from table {table_name}. {e!s}')
                continue

            for result in cursor:
                for asset_id in result:
                    try:
                        if asset_id is not None:
                            results.add(Asset(asset_id).check_existence())
                    except UnknownAsset:
                        if table_name == 'manually_tracked_balances':
                            self.msg_aggregator.add_warning(
                                f'Unknown/unsupported asset {asset_id} found in the '
                                f'manually tracked balances. Have you modified the assets DB? '
                                f'Make sure that the aforementioned asset is in there.',
                            )
                        else:
                            log.debug(
                                f'Unknown/unsupported asset {asset_id} found in the database '
                                f'If you believe this should be supported open an issue in github',
                            )

                        continue
                    except DeserializationError:
                        self.msg_aggregator.add_error(
                            f'Asset with non-string type {type(asset_id)} found in the '
                            f'database. Skipping it.',
                        )
                        continue

        return list(results)

    def update_owned_in_globaldb(self, cursor: 'DBCursor') -> None:
        """Makes sure all owned assets of the user are in the Global DB"""
        assets = self.query_owned(cursor)
        GlobalDBHandler.add_user_owned_assets(assets)

    def add_identifiers(self, write_cursor: 'DBCursor', asset_identifiers: list[str]) -> None:
        """Adds an asset to the user db asset identifier table"""
        write_cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
            [(x,) for x in asset_identifiers],
        )

    def sync_globaldb(self, write_cursor: 'DBCursor') -> None:
        """Makes sure that:
        - all the GlobalDB asset identifiers are mirrored in the user DB
        - all the assets set to have the SPAM_PROTOCOL in the global DB
        are set to be part of the user's ignored list
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            # after successful update add all asset ids
            cursor.execute('SELECT identifier from assets;')
            self.add_identifiers(
                write_cursor=write_cursor,
                asset_identifiers=[x[0] for x in cursor],
            )  # could do an attach DB here instead of two different cursor queries but probably would be overkill # noqa: E501
            globaldb_spam = cursor.execute(
                'SELECT identifier FROM evm_tokens WHERE protocol=?',
                (SPAM_PROTOCOL,),
            ).fetchall()
            self.ignore_multiple(
                write_cursor=write_cursor,
                assets=[identifier[0] for identifier in globaldb_spam],
            )

    def delete_identifier(self, write_cursor: 'DBCursor', asset_id: str) -> None:
        """Deletes an asset identifier from the user db asset identifier table

        May raise:
        - InputError if a foreign key error is encountered during deletion
        """
        try:
            write_cursor.execute(
                'DELETE FROM assets WHERE identifier=?;',
                (asset_id,),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Failed to delete asset with id {asset_id} due to {e!s}. Make sure '
                f'that this asset is not already used',
            ) from e

    def replace_identifier(self, write_cursor: 'DBCursor', source_identifier: str, target_asset: Asset) -> None:
        """
        Replaces a given source identifier either in any of the relevant tables

        May raise:
        - InputError if the source identifier is not in the DB
        """
        # the tricky part here is that we need to disable foreign keys for this
        # approach and disabling foreign keys needs a commit. So rollback is impossible.
        # But there is no way this can fail. (famous last words)
        write_cursor.executescript('PRAGMA foreign_keys = OFF;')
        write_cursor.execute(
            'DELETE from assets WHERE identifier=?;',
            (target_asset.identifier,),
        )
        write_cursor.executescript('PRAGMA foreign_keys = ON;')
        write_cursor.execute(
            'UPDATE assets SET identifier=? WHERE identifier=?;',
            (target_asset.identifier, source_identifier),
        )