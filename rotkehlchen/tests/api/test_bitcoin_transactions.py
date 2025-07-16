import random
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.bitcoin.bch.constants import BCH_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.btc.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.constants.assets import A_BCH, A_BTC
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures import WebsocketReader
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.types import Location, SupportedBlockchain, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import BTCAddress


def do_tx_query_and_get_events(
        rotkehlchen_api_server: 'APIServer',
        websocket_connection: WebsocketReader,
        accounts: list['BTCAddress'],
        async_query: bool,
        json: dict,
        expected_len: int,
        chain: SupportedBlockchain,
) -> list[HistoryBaseEntry]:
    """Utility function to query transactions and get the decoded events, asserting
    the number of events and the WS messages.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
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
    assert list(websocket_connection.messages) == [  # messages are in descending order
        {'type': 'transaction_status', 'data': {'addresses': accounts, 'chain': chain.value, 'subtype': 'bitcoin', 'status': 'decoding_transactions_finished'}},  # noqa: E501
        {'type': 'transaction_status', 'data': {'addresses': accounts, 'chain': chain.value, 'subtype': 'bitcoin', 'status': 'decoding_transactions_started'}},  # noqa: E501
        {'type': 'transaction_status', 'data': {'addresses': accounts, 'chain': chain.value, 'subtype': 'bitcoin', 'status': 'querying_transactions_finished'}},  # noqa: E501
        {'type': 'transaction_status', 'data': {'addresses': accounts, 'chain': chain.value, 'subtype': 'bitcoin', 'status': 'querying_transactions_started'}},  # noqa: E501
    ]
    websocket_connection.messages.clear()

    return events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
@pytest.mark.parametrize('use_blockcypher', [True, False])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_btc_transactions(
        rotkehlchen_api_server: 'APIServer',
        btc_accounts: list['BTCAddress'],
        use_blockcypher: bool,
        websocket_connection: WebsocketReader,
) -> None:
    """Test that bitcoin transactions are properly queried via the api.
    Since there are quite a number of transactions, only check decoding of first and last txs.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    bitcoin_manager = rotki.chains_aggregator.bitcoin
    if use_blockcypher:  # remove tx function for blockchain.info so it falls back to blockcypher
        assert bitcoin_manager.api_callbacks[0].name == 'blockchain.info'
        bitcoin_manager.api_callbacks[0] = bitcoin_manager.api_callbacks[0]._replace(
            transactions_fn=None,
        )

    async_query = random.choice([False, True])
    for json, expected_len in (
        ({'async_query': async_query, 'to_timestamp': 1740000000}, 67),  # query partial range first  # noqa: E501
        ({'async_query': async_query}, 76),  # then query the rest
    ):
        events = do_tx_query_and_get_events(
            rotkehlchen_api_server=rotkehlchen_api_server,
            websocket_connection=websocket_connection,
            accounts=btc_accounts,
            async_query=async_query,
            json=json,
            expected_len=expected_len,
            chain=SupportedBlockchain.BITCOIN,
        )

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
    with patch.object(bitcoin_manager, 'decode_transaction') as mock_decode_tx:
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json=json,
        )
        assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

    assert mock_decode_tx.call_count == 0


