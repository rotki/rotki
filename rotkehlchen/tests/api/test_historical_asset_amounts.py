"""API regression coverage for historical graph asset amounts."""

from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_without_accounting_update(
        rotkehlchen_api_server: APIServer,
) -> None:
    """The graph endpoint must remain available while accounting update is disabled."""
    timestamp = Timestamp(1672531200)
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier='btc_receive',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.BLOCKCHAIN,
                asset=A_BTC,
                amount=FVal('2'),
                notes='Receive BTC',
            )],
        )

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historicalassetamountsresource'),
        json={
            'asset': A_BTC.identifier,
            'from_timestamp': timestamp,
            'to_timestamp': timestamp,
        },
        timeout=10,
    )

    assert assert_proper_sync_response_with_result(response) == {
        'times': [timestamp],
        'values': ['2'],
    }
