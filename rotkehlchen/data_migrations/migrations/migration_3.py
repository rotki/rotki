import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_3(rotki: 'Rotkehlchen') -> None:
    """
    Update the list of ignored assets with tokens from cryptoscamdb
    """
    try:
        update_spam_assets(db=rotki.data.db)
    except RemoteError as e:
        log.error(f'Failed to update the list of ignored assets during db migration. {str(e)}')
