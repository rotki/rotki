from typing import TYPE_CHECKING

from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler

LAST_EVENTS_PROCESSING_TASK_TS = 'last_events_processing_task_ts'


def process_events(
        chains_aggregator: 'ChainsAggregator',
        database: 'DBHandler',
) -> None:
    """Processes all events and modifies/combines them or aggregates processing results

    This is supposed to be a generic processing task that can be requested or run periodically
    """
    eth2 = chains_aggregator.get_module('eth2')
    if eth2 is not None:
        eth2.combine_block_with_tx_events()

    with database.user_write() as write_cursor:
        database.update_used_query_range(  # update last withdrawal query timestamp
            write_cursor=write_cursor,
            name=LAST_EVENTS_PROCESSING_TASK_TS,
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )
