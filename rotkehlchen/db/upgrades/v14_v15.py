from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v14_to_v15(db: 'DBHandler') -> None:
    """Upgrades the DB from v14 to v15

    - Deletes all ethereum transactions from the DB so they can be saved again
      with integers for most numerical fields.
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM ethereum_transactions;')
    db.conn.commit()
