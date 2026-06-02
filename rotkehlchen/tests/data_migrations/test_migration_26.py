"""Test for data migration 26 - cleanup of orphaned manual balance tag mappings."""
import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.data_migrations import run_single_migration


@pytest.mark.parametrize('data_migration_version', [25])
def test_migration_26_orphaned_manual_balance_tags(database: DBHandler) -> None:
    """Orphaned manual-balance tag mappings (left by the v51->v52 id renumbering) are removed,
    while valid manual-balance tags and non-numeric references (blockchain accounts, xpubs) stay.
    """
    address = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'
    xpub_ref = 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz/m'  # noqa: E501
    with database.user_write() as write_cursor:
        # two manual balances with an id gap (id 4 missing), as left behind by a deletion
        write_cursor.executemany(
            'INSERT INTO manually_tracked_balances(id, asset, label, amount, location, category) '
            'VALUES(?, ?, ?, ?, ?, ?)',
            [
                (3, 'BTC', 'kept wallet', '1', 'A', 'A'),
                (5, 'ETH', 'tagged wallet', '2', 'A', 'A'),
            ],
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO tags(name, description, background_color, foreground_color) '
            'VALUES(?, ?, ?, ?)', ('public', '', 'ffffff', '000000'),
        )
        write_cursor.executemany(
            'INSERT INTO tag_mappings(object_reference, tag_name) VALUES(?, ?)',
            [
                ('5', 'public'),  # valid: points at an existing manual balance
                ('7', 'public'),  # orphan: no manual balance with id 7
                (address, 'public'),  # blockchain account tag, must be untouched
                (xpub_ref, 'public'),  # xpub tag, must be untouched
            ],
        )

    run_single_migration(database=database, migration=26)

    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT object_reference FROM tag_mappings WHERE tag_name=?', ('public',),
        ).fetchall()) == {('5',), (address,), (xpub_ref,)}  # orphan '7' removed, rest kept
