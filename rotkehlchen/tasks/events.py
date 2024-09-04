from typing import TYPE_CHECKING

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler


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
        eth2.refresh_activated_validators_deposits()

    with database.user_write() as write_cursor:
        database.set_static_cache(  # update last withdrawal query timestamp
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS,
            value=ts_now(),
        )
