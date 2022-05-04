from typing import TYPE_CHECKING

from rotkehlchen.assets.spam_assets import update_spam_assets

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


def data_migration_3(rotki: 'Rotkehlchen') -> None:
    """
    Update the list of ignored assets with tokens from cryptoscamdb
    """
    update_spam_assets(rotki.data.db)
