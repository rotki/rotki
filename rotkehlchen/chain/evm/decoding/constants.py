from rotkehlchen.accounting.structures.types import HistoryEventType

CPT_GAS = 'gas'

OUTGOING_EVENT_TYPES = {
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
}
