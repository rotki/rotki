import logging
from typing import TYPE_CHECKING, Callable, Dict, Any, NamedTuple, Optional

from rotkehlchen.app_upgrades.upgrades.upgrade_1 import app_upgrade_1
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UpgradeRecord(NamedTuple):
    version: int
    function: Callable
    kwargs: Optional[Dict[str, Any]] = None


UPGRADE_LIST = [
    UpgradeRecord(version=1, function=app_upgrade_1),
]


class RotkiUpgradeManager:

    def __init__(self, rotki: 'Rotkehlchen'):
        self.rotki = rotki

    def run_upgrades(self) -> None:
        # get last upgrade setting
        settings = self.rotki.data.db.get_settings()
        current_upgrade = settings.last_app_upgrade
        for upgrade in UPGRADE_LIST:
            if current_upgrade < upgrade.version:
                self._perform_upgrade(upgrade)
                current_upgrade += 1
        self.rotki.data.db.conn.cursor().execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_app_upgrade', current_upgrade),
        )

    def _perform_upgrade(self, upgrade: UpgradeRecord) -> None:
        try:
            kwargs = upgrade.kwargs if upgrade.kwargs is not None else {}
            upgrade.function(rotki=self.rotki, **kwargs)
        except BaseException as e:
            error = f'Failed to run soft migration from version {upgrade.version} : {str(e)}'
            log.error(error)
