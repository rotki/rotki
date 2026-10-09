from typing import TYPE_CHECKING, Any
from unittest.mock import call, patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_bitvavo
from rotkehlchen.constants.assets import A_BTC, A_ETC, A_ETH, A_EUR, A_LINK, A_USDC
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.bitvavo import (
    BITVAVO_KEY_HEADER,
    BITVAVO_SIGNATURE_HEADER,
    BITVAVO_TIMESTAMP_HEADER,
    HISTORY_MAX_ITEMS,
    HISTORY_OVERLAP_MS,
    Bitvavo,
    deserialize_bitvavo_timestamp,
)
from rotkehlchen.exchanges.exchange import HistoryEventQueue
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events_multi_fee
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.messages import (
    consume_errors,
    consume_errors_and_unknown_assets,
    consume_warnings,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

TIMESTAMP_MS = 1700490703564


def test_name(bitvavo_exchange: Bitvavo) -> None:
    assert bitvavo_exchange.location == Location.BITVAVO
    assert bitvavo_exchange.name == 'bitvavo'


def test_signature_matches_bitvavo_documentation(bitvavo_exchange: Bitvavo) -> None:
    """The worked example of https://docs.bitvavo.com/docs/rest-api/introduction/ with its
    published inputs and result, so the signing is checked against Bitvavo's own numbers.
    """
    bitvavo_exchange.secret = ApiSecret(b'bitvavo')
    assert bitvavo_exchange._generate_signature(
        method='POST',
        request_path='/v2/order',
        timestamp='1548172481125',
        body='{"market":"BTC-EUR","side":"buy","price":"5000","amount":"1.23","orderType":"limit"}',
    ) == '44d022723a20973a18f7ee97398b9fdd405d2d019c8d39e24b8cc0dcb39ca016'


def test_api_query_headers(bitvavo_exchange: Bitvavo) -> None:
    """The key travels in the session headers, the timestamp and signature per request, and
    the signature covers the path and query string exactly as requests puts them on the wire.
    """
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == bitvavo_exchange.api_key

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        assert (sent_path := requests.Request(
            method='GET',
            url=url,
            params=kwargs['params'],
        ).prepare().path_url) == '/v2/balance?symbol=BTC'
        headers = kwargs['headers']
        assert headers[BITVAVO_TIMESTAMP_HEADER] == str(TIMESTAMP_MS)
        assert headers[BITVAVO_SIGNATURE_HEADER] == bitvavo_exchange._generate_signature(
            method='GET',
            request_path=sent_path,
            timestamp=str(TIMESTAMP_MS),
        )
        return MockResponse(200, '[{"symbol": "BTC", "available": "1", "inOrder": "0"}]')

    with (
        patch.object(bitvavo_exchange.session, 'get', side_effect=mock_get),
        patch('rotkehlchen.exchanges.bitvavo.ts_now_in_ms', return_value=TIMESTAMP_MS),
    ):
        assert bitvavo_exchange._api_query(
            endpoint='/balance',
            options={'symbol': 'BTC'},
        ) == [{'symbol': 'BTC', 'available': '1', 'inOrder': '0'}]


@pytest.mark.parametrize(('response', 'expected_in_msg'), [
    (
        MockResponse(403, '{"errorCode": 311, "error": "Your API key does not have the View access permission."}'),  # noqa: E501
        'error code 311: Your API key does not have the View access permission.',
    ),
    (MockResponse(429, '{"errorCode": 105, "error": "You exceeded the rate limit."}'), 'rate limiting'),  # noqa: E501
    (
        MockResponse(502, '<html>bad gateway</html>'),
        'invalid JSON with HTTP status 502',
    ),
    (MockResponse(500, '{"unexpected": "shape"}'), 'HTTP status 500'),
])
def test_api_query_errors(
        bitvavo_exchange: Bitvavo,
        response: MockResponse,
        expected_in_msg: str,
) -> None:
    with (
        patch.object(bitvavo_exchange.session, 'get', return_value=response),
        pytest.raises(RemoteError, match=expected_in_msg),
    ):
        bitvavo_exchange._api_query(endpoint='/balance')


def test_validate_api_key(bitvavo_exchange: Bitvavo) -> None:
    with patch.object(bitvavo_exchange, '_api_query', return_value=[]):
        assert bitvavo_exchange.validate_api_key() == (True, '')

    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=RemoteError('Bitvavo request at x failed with error code 305: inactive'),
    ):
        valid, msg = bitvavo_exchange.validate_api_key()

    assert valid is False
    assert 'error code 305' in msg


def test_edit_exchange_credentials_updates_key_header(bitvavo_exchange: Bitvavo) -> None:
    """A changed API key has to replace the one the session sends, otherwise requests keep
    authenticating with the old key while being signed with the new secret.
    """
    assert bitvavo_exchange.edit_exchange_credentials(ExchangeAuthCredentials(
        api_key=(new_key := make_api_key()),
        api_secret=(new_secret := make_api_secret()),
        passphrase=None,
    )) is True
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == new_key
    assert bitvavo_exchange.secret == new_secret


def test_edit_exchange_credentials_without_changes(bitvavo_exchange: Bitvavo) -> None:
    old_key = bitvavo_exchange.api_key
    assert bitvavo_exchange.edit_exchange_credentials(ExchangeAuthCredentials(
        api_key=None,
        api_secret=None,
        passphrase=None,
    )) is False
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == old_key


def test_first_connection(bitvavo_exchange: Bitvavo) -> None:
    bitvavo_exchange.first_connection()
    assert bitvavo_exchange.first_connection_made is True


def test_api_query_connection_error(bitvavo_exchange: Bitvavo) -> None:
    with (
        patch.object(
            bitvavo_exchange.session,
            'get',
            side_effect=requests.exceptions.ConnectionError('no route to host'),
        ),
        pytest.raises(RemoteError, match='connection error: no route to host'),
    ):
        bitvavo_exchange._api_query(endpoint='/balance')


def test_query_balances_unexpected_data(bitvavo_exchange: Bitvavo) -> None:
    responses = {'/balance': {'not': 'a list'}, '/stakingBalance': []}
    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=lambda endpoint: responses[endpoint],
    ):
        balances, msg = bitvavo_exchange.query_balances()

    assert balances is None
    assert 'unexpected data' in msg


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances_skips_malformed_entries(bitvavo_exchange: Bitvavo) -> None:
    """A malformed entry is reported and skipped, the rest of the balances still count."""
    responses = {
        '/balance': [
            {'symbol': 'BTC', 'available': '1', 'inOrder': '0'},
            {'symbol': 'ETH', 'available': 'not a number', 'inOrder': '0'},
            {'symbol': 'EUR'},  # amounts missing
        ],
        '/stakingBalance': [{'symbol': 'BTC'}],  # amount missing
    }
    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=lambda endpoint: responses[endpoint],
    ):
        balances, msg = bitvavo_exchange.query_balances()

    assert msg == ''
    assert balances == {A_BTC: Balance(amount=FVal('1'), value=FVal('1.5'))}
    assert consume_errors(bitvavo_exchange.msg_aggregator) == [
        'Failed to deserialize a Bitvavo balance entry. Check logs for details. Ignoring it.',
    ] * 3


def test_query_online_margin_history(bitvavo_exchange: Bitvavo) -> None:
    assert bitvavo_exchange.query_online_margin_history(
        start_ts=Timestamp(0),
        end_ts=Timestamp(1),
    ) == []


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(bitvavo_exchange: Bitvavo) -> None:
    """available, inOrder and the Fixed Staking amount are summed per asset, zero balances
    and unknown assets are skipped.
    """
    responses = {
        '/balance': [
            {'symbol': 'BTC', 'available': '1.1', 'inOrder': '0.4'},
            {'symbol': 'EUR', 'available': '250.5', 'inOrder': '0'},
            {'symbol': 'ETH', 'available': '0', 'inOrder': '0'},
            {'symbol': 'NOTAREALASSET', 'available': '5', 'inOrder': '0'},
        ],
        '/stakingBalance': [
            {'symbol': 'BTC', 'amount': '0.5'},  # adds to the tradeable BTC
            {'symbol': 'ETC', 'amount': '3'},  # held only in Fixed Staking
            {'symbol': 'ETH', 'amount': '0'},
        ],
    }
    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=lambda endpoint: responses[endpoint],
    ) as api_query:
        balances, msg = bitvavo_exchange.query_balances()

    assert api_query.call_args_list == [
        call(endpoint='/balance'),
        call(endpoint='/stakingBalance'),
    ]
    assert msg == ''
    assert balances == {
        A_BTC: Balance(amount=FVal('2'), value=FVal('3')),
        A_EUR: Balance(amount=FVal('250.5'), value=FVal('375.75')),
        A_ETC: Balance(amount=FVal('3'), value=FVal('4.5')),
    }
    assert consume_errors_and_unknown_assets(bitvavo_exchange.msg_aggregator) == ([], ['NOTAREALASSET'])  # noqa: E501


