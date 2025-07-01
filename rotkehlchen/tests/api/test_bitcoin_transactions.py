import random
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.bitcoin.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.types import BitcoinTx
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures import WebsocketReader
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import BTCAddress


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
@pytest.mark.parametrize('use_blockcypher', [True, False])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_transactions(
        rotkehlchen_api_server: 'APIServer',
        btc_accounts: list['BTCAddress'],
        use_blockcypher: bool,
        websocket_connection: WebsocketReader,
) -> None:
    """Test that bitcoin transactions are properly queried via the api.
    Since there are quite a number of transactions, only check decoding of first and last txs.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    bitcoin_manager = rotki.chains_aggregator.bitcoin_manager
    async_query = random.choice([False, True])
    original_blockchain_info_query = bitcoin_manager._query_blockchain_info_transactions

    def mock_blockchain_info_query(**kwargs: Any) -> tuple[int, list[BitcoinTx]]:
        """Raise a remote error so it tries the next api if we want to use blockcypher."""
        if use_blockcypher:
            raise RemoteError('Use blockcypher api instead.')

        return original_blockchain_info_query(**kwargs)

    query_patch = patch.object(bitcoin_manager, '_query_blockchain_info_transactions', new=mock_blockchain_info_query)  # noqa: E501
    for json, expected_len in (
        ({'async_query': async_query, 'to_timestamp': 1740000000}, 67),  # query partial range first  # noqa: E501
        ({'async_query': async_query}, 76),  # then query the rest
    ):
        with query_patch:
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

        # Confirm WS tx status messages were sent
        websocket_connection.wait_until_messages_num(4, timeout=5)
        assert list(websocket_connection.messages) == [
            {'type': 'transaction_status', 'data': {'addresses': btc_accounts, 'chain': 'BTC', 'subtype': 'bitcoin', 'status': 'decoding_transactions_finished'}},  # noqa: E501
            {'type': 'transaction_status', 'data': {'addresses': btc_accounts, 'chain': 'BTC', 'subtype': 'bitcoin', 'status': 'decoding_transactions_started'}},  # noqa: E501
            {'type': 'transaction_status', 'data': {'addresses': btc_accounts, 'chain': 'BTC', 'subtype': 'bitcoin', 'status': 'querying_transactions_finished'}},  # noqa: E501
            {'type': 'transaction_status', 'data': {'addresses': btc_accounts, 'chain': 'BTC', 'subtype': 'bitcoin', 'status': 'querying_transactions_started'}},  # noqa: E501
        ]
        websocket_connection.messages.clear()

    assert events[74:] == [HistoryEvent(
        identifier=68,
        event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}67c97abe049b671a02e537eb901cd600430ddaa5b09b50434969e360ada748bf'),  # noqa: E501
        sequence_index=0,
        # The two apis disagree on the timestamp here. Seems to be a bug in blockchain.info.
        # I've seen it switch between two different timestamps when repeating the same query.
        # The timestamps are relatively close though, and the timestamp isn't included in the
        # history event unique constraint, so it should be fine.
        timestamp=(timestamp := TimestampMS(1747980089000) if use_blockcypher else TimestampMS(1747979393000)),  # noqa: E501
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal(fee_amount := '0.00000109921082299887260428410372040586245772266065388951521984216459977452085682074'),  # noqa: E501
        location_label=(user_address := btc_accounts[0]),
        notes=f'Spend {fee_amount} BTC for fees',
    ), HistoryEvent(
        identifier=69,
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal(spend_amount := '0.00000890078917700112739571589627959413754227733934611048478015783540022547914317926'),  # noqa: E501
        location_label=user_address,
        notes=f'Send {spend_amount} BTC to bc1pg8vm7hk9ashas2mxkv5g74lxn26w3qr9lqyxrql7tg95j7xja5kqjz3na4',  # noqa: E501
    )]
    assert events[0] == HistoryEvent(
        identifier=67,
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

    # Ensure the cached latest tx timestamp is respected and no decoding is attempted.
    with (
        query_patch,
        patch.object(bitcoin_manager, 'decode_transaction') as mock_decode_tx,
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json=json,
        )
        assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

    assert mock_decode_tx.call_count == 0
