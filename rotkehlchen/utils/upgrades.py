from collections.abc import Callable
from typing import Any, NamedTuple

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.utils.interfaces import ProgressUpdater


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: dict[str, Any] | None = None


class DBUpgradeProgressHandler(ProgressUpdater):
    """Class to notify users through websockets about progress of upgrading the database."""

    def _notify_frontend(self, step_name: str | None = None) -> None:
        """Sends to the user through websockets all information about db upgrading progress."""
        self.messages_aggregator.add_message(
            message_type=WSMessageType.DB_UPGRADE_STATUS,
            data={
                'start_version': self.start_version,
                'target_version': self.target_version,
                'current_upgrade': {
                    'to_version': self.current_version,
                    'total_steps': self.current_round_total_steps,
                    'current_step': self.current_round_current_step,
                    'description': step_name,
                },
            },
        )
