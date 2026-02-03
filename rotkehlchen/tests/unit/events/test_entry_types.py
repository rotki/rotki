from rotkehlchen.history.events.constants import CHAIN_ENTRY_TYPES, STAKING_ENTRY_TYPES
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType


def test_entry_types_covered():
    """Test that all entry types are covered by the constants"""
    all_entry_types = set(HistoryBaseEntryType)
    generic_types = {  # types that don't need any extra DB fields
        HistoryBaseEntryType.HISTORY_EVENT,
        HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
        HistoryBaseEntryType.SWAP_EVENT,
    }
    assert all_entry_types == (generic_types | STAKING_ENTRY_TYPES | CHAIN_ENTRY_TYPES)