def test_query_balances_staking_query_fails(bitvavo_exchange: Bitvavo) -> None:
    """A failing staking query fails the whole balance query instead of silently
    reporting only the tradeable part.
    """
    def mock_api_query(endpoint: str) -> list[dict[str, str]]:
        if endpoint == '/stakingBalance':
            raise RemoteError('staking endpoint down')
        return [{'symbol': 'BTC', 'available': '1', 'inOrder': '0'}]

    with patch.object(bitvavo_exchange, '_api_query', side_effect=mock_api_query):
        balances, msg = bitvavo_exchange.query_balances()

    assert balances is None
    assert 'staking endpoint down' in msg


def test_query_balances_remote_error(bitvavo_exchange: Bitvavo) -> None:
    with patch.object(bitvavo_exchange, '_api_query', side_effect=RemoteError('boom')):
        balances, msg = bitvavo_exchange.query_balances()

    assert balances is None
    assert msg == 'Failed to query Bitvavo balances due to a remote error: boom'


@pytest.mark.parametrize(('value', 'expected'), [
    ('2024-03-01T10:00:00.250Z', 1709287200250),  # trades carry milliseconds
    ('2024-03-05T14:00:00.000Z', 1709647200000),
    ('2021-01-01T00:00:01Z', 1609459201000),  # whole seconds, no fraction
    ('2021-01-01T00:00:01', 1609459201000),  # no timezone given, read as UTC
])
def test_deserialize_timestamp(value: str, expected: int) -> None:
    assert deserialize_bitvavo_timestamp(value) == TimestampMS(expected)


@pytest.mark.parametrize('value', ['not a date', None, 1709287200250])
def test_deserialize_timestamp_invalid(value: object) -> None:
    with pytest.raises(DeserializationError):
        deserialize_bitvavo_timestamp(value)


def group_id(unique_id: str) -> str:
    return create_group_identifier_from_unique_id(location=Location.BITVAVO, unique_id=unique_id)


