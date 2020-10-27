from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.utils import is_valid_derivation_path
from rotkehlchen.typing import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v19_to_v20(db: 'DBHandler') -> None:
    """Upgrades the DB from v19 to v20

    - Delete all xpub entries that have an invalid derivation path as part of
    mitigation of https://github.com/rotki/rotki/issues/1641
    """
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT xpub, derivation_path FROM xpubs;')
    for entry in query:
        derivation_path = entry[1]
        if derivation_path == '':
            continue
        valid, _ = is_valid_derivation_path(derivation_path)
        if valid:
            continue

        # At this point we have a DB entry with an invalid derivation path. Delete it
        xpub = entry[0]
        # Delete the tag mappings for all derived addresses
        cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'object_reference IN ('
            'SELECT address from xpub_mappings WHERE xpub=? and derivation_path IS ?);',
            (xpub, derivation_path),
        )
        # Delete any derived addresses
        cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account IN ('
            'SELECT address from xpub_mappings WHERE xpub=? and derivation_path IS ?);',
            (
                SupportedBlockchain.BITCOIN.value,
                xpub,
                derivation_path,
            ),
        )
        # And then finally delete the xpub itself
        cursor.execute(
            'DELETE FROM xpubs WHERE xpub=? AND derivation_path IS ?;',
            (xpub, derivation_path),
        )

    db.conn.commit()