@pytest.mark.vcr
@pytest.mark.freeze_time('2025-07-14 08:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('bch_accounts', [[
    '1Mnwij9Zkk6HtmdNzyEUFgp6ojoLaZekP8',
    'bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt',
    'qrfec2pytp47p5drvfsdexqd0ue4r3hrhv9tq7vj5z',
]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_bch_transactions(
        rotkehlchen_api_server: 'APIServer',
        bch_accounts: list['BTCAddress'],
        websocket_connection: WebsocketReader,
) -> None:
    """Test that bitcoin cash transactions are properly queried via the api.
    Since there are quite a number of transactions, only check decoding of first and last txs.
    """
    async_query = random.choice([False, True])
    for json, expected_len in (
        ({'async_query': async_query, 'to_timestamp': 1700000000}, 79),  # query partial range first  # noqa: E501
        ({'async_query': async_query, 'accounts': [{'address': account, 'blockchain': 'bch'} for account in bch_accounts]}, 104),  # then query the rest  # noqa: E501
    ):
        events = do_tx_query_and_get_events(
            rotkehlchen_api_server=rotkehlchen_api_server,
            websocket_connection=websocket_connection,
            accounts=bch_accounts,
            async_query=async_query,
            json=json,
            expected_len=expected_len,
            chain=SupportedBlockchain.BITCOIN_CASH,
        )

    assert events[100:] == [HistoryEvent(
        identifier=83,
        event_identifier=f'{BCH_EVENT_IDENTIFIER_PREFIX}cc39c599f9684909efbec9a86a37bbe583fd9865f61e90c684b290b092b818f2',
        sequence_index=0,
        timestamp=TimestampMS(1703868928000),
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BCH,
        amount=FVal('1173.95659108'),
        location_label=bch_accounts[2],
        notes=(
            'Receive 1173.95659108 BCH from bitcoincash:qrp0wxt3drg0ucftdw7nuyrf6ptkj53anc3sqggkcr, bitcoincash:qq8rxh3ppnd7nz5nygax9shukgyqqeugruc6qvepp0, '  # noqa: E501
            'bitcoincash:qq6xsy8z0tck5cd3k9y86dnwys60lz6chcaxk3htdc, bitcoincash:qq9rz577fz59sr72czd30am4c46quflexvnwzvs0fm, bitcoincash:qqdm2sagzmlkady4mvpvh8k5nyqydx93wsvsffaar4, '  # noqa: E501
            'bitcoincash:qq02rp4krqc5nxflczac00m3j0s45tqynvye8d6x49, bitcoincash:qqejgx2wrd63hgmf4h8ucalm9sv4v6ex25q9xledjx, bitcoincash:qzkdjrx335cd8rkn9mem6u7m3xk8ejjed5zht3a55c, '  # noqa: E501
            'bitcoincash:qq3cuezq752gl0kh8hc0c8ex64ltk9z5qcnvhk96mh, bitcoincash:qp2q7366pj0ssk84epxnahukylrcjajnjukllvf9wa, bitcoincash:qzl5peg8n9wn6x3knlcagwzu9cr45736ggw8g52pgw, '  # noqa: E501
            'bitcoincash:qzntyrhgytunwalm3668gs572h46vtc3ncqq77fcae, bitcoincash:qrxjnws6nhenl57zz9m9hm5jy004mv9w4gk464qsdx, bitcoincash:qpm2l64983f4j5dx5s5c6ksxkvg44vd4qgpp6uar28, '  # noqa: E501
            'bitcoincash:qruyvm7cn5zqztd53cfqfx4xrxthepq0dycj5ptlk0, bitcoincash:qztd76nqpal6mldcydqpf2qre7ds8ancsg82zecdh2, bitcoincash:qpc0wdxghr2upqkqwfzmtn9h0xvygq59my0zn5keae, '  # noqa: E501
            'bitcoincash:qqg654fzs8cphugjmkl3yx3rs9n6gjv9wun3qp2d5c, bitcoincash:qpa0qpxh8gec4g7xlw88xrmke0tmgsa3mcz7qqm4k9, bitcoincash:qzduv0x5m3uljfqv08p7lma66qrtlj23jc0rkyk5gs, '  # noqa: E501
            'bitcoincash:qzp6f39tzqpldjcugszpuhhysvahtc5rzgha66g79r, bitcoincash:qq3xtnu9vlkt9dsj8us75xayyvww2vx6hyusu2pwkr, bitcoincash:qqhknunxuc60zhcm7lqwd52gewvq0drq0s6vr082gt, '  # noqa: E501
            'bitcoincash:qqa0h85huwpyqumpj8tmp6lc45ksxgv3dsvqrxwgmy'
        ),
    ), HistoryEvent(
        identifier=82,
        event_identifier=f'{BCH_EVENT_IDENTIFIER_PREFIX}dcc1e78d9a48643553f4cd9b71564fb8032f6fd48ede977f8806be15ac29b917',
        sequence_index=0,
        timestamp=TimestampMS(1732270516000),
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BCH,
        amount=(receive_amount_1 := FVal('0.01986791')),
        location_label=(user_address := bch_accounts[1]),
        notes=f'Receive {receive_amount_1} BCH from bitcoincash:qpx003lsm24lu7q2nf7zh640n52gdl2kucna02956q, bitcoincash:qpq4ajfp58lpj70r232pf7pt55s9vm8x4yxmd6c90w',  # noqa: E501
    ), HistoryEvent(
        identifier=80,
        event_identifier=(event_identifier := f'{BCH_EVENT_IDENTIFIER_PREFIX}3944ec023a1a4004d26c476051160ab97c1004a5a34799fc197c885acc745ead'),  # noqa: E501
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749190001000)),
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BCH,
        amount=FVal(fee_amount := '0.00007592'),
        location_label=user_address,
        notes=f'Spend {fee_amount} BCH for fees',
    ), HistoryEvent(
        identifier=81,
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BCH,
        amount=FVal(spend_amount := '0.03559966'),
        location_label=user_address,
        notes=f'Send {spend_amount} BCH to bitcoincash:qr40efj25rw7lmr4qr90636xne2gsmq39ugdsw5k3g',
    )]
    assert events[0] == HistoryEvent(
        identifier=79,
        event_identifier=f'{BCH_EVENT_IDENTIFIER_PREFIX}7eb2146b27dbf6e4ea0d61c2e85a6aeae2415392043fa44904b0a88f1341a662',
        sequence_index=0,
        timestamp=TimestampMS(1545323818000),
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BCH,
        amount=FVal(receive_amount_2 := '616.69939095'),
        location_label=bch_accounts[0],
        notes=f'Receive {receive_amount_2} BCH from bitcoincash:qq9h55edlyekfj46jej23ek3e5sydhqqaqs4s0tjz0',  # noqa: E501
    )
