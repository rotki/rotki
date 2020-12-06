from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.errors import DBUpgradeError

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _migrate_fiat_balances(db: 'DBHandler') -> None:
    """Migrates fiat balances from the old current_balances table to manually tracked balances"""
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT asset, amount FROM current_balances;')
    for entry in query.fetchall():  # fetchall() here since the same cursors can't be used later
        asset = entry[0]
        amount = entry[1]
        try:
            cursor.execute(
                'INSERT INTO manually_tracked_balances(asset, label, amount, location) '
                'VALUES(?, ?, ?, ?);',
                (asset, f'My {asset} bank', amount, 'I'),
            )
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # Assume it failed since the label already exists. Then use a much more temporary label
            try:
                cursor.execute(
                    'INSERT INTO manually_tracked_balances(asset, label, amount, location) '
                    'VALUES(?, ?, ?, ?);',
                    (
                        asset,
                        f'Migrated from fiat balances. My {asset} bank',
                        amount,
                        'I'),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise DBUpgradeError(
                    f'Failed to migrate {asset} fiat balance to '
                    f'manually tracked balances. Error: {str(e)}',
                ) from e

        db.conn.commit()

    # Once any fiat balances got migrated, we can delete the table
    cursor.execute('DROP TABLE IF EXISTS current_balances;')
    db.conn.commit()


def _delete_unneeded_data(db: 'DBHandler') -> None:
    """Delete owned eth tokens and alethio credentials"""
    cursor = db.conn.cursor()
    # Remove all owned eth tokens as this setting is no longer going to be used
    cursor.execute('DELETE FROM multisettings WHERE name="eth_token";')
    # If the user had any alethio credentials remove them.
    cursor.execute('DELETE FROM external_service_credentials WHERE name="alethio";')
    db.conn.commit()


def upgrade_v12_to_v13(db: 'DBHandler') -> None:
    """Upgrades the DB from v12 to v13

    - Deletes the old fiat balances and migrates them to the manually_tracked_balances
    - Deletes owned eth tokens and alethio credentials as they are no longer needed
    """
    _migrate_fiat_balances(db)
    _delete_unneeded_data(db)
