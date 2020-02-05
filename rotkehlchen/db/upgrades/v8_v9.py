from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _upgrade_user_credentials_table(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the user credentiaals trades table at v8
    query = cursor.execute('SELECT name, api_key, api_secret from user_credentials')
    credential_tuples = []
    for result in query:
        credential_tuples.append((result[0], result[1], result[2], None))

    # We got all credentials data. Now delete the old table and create the new one
    cursor.execute('DROP TABLE user_credentials;')
    db.conn.commit()
    # Now create user credentials table at v9
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_credentials (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT
    );""")
    db.conn.commit()
    # and finally move the data to the new table
    cursor.executemany(
        'INSERT INTO user_credentials(name, api_key, api_secret, passphrase) '
        'VALUES (?, ?, ?, ?)',
        credential_tuples,
    )
    db.conn.commit()


def upgrade_v8_to_v9(db: 'DBHandler') -> None:
    """Upgrades the DB from v8 to v9

    - Adds the passphrase column to the user credentials
    - All previous user credentials get a null passphrase
    """
    _upgrade_user_credentials_table(db)
