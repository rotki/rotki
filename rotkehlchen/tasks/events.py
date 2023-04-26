from typing import TYPE_CHECKING

from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

LAST_EVENTS_PROCESSING_TASK_TS = 'last_events_processing_task_ts'


def process_events(rotki: 'Rotkehlchen') -> None:
    """Processes all events and modifies/combines them or aggregates processing results

    This is supposed to be a generic processing task that can be requested or run periodically
    """
    eth2 = rotki.chains_aggregator.get_module('eth2')
    if eth2 is None:
        return

    eth2.combine_block_with_tx_events()
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.update_used_query_range(  # update last withdrawal query timestamp
            write_cursor=write_cursor,
            name=LAST_EVENTS_PROCESSING_TASK_TS,
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )
