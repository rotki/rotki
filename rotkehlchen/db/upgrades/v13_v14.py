"""
Assets removed from all_assets.json in https://github.com/rotki/rotki/pull/1354
due to no price support neither in cryptocompare nor in coingecko
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


REMOVED_ASSETS = [
    'ACC-2',
    'APH-2',
    'ATOM-2',
    'BLZ-2',
    'FORK',
    'KNC-2',
    'LUNA',
    'MARS',
    'POLY-2',
    'PRC-2',
    'TALK',
    'USDS-2',
]
REMOVED_ETH_TOKENS = [
    'AI',
    'BLX',
    'BNN',
    'BTK',
    'CAT-2',
    'DAXT',
    'DEW',
    'E4ROW',
    'EDU-2',
    'EXC',
    'FID',
    'FLX',
    'FMF',
    'FT-2',
    'JOT',
    'LCT-2',
    'LML',
    'MORE-2',
    'NCC-2',
    'NTO',
    'NXX',
    'OCC-2',
    'PASS-2',
    'RGS',
    'SMART-2',
    'SNIP',
    'STRC',
    'XMCT',
    'XPA',
]


def _delete_unsupported_assets(db: 'DBHandler') -> None:
    """Deletes all assets that are no longer supported from various DB tables"""
    cursor = db.conn.cursor()
    # Kind of heavy handed, but let's just delete the ethereum tokens cache
    # Easier query than deleting tokens from the string that is a json list
    cursor.execute('DELETE FROM ethereum_accounts_details;')
    db.conn.commit()
    tuples = [(x,) for x in REMOVED_ASSETS + REMOVED_ETH_TOKENS]
    # Delete all timed balances that contain any of the removed assets
    cursor.executemany(
        'DELETE FROM timed_balances WHERE currency=?;',
        tuples,
    )
    db.conn.commit()
    # Delete all manually tracked balances that contain any of the removed assets
    cursor.executemany(
        'DELETE FROM manually_tracked_balances WHERE asset=?;',
        tuples,
    )
    db.conn.commit()
    # Delete all ignored asset entries that may contain removed assets
    cursor.executemany(
        'DELETE FROM multisettings WHERE name=? AND value=?;',
        [('ignored_asset', x) for x in REMOVED_ASSETS + REMOVED_ETH_TOKENS],
    )
    db.conn.commit()
    # Delete all trades that contain a removed asset in either part of the pair or in the fee
    cursor.executemany(
        'DELETE FROM trades WHERE pair LIKE ? ESCAPE ?;',
        [(f'{x}\\_%', '\\') for x in REMOVED_ASSETS + REMOVED_ETH_TOKENS],
    )
    cursor.executemany(
        'DELETE FROM trades WHERE pair LIKE ? ESCAPE ?;',
        [(f'%\\_{x}', '\\') for x in REMOVED_ASSETS + REMOVED_ETH_TOKENS],
    )
    cursor.executemany(
        'DELETE FROM trades WHERE fee_currency = ?;',
        tuples,
    )
    db.conn.commit()
    # Delete all asset movements that deal with removed assets
    cursor.executemany(
        'DELETE FROM asset_movements WHERE asset=? OR fee_asset=?;',
        [(x, x) for x in REMOVED_ASSETS + REMOVED_ETH_TOKENS],
    )
    db.conn.commit()


def upgrade_v13_to_v14(db: 'DBHandler') -> None:
    """Upgrades the DB from v13 to v14

    - Deletes all assets that are no longer supported from the DB
    """
    _delete_unsupported_assets(db)
