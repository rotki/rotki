import logging

from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import CPT_EIGENLAYER
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_eigenpods_to_owners_mapping(db: DBHandler) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
    """Read stored events and get the deployed eigenpods to owners mappings"""
    db_filter = EvmEventFilterQuery.make(
        counterparties=[CPT_EIGENLAYER],
        location=Location.ETHEREUM,
        event_types=[HistoryEventType.INFORMATIONAL],
        event_subtypes=[HistoryEventSubType.CREATE],
    )
    with db.conn.read_ctx() as cursor:
        if len(events := DBHistoryEvents(db).get_history_events(
            cursor=cursor,
            filter_query=db_filter,
            has_premium=True,
        )) == 0:
            return {}

    eigenpod_owner_mapping = {}
    for event in events:
        if event.extra_data is None or (owner := event.extra_data.get('eigenpod_owner')) is None or (eigenpod := event.extra_data.get('eigenpod_address')) is None:  # noqa: E501
            log.error(f'Expected to find extra data with owner and eigenpod in {event}. Skipping.')
            continue

        eigenpod_owner_mapping[eigenpod] = owner

    return eigenpod_owner_mapping
