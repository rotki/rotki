from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import CPT_EIGENLAYER
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS


def add_create_eigenpod_event(
        database: DBHandler,
        eigenpod_address: ChecksumEvmAddress,
        eigenpod_owner: ChecksumEvmAddress,
):
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.CREATE,
                asset=A_ETH,
                amount=ZERO,
                counterparty=CPT_EIGENLAYER,
                location_label=eigenpod_owner,
                address=make_evm_address(),
                extra_data={'eigenpod_owner': eigenpod_owner, 'eigenpod_address': eigenpod_address},  # noqa: E501
            ),
        )