# Rows in the shape GET /account/history returns them, one per handled case.
LEDGER_PAGE_1: list[dict[str, Any]] = [
    {
        'transactionId': 'buy-1', 'executedAt': '2024-03-01T10:00:00.250Z', 'type': 'buy',
        'priceCurrency': 'EUR', 'priceAmount': '2500',
        'sentCurrency': 'EUR', 'sentAmount': '100',
        'receivedCurrency': 'ETH', 'receivedAmount': '0.04',
        'feesCurrency': 'EUR', 'feesAmount': '0.25', 'address': None,
    }, {
        'transactionId': 'sell-1', 'executedAt': '2024-03-02T11:30:15.500Z', 'type': 'sell',
        'priceCurrency': 'EUR', 'priceAmount': '45000',
        'sentCurrency': 'BTC', 'sentAmount': '0.01',
        'receivedCurrency': 'EUR', 'receivedAmount': '450',
        'feesCurrency': 'EUR', 'feesAmount': '1.25', 'address': None,
    }, {  # fiat deposit: masked IBAN as address and an explicit zero fee
        'transactionId': 'dep-1', 'executedAt': '2024-03-03T12:00:00.000Z', 'type': 'deposit',
        'receivedCurrency': 'EUR', 'receivedAmount': '1000',
        'feesCurrency': 'EUR', 'feesAmount': '0', 'address': 'NL00**',
    }, {  # crypto withdrawal: sent amount is net, fee separate
        'transactionId': 'wd-1', 'executedAt': '2024-03-04T13:00:00.000Z', 'type': 'withdrawal',
        'sentCurrency': 'ETH', 'sentAmount': '0.99',
        'feesCurrency': 'ETH', 'feesAmount': '0.01', 'address': '0x1234',
    }, {  # withdrawal without any fee fields
        'transactionId': 'wd-2', 'executedAt': '2024-03-04T13:00:00.000Z', 'type': 'withdrawal',
        'sentCurrency': 'EUR', 'sentAmount': '100', 'address': 'NL00**',
    }, {
        'transactionId': 'stk-1', 'executedAt': '2024-03-05T14:00:00.000Z', 'type': 'staking',
        'receivedCurrency': 'BTC', 'receivedAmount': '0.00000123', 'address': None,
    }, {
        'transactionId': 'aff-1', 'executedAt': '2024-03-06T00:00:04.000Z', 'type': 'affiliate',
        'receivedCurrency': 'EUR', 'receivedAmount': '1.5', 'address': None,
    }, {
        'transactionId': 'reb-1', 'executedAt': '2024-03-07T16:00:00.000Z', 'type': 'rebate',
        'receivedCurrency': 'EUR', 'receivedAmount': '0.05', 'address': None,
    }, {  # corrections booked by Bitvavo support go in both directions
        'transactionId': 'adj-1', 'executedAt': '2024-03-08T09:00:00.000Z',
        'type': 'manually_assigned', 'sentCurrency': 'ETC', 'sentAmount': '0.00000042',
    }, {
        'transactionId': 'adj-2', 'executedAt': '2024-03-08T09:00:00.000Z',
        'type': 'manually_assigned', 'receivedCurrency': 'ETC', 'receivedAmount': '0.5',
    }, {  # documented by Bitvavo but not handled: reported, never skipped silently
        'transactionId': 'wc-1', 'executedAt': '2024-03-08T09:00:00.000Z',
        'type': 'withdrawal_cancelled', 'receivedCurrency': 'ETH', 'receivedAmount': '1',
    }, {  # a type Bitvavo does not document: reported once for both rows
        'transactionId': 'unk-1', 'executedAt': '2024-03-08T09:00:00.000Z',
        'type': 'margin_interest', 'sentCurrency': 'EUR', 'sentAmount': '1',
    }, {
        'transactionId': 'unk-2', 'executedAt': '2024-03-08T09:00:00.000Z',
        'type': 'margin_interest', 'sentCurrency': 'EUR', 'sentAmount': '2',
    }, {  # unknown asset: skipped with an unknown asset message
        'transactionId': 'stk-2', 'executedAt': '2024-03-05T14:00:00.000Z', 'type': 'staking',
        'receivedCurrency': 'NOTAREALASSET', 'receivedAmount': '1',
    }, {  # broken row: missing the amount
        'transactionId': 'bad-1', 'executedAt': '2024-03-05T14:00:00.000Z', 'type': 'staking',
        'receivedCurrency': 'BTC',
    },
]
LEDGER_PAGE_2: list[dict[str, Any]] = [
    {  # crypto deposit on the second page, no address
        'transactionId': 'dep-2', 'executedAt': '2024-03-09T10:00:00.000Z', 'type': 'deposit',
        'receivedCurrency': 'BTC', 'receivedAmount': '0.5', 'address': None,
    },
]


