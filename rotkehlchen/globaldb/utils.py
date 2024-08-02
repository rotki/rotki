from typing import TYPE_CHECKING

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.types import SPAM_PROTOCOL

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.drivers.client import DBCursor, DBWriterClient


# Whenever you upgrade the global DB make sure to:
# 1. Go to assets repo and tweak the min/max schema of the updates
# 2. Tweak ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS
GLOBAL_DB_VERSION = 8
ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS = (3, GLOBAL_DB_VERSION)
MIN_SUPPORTED_GLOBAL_DB_VERSION = 2

# Some functions that split the logic out of some GlobalDB query functions that are
# complicated enough to be abstracted and are used in multiple places. The main reason
# this exists is a bad design in the GlobalDBHandler() that can create circular imports.
# The cases I (Lefteris) know is maybe_upgrade_globaldb() and maybe_apply_globaldb_migrations()


def globaldb_get_setting_value(cursor: 'DBCursor', name: str, default_value: int) -> int:
    """
    Implementation of the logic of getting a setting from the global DB. Only for ints for now.
    """
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', (name,),
    )
    result = query.fetchall()
    # If setting is not set, it's the default
    if len(result) == 0:
        return default_value

    return int(result[0][0])


def set_token_spam_protocol(
        write_cursor: 'DBWriterClient',
        token: 'EvmToken',
        is_spam: bool,
) -> None:
    """
    Set the protocol field of the provided token as `SPAM` depending on the `is_spam`
    argument and clean the resolver cache. It overwrites the protocol field of the provided token
    """
    write_cursor.execute(
        'UPDATE evm_tokens SET protocol=? WHERE identifier=?',
        (SPAM_PROTOCOL if is_spam is True else None, token.identifier),
    )
    object.__setattr__(token, 'protocol', None)
    AssetResolver.clean_memory_cache(identifier=token.identifier)
