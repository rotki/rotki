from typing import Final

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import (
    EventCategory,
    HistoryEventSubType,
    HistoryEventType,
)

# possible combinations of types and subtypes mapped to their event
# category based on the entry type
ENTRY_TYPE_MAPPINGS: Final = {
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.serialize(): {
        HistoryEventType.STAKING: {
            HistoryEventSubType.REMOVE_ASSET: {
                'is_exit': EventCategory.STAKE_EXIT,
                'not_exit': EventCategory.WITHDRAW,
            },
        },
    },
}
