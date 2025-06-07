import random
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.bitcoin.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import BTCAddress


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
def test_query_transactions(
        rotkehlchen_api_server: 'APIServer',
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that bitcoin transactions are properly queried via the api.
    Since there are quite a number of transactions, only check decoding of first and last txs.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])
    for json, expected_len in (
        ({'async_query': async_query, 'to_timestamp': 1740000000}, 59),  # query partial range first  # noqa: E501
        ({'async_query': async_query}, 67),  # then query the rest
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json=json,
        )
        assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
        with rotki.data.db.conn.read_ctx() as cursor:
            events = DBHistoryEvents(rotki.data.db).get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    order_by_rules=[('timestamp', True), ('event_identifier', True), ('sequence_index', True)],  # noqa: E501
                ),
                has_premium=True,
            )
        assert len(events) == expected_len

    assert events[66:] == [HistoryEvent(
        identifier=60,
        event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}67c97abe049b671a02e537eb901cd600430ddaa5b09b50434969e360ada748bf',
        sequence_index=0,
        timestamp=TimestampMS(1747980089000),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal(fee_amount := '0.00000109921082299887260428410372040586245772266065388951521984216459977452085682074'),  # noqa: E501
        location_label=(user_address := btc_accounts[0]),
        notes=f'Spend {fee_amount} BTC for fees',
    )]  # TODO: this is a multi-input tx. Adjust this test after adding multi-input decoding.
    assert events[0] == HistoryEvent(
        identifier=59,
        event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}0d39207fd965314941546a698e5f76277818e8b95f41b2e02dfe1901db86acf1',
        sequence_index=0,
        timestamp=TimestampMS(1519764871000),
        location=Location.BITCOIN,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal(receive_amount := '0.00009310'),
        location_label=user_address,
        notes=f'Receive {receive_amount} BTC from 3QrkDXwdkmQgDk9kKSNCv4KrQFgegna5ym',
    )
