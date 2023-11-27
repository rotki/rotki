from typing import Any

from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_ms_to_sec


def history_event_to_staking_for_api(event: HistoryBaseEntry) -> dict[str, Any]:
    """This is a utility function to be used by kraken staking and binance savings
    rotki api endpoints. It just serves to reduce the returned data by the api
    for those endpoints.

    TODO: Think if we need these and if instead the frontend could just consume normal
    history events through the rotki API
    """
    data = {
        'asset': event.asset.identifier,
        'timestamp': ts_ms_to_sec(event.timestamp),
        'location': str(event.location),
        'balance': abs(event.balance).serialize(),
    }
    if not (
            event.location == Location.BINANCE and
            event.event_type == HistoryEventSubType.REWARD
    ):
        data['event_type'] = event.event_subtype.serialize()

    balance = abs(event.balance).serialize()
    return {**data, **balance}