def expected_ledger_events() -> list[HistoryBaseEntry]:
    a_eur, a_btc, a_eth, a_etc = (
        a.resolve_to_asset_with_oracles() for a in (A_EUR, A_BTC, A_ETH, A_ETC)
    )
    return [
        *create_swap_events_multi_fee(
            timestamp=TimestampMS(1709287200250),
            location=Location.BITVAVO,
            spend=AssetAmount(asset=a_eur, amount=FVal('100')),
            receive=AssetAmount(asset=a_eth, amount=FVal('0.04')),
            fees=[(AssetAmount(asset=a_eur, amount=FVal('0.25')), None, None)],
            location_label='bitvavo',
            group_identifier=group_id('buy-1'),
        ),
        *create_swap_events_multi_fee(
            timestamp=TimestampMS(1709379015500),
            location=Location.BITVAVO,
            spend=AssetAmount(asset=a_btc, amount=FVal('0.01')),
            receive=AssetAmount(asset=a_eur, amount=FVal('450')),
            fees=[(AssetAmount(asset=a_eur, amount=FVal('1.25')), None, None)],
            location_label='bitvavo',
            group_identifier=group_id('sell-1'),
        ),
        *create_asset_movement_with_fee(
            timestamp=TimestampMS(1709467200000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_eur,
            amount=FVal('1000'),
            unique_id='dep-1',
            extra_data={'address': 'NL00**'},
        ),
        *create_asset_movement_with_fee(
            timestamp=TimestampMS(1709557200000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_eth,
            amount=FVal('0.99'),
            fee=AssetAmount(asset=a_eth, amount=FVal('0.01')),
            unique_id='wd-1',
            extra_data={'address': '0x1234'},
        ),
        *create_asset_movement_with_fee(
            timestamp=TimestampMS(1709557200000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_eur,
            amount=FVal('100'),
            unique_id='wd-2',
            extra_data={'address': 'NL00**'},
        ),
        HistoryEvent(
            group_identifier=group_id('stk-1'),
            sequence_index=0,
            timestamp=TimestampMS(1709647200000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            asset=a_btc,
            amount=FVal('0.00000123'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            notes='Staking reward of 0.00000123 BTC at Bitvavo',
        ),
        HistoryEvent(
            group_identifier=group_id('aff-1'),
            sequence_index=0,
            timestamp=TimestampMS(1709683204000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            asset=a_eur,
            amount=FVal('1.5'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            notes='Affiliate reward of 1.5 EUR at Bitvavo',
        ),
        HistoryEvent(
            group_identifier=group_id('reb-1'),
            sequence_index=0,
            timestamp=TimestampMS(1709827200000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            asset=a_eur,
            amount=FVal('0.05'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.CASHBACK,
            notes='Fee rebate of 0.05 EUR at Bitvavo',
        ),
        HistoryEvent(
            group_identifier=group_id('adj-1'),
            sequence_index=0,
            timestamp=TimestampMS(1709888400000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            asset=a_etc,
            amount=FVal('0.00000042'),
            event_type=HistoryEventType.ADJUSTMENT,
            event_subtype=HistoryEventSubType.SPEND,
            notes='Balance correction of 0.00000042 ETC at Bitvavo',
        ),
        HistoryEvent(
            group_identifier=group_id('adj-2'),
            sequence_index=0,
            timestamp=TimestampMS(1709888400000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            asset=a_etc,
            amount=FVal('0.5'),
            event_type=HistoryEventType.ADJUSTMENT,
            event_subtype=HistoryEventSubType.RECEIVE,
            notes='Balance correction of 0.5 ETC at Bitvavo',
        ),
        *create_asset_movement_with_fee(
            timestamp=TimestampMS(1709978400000),
            location=Location.BITVAVO,
            location_label='bitvavo',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_btc,
            amount=FVal('0.5'),
            unique_id='dep-2',
        ),
    ]


def mock_ledger_pages() -> Callable[..., dict[str, Any]]:
    def mock_api_query(endpoint: str, options: dict[str, Any]) -> dict[str, Any]:
        assert endpoint == '/account/history'
        page = options['page']
        return {
            'items': LEDGER_PAGE_1 if page == 1 else LEDGER_PAGE_2,
            'currentPage': page,
            'totalPages': 2,
            'maxItems': HISTORY_MAX_ITEMS,
        }
    return mock_api_query


def test_query_online_history_events(bitvavo_exchange: Bitvavo) -> None:
    """Every handled ledger row type is dispatched to the right event shape, unhandled
    types are skipped with a warning that names every skipped type, and the range is always
    sent because the endpoint otherwise silently returns only the last 30 days. It starts
    before the requested start, so that it overlaps the range queried before it.
    """
    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=mock_ledger_pages(),
    ) as api_query:
        events, end_ts = bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert end_ts == Timestamp(1800000000)
    assert api_query.call_args_list == [
        call(endpoint='/account/history', options={
            'fromDate': 1599999998000,
            'toDate': 1800000000000,
            'maxItems': HISTORY_MAX_ITEMS,
            'page': page,
        }) for page in (1, 2)
    ]
    assert events == expected_ledger_events()
    assert consume_warnings(bitvavo_exchange.msg_aggregator) == [(
        'Skipped Bitvavo history entries of type margin_interest, withdrawal_cancelled, which '
        'rotki does not handle yet. Check logs for details and report it to rotki.'
    )] * 2  # one warning per type, folded into one row that names both
    assert consume_errors_and_unknown_assets(bitvavo_exchange.msg_aggregator) == ([(
        "Failed to deserialize a Bitvavo history entry: Missing key 'receivedAmount'. "
        'Check logs for details. Ignoring it.'
    )], ['NOTAREALASSET'])


def test_query_online_history_events_into_queue(bitvavo_exchange: Bitvavo) -> None:
    """With an event queue the events are saved through it and none are returned."""
    queue = HistoryEventQueue(
        database=bitvavo_exchange.db,
        location_string='bitvavo_history_events_bitvavo',
        query_start_ts=Timestamp(1600000000),
    )
    with patch.object(bitvavo_exchange, '_api_query', side_effect=mock_ledger_pages()):
        end_ts = bitvavo_exchange.query_online_history_events_into_queue(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
            event_queue=queue,
        )

    assert end_ts == Timestamp(1800000000)
    assert queue.events == []
    assert queue.saved_events == len(expected_ledger_events())


def test_query_online_history_events_remote_error(bitvavo_exchange: Bitvavo) -> None:
    with (
        patch.object(bitvavo_exchange, '_api_query', side_effect=RemoteError('boom')),
        pytest.raises(RemoteError, match='boom'),
    ):
        bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert consume_errors(bitvavo_exchange.msg_aggregator) == [
        'Got remote error while querying Bitvavo history: boom',
    ]


def test_query_online_history_events_unexpected_data(bitvavo_exchange: Bitvavo) -> None:
    with (
        patch.object(bitvavo_exchange, '_api_query', return_value=[{'not': 'a page'}]),
        pytest.raises(RemoteError, match='unexpected data'),
    ):
        bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )


def test_failure_on_a_later_page_keeps_earlier_pages_and_records_no_range(
        bitvavo_exchange: Bitvavo,
) -> None:
    """Pages are saved as they arrive, so a failure halfway loses nothing that was already
    fetched, and the range is not marked as queried, so the next query fetches the rest.
    """
    def mock_api_query(endpoint: str, options: dict[str, Any]) -> dict[str, Any]:  # pylint: disable=unused-argument
        if options['page'] == 2:
            raise RemoteError('page two failed')
        return {'items': LEDGER_PAGE_1, 'currentPage': 1, 'totalPages': 2}

    with (
        patch.object(bitvavo_exchange, '_api_query', side_effect=mock_api_query),
        pytest.raises(RemoteError, match='page two failed'),
    ):
        bitvavo_exchange.query_history_events()

    with bitvavo_exchange.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (group_id('buy-1'),),
        ).fetchone()[0] == 3  # spend, receive and fee of the first row of page one
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name=?',
            (f'{Location.BITVAVO!s}_history_events_{bitvavo_exchange.name}',),
        ).fetchone()[0] == 0


@pytest.mark.parametrize(('start_ts', 'from_date'), [
    (1600000000, 1600000000000 - HISTORY_OVERLAP_MS),
    (1, 0),
    (0, 0),
])
def test_history_range_reaches_back_before_its_start(
        bitvavo_exchange: Bitvavo,
        start_ts: int,
        from_date: int,
) -> None:
    """rotki starts a range one second after the previous one ended. A trade stamped inside
    that last second, which Bitvavo reports in milliseconds, is only fetched when the next
    query reaches back over it, which is why the overlap is longer than that one second.
    The start of time is not passed as a negative value.
    """
    with patch.object(bitvavo_exchange, '_api_query', return_value={
        'items': [], 'currentPage': 1, 'totalPages': 1,
    }) as api_query:
        bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(1800000000),
        )

    assert api_query.call_args.kwargs['options']['fromDate'] == from_date


def test_pagination_without_a_page_count_continues_until_a_short_page(
        bitvavo_exchange: Bitvavo,
) -> None:
    """A response without totalPages must not end the query after the first page, which
    would silently drop the rest of the history.
    """
    def mock_api_query(endpoint: str, options: dict[str, Any]) -> dict[str, Any]:  # pylint: disable=unused-argument
        return {'items': LEDGER_PAGE_1 if options['page'] == 1 else LEDGER_PAGE_2}

    with (
        patch('rotkehlchen.exchanges.bitvavo.HISTORY_MAX_ITEMS', len(LEDGER_PAGE_1)),
        patch.object(bitvavo_exchange, '_api_query', side_effect=mock_api_query) as api_query,
    ):
        events, _ = bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert api_query.call_count == 2
    assert events == expected_ledger_events()


def test_asset_symbol_resolution() -> None:
    """Symbols that are not rotki identifiers resolve through the exchange symbol mappings,
    the others directly, and an unknown symbol is an error instead of a guess.
    """
    assert asset_from_bitvavo('USDC') == A_USDC
    assert asset_from_bitvavo('LINK') == A_LINK
    assert asset_from_bitvavo('EUR') == A_EUR
    assert asset_from_bitvavo('BTC') == A_BTC
    assert asset_from_bitvavo('XRP') == Asset('XRP')
    with pytest.raises(UnknownAsset):
        asset_from_bitvavo('NOTAREALASSET')


def ledger_row(ledger_type: str, side: str = 'received') -> dict[str, str]:
    return {
        'transactionId': f'{ledger_type}-row',
        'executedAt': '2024-03-05T14:00:00.000Z',
        'type': ledger_type,
        f'{side}Currency': 'ETH',
        f'{side}Amount': '1.5',
    }


@pytest.mark.parametrize(('ledger_type', 'event_type', 'event_subtype', 'notes_prefix'), [
    ('staking', HistoryEventType.STAKING, HistoryEventSubType.REWARD, 'Staking reward'),
    ('fixed_staking', HistoryEventType.STAKING, HistoryEventSubType.REWARD, 'Fixed staking reward'),  # noqa: E501
    ('affiliate', HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, 'Affiliate reward'),
    ('rebate', HistoryEventType.RECEIVE, HistoryEventSubType.CASHBACK, 'Fee rebate'),
    ('distribution', HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, 'Distribution'),
])
def test_reward_ledger_types(
        bitvavo_exchange: Bitvavo,
        ledger_type: str,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        notes_prefix: str,
) -> None:
    """Pins the event type and subtype of every crediting ledger type, since the pair decides
    the default tax treatment.
    """
    assert bitvavo_exchange._deserialize_ledger_entry(ledger_row(ledger_type)) == [HistoryEvent(
        group_identifier=group_id(f'{ledger_type}-row'),
        sequence_index=0,
        timestamp=TimestampMS(1709647200000),
        location=Location.BITVAVO,
        location_label='bitvavo',
        asset=A_ETH,
        amount=FVal('1.5'),
        event_type=event_type,
        event_subtype=event_subtype,
        notes=f'{notes_prefix} of 1.5 ETH at Bitvavo',
    )]


@pytest.mark.parametrize('ledger_type', ['manually_assigned', 'manually_assigned_bitvavo'])
@pytest.mark.parametrize(('side', 'event_subtype'), [
    ('received', HistoryEventSubType.RECEIVE),
    ('sent', HistoryEventSubType.SPEND),
])
def test_adjustment_ledger_types(
        bitvavo_exchange: Bitvavo,
        ledger_type: str,
        side: str,
        event_subtype: HistoryEventSubType,
) -> None:
    """Corrections follow the side Bitvavo filled, and use ADJUSTMENT so the tracked balance
    moves, which EXCHANGE_ADJUSTMENT would not do.
    """
    (event,) = bitvavo_exchange._deserialize_ledger_entry(ledger_row(ledger_type, side=side))
    assert (event.event_type, event.event_subtype) == (HistoryEventType.ADJUSTMENT, event_subtype)
    assert event.amount == FVal('1.5')
    assert event.notes == 'Balance correction of 1.5 ETH at Bitvavo'


@pytest.mark.parametrize('ledger_type', [
    'loan',
    'withdrawal_cancelled',
    'internal_transfer',
    'external_transferred_funds',
    'a_type_bitvavo_adds_later',
])
def test_unhandled_ledger_types_are_reported(bitvavo_exchange: Bitvavo, ledger_type: str) -> None:
    assert bitvavo_exchange._deserialize_ledger_entry(ledger_row(ledger_type)) == []
    assert consume_warnings(bitvavo_exchange.msg_aggregator) == [(
        f'Skipped Bitvavo history entries of type {ledger_type}, which rotki does not '
        f'handle yet. Check logs for details and report it to rotki.'
    )]


def test_querying_the_same_range_again_saves_nothing(bitvavo_exchange: Bitvavo) -> None:
    """Re-pulling a range must not duplicate events, or income would count twice."""
    saved = []
    for _ in range(2):
        queue = HistoryEventQueue(
            database=bitvavo_exchange.db,
            location_string='bitvavo_history_events_bitvavo',
            query_start_ts=Timestamp(1600000000),
        )
        with patch.object(bitvavo_exchange, '_api_query', side_effect=mock_ledger_pages()):
            bitvavo_exchange.query_online_history_events_into_queue(
                start_ts=Timestamp(1600000000),
                end_ts=Timestamp(1800000000),
                event_queue=queue,
            )
        saved.append(queue.saved_events)

    assert saved == [len(expected_ledger_events()), 0]


@pytest.mark.parametrize('unknown_side', ['sent', 'received', 'fees'])
def test_trade_with_an_unknown_asset_is_skipped_whole(
        bitvavo_exchange: Bitvavo,
        unknown_side: str,
) -> None:
    """Half a swap would corrupt balances, so no leg may be created when any asset of the
    trade cannot be resolved.
    """
    row: dict[str, Any] = {**LEDGER_PAGE_1[0], f'{unknown_side}Currency': 'NOTAREALASSET'}
    with patch.object(bitvavo_exchange, '_api_query', return_value={
        'items': [row], 'currentPage': 1, 'totalPages': 1, 'maxItems': HISTORY_MAX_ITEMS,
    }):
        events, _ = bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert events == []
    assert consume_errors_and_unknown_assets(bitvavo_exchange.msg_aggregator) == ([], ['NOTAREALASSET'])  # noqa: E501


def test_pagination_stops_on_an_empty_page(bitvavo_exchange: Bitvavo) -> None:
    """An empty page ends the query even if totalPages claims there is more."""
    def mock_api_query(endpoint: str, options: dict[str, Any]) -> dict[str, Any]:  # pylint: disable=unused-argument
        return {
            'items': LEDGER_PAGE_2 if options['page'] == 1 else [],
            'currentPage': options['page'],
            'totalPages': 99,
            'maxItems': HISTORY_MAX_ITEMS,
        }

    with patch.object(bitvavo_exchange, '_api_query', side_effect=mock_api_query) as api_query:
        events, _ = bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert api_query.call_count == 2
    assert len(events) == 1


@pytest.mark.parametrize(('override', 'expected_in_error'), [
    ({'receivedAmount': 'not a number'}, 'Failed to deserialize value entry'),
    ({'executedAt': 'not a date'}, 'Failed to deserialize Bitvavo timestamp from not a date'),
])
def test_ledger_row_with_an_unparseable_value_is_reported(
        bitvavo_exchange: Bitvavo,
        override: dict[str, str],
        expected_in_error: str,
) -> None:
    """A row whose amount or timestamp cannot be read is reported and skipped, and the rows
    around it are still imported.
    """
    with patch.object(bitvavo_exchange, '_api_query', return_value={
        'items': [ledger_row('staking') | override, *LEDGER_PAGE_2],
        'currentPage': 1,
        'totalPages': 1,
        'maxItems': HISTORY_MAX_ITEMS,
    }):
        events, _ = bitvavo_exchange.query_online_history_events(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1800000000),
        )

    assert len(events) == 1
    (error,) = consume_errors(bitvavo_exchange.msg_aggregator)
    assert error.startswith('Failed to deserialize a Bitvavo history entry: ')
    assert expected_in_error in error
