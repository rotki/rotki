import os
from typing import Final

ROTKI_ACCOUNTING_UPDATE: Final = 'ROTKI_ACCOUNTING_UPDATE'


def is_accounting_update_enabled() -> bool:
    """Return whether experimental accounting update functionality is enabled."""
    return os.environ.get(ROTKI_ACCOUNTING_UPDATE) == 'True'
