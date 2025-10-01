import json
import logging

from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import CPT_EIGENLAYER
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_eigenpods_to_owners_mapping(db: DBHandler) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
    """Read stored events and get the deployed eigenpods to owners mappings"""
    with db.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT event_identifier, extra_data FROM history_events JOIN chain_events_info ON '
            'history_events.identifier=chain_events_info.identifier WHERE counterparty=? AND '
            'type=? AND subtype=? AND location=? AND extra_data IS NOT NULL',
            (
                CPT_EIGENLAYER,
                HistoryEventType.INFORMATIONAL.serialize(),
                HistoryEventSubType.CREATE.serialize(),
                Location.ETHEREUM.serialize_for_db(),
            ),
        )
        if len(events_extra_data := cursor.fetchall()) == 0:
            return {}

    eigenpod_owner_mapping = {}
    for row in events_extra_data:
        try:
            extra_data = json.loads(row[1])
        except json.JSONDecodeError:
            log.error(
                f'Error processing extra data for eigenpod information in {row[0]}. Skipping...',
            )
            continue

        if (owner := extra_data.get('eigenpod_owner')) is None or (eigenpod := extra_data.get('eigenpod_address')) is None:  # noqa: E501
            log.error(f'Expected to find extra data with owner and eigenpod in event with id {row[0]}. Skipping.')  # noqa: E501
            continue

        eigenpod_owner_mapping[eigenpod] = owner

    return eigenpod_owner_mapping
