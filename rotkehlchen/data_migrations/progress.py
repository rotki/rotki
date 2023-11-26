
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.utils.interfaces import ProgressUpdater


class MigrationProgressHandler(ProgressUpdater):

    def _notify_frontend(self, step_name: str | None = None) -> None:
        self.messages_aggregator.add_message(
            message_type=WSMessageType.DATA_MIGRATION_STATUS,
            data={
                'start_version': self.start_version,
                'target_version': self.target_version,
                'current_migration': {
                    'version': self.current_version,
                    'total_steps': self.current_round_total_steps,
                    'current_step': self.current_round_current_step,
                    'description': step_name,
                },
            },
        )
