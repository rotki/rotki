"""Tests for Bit2me exchange integration."""
from unittest.mock import patch

import pytest

from rotkehlchen.assets.converters import asset_from_bit2me
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp

# Sample API responses based on real Bit2Me API data
# Note: The pocket API returns "currency" field for the currency symbol
BIT2ME_BALANCES_RESPONSE = """[
  {
    "id": "603177ce-7a00-40d6-adef-3670832c2a51",
    "userId": "test-user-id",
    "currency": "EUR",
    "balance": "1500.50000000",
    "blockedBalance": "100.00000000",
    "blockedOutputBalance": "0.00000000",
    "name": "EUR",
    "color": 0,
    "createdAt": "2025-11-09T12:53:14.229Z"
  },
  {
    "id": "339b61c6-df74-409c-85a4-68c421da6382",
    "userId": "test-user-id",
    "currency": "BTC",
    "balance": "0.50000000",
    "blockedBalance": "0.10000000",
    "blockedOutputBalance": "0.00000000",
    "name": "BTC 1",
    "color": 0,
    "createdAt": "2025-11-09T13:40:59.297Z"
  },
  {
    "id": "d12d3a93-eda4-47a4-bdb6-f2168e918c54",
    "userId": "test-user-id",
    "currency": "ETH",
    "balance": "2.00000000",
    "blockedBalance": "0.00000000",
    "blockedOutputBalance": "0.00000000",
    "name": "ETH 1",
    "color": 0,
    "createdAt": "2025-11-09T14:06:25.836Z"
  },
  {
    "id": "zero-balance-wallet",
    "userId": "test-user-id",
    "currency": "DOGE",
    "balance": "0.00000000",
    "blockedBalance": "0.00000000",
    "blockedOutputBalance": "0.00000000",
    "name": "DOGE 1",
    "color": 0,
    "createdAt": "2025-11-09T14:06:25.836Z"
  }
]"""

BIT2ME_TRANSACTIONS_RESPONSE = """{
  "total": 4,
  "data": [
    {
      "id": "withdrawal-eth-001",
      "date": "2025-12-07T18:14:51.257Z",
      "completedAt": "2025-12-07T18:19:43.431Z",
      "canceledAt": null,
      "concept": "",
      "type": "withdrawal",
      "subtype": "automatic-send",
      "method": "blockchain",
      "status": "completed",
      "denomination": {
        "amount": "0.50000000",
        "currency": "ETH"
      },
      "frequency": "punctual",
      "isInitialRecurringOrder": false,
      "origin": {
        "pocketName": "",
        "pocketId": "d12d3a93-eda4-47a4-bdb6-f2168e918c54",
        "amount": "0.50000000",
        "currency": "ETH",
        "class": "pocket"
      },
      "destination": {
        "pocketName": null,
        "pocketId": null,
        "amount": "0.49900000",
        "currency": "ETH",
        "address": "0xaf461f2c27e472c0e30e9aa8394a844fbedbe0f8",
        "addressNetwork": "ethereum",
        "class": "blockchain"
      }
    },
    {
      "id": "deposit-eur-001",
      "date": "2025-11-18T23:04:03.372Z",
      "completedAt": "2025-11-18T23:04:03.372Z",
      "canceledAt": null,
      "concept": "Bank deposit",
      "type": "deposit",
      "subtype": "funding",
      "method": "bank-transfer",
      "status": "completed",
      "denomination": {
        "amount": "1000.00000000",
        "currency": "EUR"
      },
      "frequency": "punctual",
      "isInitialRecurringOrder": false,
      "origin": {
        "pocketName": null,
        "pocketId": null,
        "amount": "1000.00000000",
        "currency": "EUR",
        "bankAccount": "ES7114650100911707548049",
        "class": "bank-transfer"
      },
      "destination": {
        "pocketName": "",
        "pocketId": "603177ce-7a00-40d6-adef-3670832c2a51",
        "amount": "1000.00000000",
        "currency": "EUR",
        "class": "pocket"
      }
    },
    {
      "id": "purchase-btc-001",
      "date": "2025-11-18T23:33:51.381Z",
      "completedAt": "2025-11-18T23:33:51.381Z",
      "canceledAt": null,
      "concept": "",
      "type": "transfer",
      "subtype": "purchase",
      "method": "pocket",
      "status": "completed",
      "denomination": {
        "amount": "100.00000000",
        "currency": "EUR"
      },
      "frequency": "punctual",
      "isInitialRecurringOrder": false,
      "origin": {
        "pocketName": "",
        "pocketId": "603177ce-7a00-40d6-adef-3670832c2a51",
        "amount": "100.00000000",
        "currency": "EUR",
        "class": "pocket"
      },
      "destination": {
        "pocketName": "",
        "pocketId": "339b61c6-df74-409c-85a4-68c421da6382",
        "amount": "0.00122130",
        "currency": "BTC",
        "class": "pocket"
      },
      "instantId": "390ab3d9-20c4-4087-a170-4a7ef51ab1a4"
    },
    {
      "id": "internal-transfer-001",
      "date": "2025-11-15T10:00:00.000Z",
      "completedAt": "2025-11-15T10:00:00.000Z",
      "canceledAt": null,
      "concept": "Internal transfer",
      "type": "transfer",
      "subtype": "internal",
      "method": "pocket",
      "status": "completed",
      "denomination": {
        "amount": "50.00000000",
        "currency": "EUR"
      },
      "frequency": "punctual",
      "isInitialRecurringOrder": false,
      "origin": {
        "pocketName": "",
        "pocketId": "pocket-1",
        "amount": "50.00000000",
        "currency": "EUR",
        "class": "pocket"
      },
      "destination": {
        "pocketName": "",
        "pocketId": "pocket-2",
        "amount": "50.00000000",
        "currency": "EUR",
        "class": "pocket"
      }
    }
  ]
}"""

BIT2ME_EARN_TRANSACTIONS_RESPONSE = """{
  "total": 3,
  "data": [
    {
      "id": "earn-deposit-btc-001",
      "date": "2025-12-24T07:42:21.068Z",
      "type": "withdrawal",
      "subtype": "earn",
      "status": "completed",
      "origin": {
        "pocketId": "339b61c6-df74-409c-85a4-68c421da6382",
        "amount": "0.50000000",
        "currency": "BTC",
        "class": "pocket"
      },
      "destination": {
        "amount": "0.50000000",
        "currency": "BTC",
        "class": "earn"
      }
    },
    {
      "id": "earn-withdrawal-btc-001",
      "date": "2025-12-25T10:00:00.000Z",
      "type": "deposit",
      "subtype": "earn",
      "status": "completed",
      "origin": {
        "amount": "0.10000000",
        "currency": "BTC",
        "class": "earn"
      },
      "destination": {
        "pocketId": "339b61c6-df74-409c-85a4-68c421da6382",
        "amount": "0.10000000",
        "currency": "BTC",
        "class": "pocket"
      }
    },
    {
      "id": "earn-deposit-eth-001",
      "date": "2025-12-20T12:00:00.000Z",
      "type": "withdrawal",
      "subtype": "earn",
      "status": "completed",
      "origin": {
        "pocketId": "d12d3a93-eda4-47a4-bdb6-f2168e918c54",
        "amount": "1.00000000",
        "currency": "ETH",
        "class": "pocket"
      },
      "destination": {
        "amount": "1.00000000",
        "currency": "ETH",
        "class": "earn"
      }
    }
  ]
}"""

BIT2ME_TRADES_RESPONSE = """{
  "trades": []
}"""


def test_bit2me_location(bit2me):
    """Test that Bit2me has the correct location."""
    assert bit2me.location == Location.BIT2ME
    assert bit2me.location_id().location == Location.BIT2ME


def test_bit2me_name(bit2me):
    """Test that Bit2me has the correct name."""
    assert bit2me.name == 'bit2me'


def test_bit2me_signature_generation(bit2me):
    """Test signature generation for Bit2me API."""
    path = '/v1/wallet/pocket'
    nonce, signature = bit2me._generate_signature(path)

    # Verify nonce is a timestamp string
    assert isinstance(nonce, str)
    assert nonce.isdigit()
    assert len(nonce) == 13  # milliseconds timestamp

    # Verify signature is base64 encoded
    assert isinstance(signature, str)
    assert len(signature) > 0


def test_bit2me_signature_with_body(bit2me):
    """Test signature generation with request body."""
    path = '/v1/trading/order'
    body = {'symbol': 'BTC-EUR', 'side': 'buy'}
    _, signature = bit2me._generate_signature(path, body)

    # Verify signature is different when body is included
    _, signature2 = bit2me._generate_signature(path)
    assert signature != signature2


def test_bit2me_query_balances(bit2me):
    """Test querying balances from Bit2me."""

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BIT2ME_BALANCES_RESPONSE)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        balances, msg = bit2me.query_balances()

    assert msg == ''
    # Should have 3 balances (EUR, BTC, ETH) - DOGE has zero balance and is skipped
    assert len(balances) == 3

    # Check EUR balance (1500.50 + 100 blocked = 1600.50)
    assert balances[A_EUR].amount == FVal('1600.50')

    # Check BTC balance (0.5 + 0.1 blocked = 0.6)
    assert balances[A_BTC].amount == FVal('0.60')

    # Check ETH balance (2.0)
    assert balances[A_ETH].amount == FVal('2.0')


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_bit2me_query_balances_unknown_asset(bit2me):
    """Test that if a Bit2me balance query returns unknown asset no exception
    is raised and a warning is logged."""
    response = BIT2ME_BALANCES_RESPONSE.replace(
        '"currency": "BTC"', '"currency": "UNKNOWN_ASSET_XYZ"',
    )

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, response)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        balances, msg = bit2me.query_balances()

    assert msg == ''
    # Should still have EUR and ETH, but not the unknown asset
    assert len(balances) == 2
    assert A_EUR in balances
    assert A_ETH in balances


def test_bit2me_query_balances_with_earn(bit2me):
    """Test that EARN balances are included in the total balance.

    EARN balances are calculated from earn transactions:
    - withdrawal/earn with dest_class=earn = deposit TO earn (adds)
    - deposit/earn with dest_class=pocket = withdrawal FROM earn (subtracts)
    """

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        if 'transaction' in url:
            return MockResponse(200, BIT2ME_EARN_TRANSACTIONS_RESPONSE)
        return MockResponse(200, BIT2ME_BALANCES_RESPONSE)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        balances, msg = bit2me.query_balances()

    assert msg == ''

    # BTC: pocket (0.5 + 0.1 blocked) + earn (0.5 deposited - 0.1 withdrawn) = 1.0
    assert A_BTC in balances
    assert balances[A_BTC].amount == FVal('1.0')

    # ETH: pocket (2.0) + earn (1.0 deposited) = 3.0
    assert A_ETH in balances
    assert balances[A_ETH].amount == FVal('3.0')

    # EUR should still be just pocket balance
    assert A_EUR in balances
    assert balances[A_EUR].amount == FVal('1600.50')


def test_bit2me_query_deposits_withdrawals(bit2me):
    """Test querying deposit/withdrawal history from Bit2me."""

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BIT2ME_TRANSACTIONS_RESPONSE)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        movements = bit2me.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1800000000),
        )

    # Should have 3 movements: 1 deposit (no fee for bank transfer) + 2 withdrawal (event + fee)
    # The purchase (transfer) and internal transfer are skipped
    assert len(movements) == 3

    # Find the withdrawal events
    withdrawal_events = [m for m in movements if m.event_type == HistoryEventType.WITHDRAWAL]
    assert len(withdrawal_events) == 2  # withdrawal + fee

    # Find the deposit events
    deposit_events = [m for m in movements if m.event_type == HistoryEventType.DEPOSIT]
    assert len(deposit_events) == 1  # deposit only (no fee for bank transfer)

    # Check withdrawal details
    withdrawal = next(e for e in withdrawal_events if e.event_subtype != HistoryEventSubType.FEE)
    assert withdrawal.asset == A_ETH
    assert withdrawal.amount == FVal('0.5')


def test_bit2me_query_brokerage_trades(bit2me):
    """Test querying brokerage trades (purchases) from Bit2me."""

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BIT2ME_TRANSACTIONS_RESPONSE)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        trades = bit2me._query_brokerage_trades(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1800000000),
        )

    # Should have swap events for the purchase (spend EUR, receive BTC)
    assert len(trades) == 2  # spend + receive events

    # Find spend and receive events
    spend_event = next(
        (t for t in trades if t.event_subtype == HistoryEventSubType.SPEND), None,
    )
    receive_event = next(
        (t for t in trades if t.event_subtype == HistoryEventSubType.RECEIVE), None,
    )

    assert spend_event is not None
    assert receive_event is not None

    # Check spend (100 EUR)
    assert spend_event.asset == A_EUR
    assert spend_event.amount == FVal('100')

    # Check receive (0.00122130 BTC)
    assert receive_event.asset == A_BTC
    assert receive_event.amount == FVal('0.00122130')


def test_bit2me_query_history_events(bit2me):
    """Test querying all history events combines trades and movements."""

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        if 'transaction' in url:
            return MockResponse(200, BIT2ME_TRANSACTIONS_RESPONSE)
        elif 'trade' in url:
            return MockResponse(200, BIT2ME_TRADES_RESPONSE)
        return MockResponse(200, '{}')

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        events, _ = bit2me.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1800000000),
        )

    # Should have: 2 withdrawal events + 2 deposit events + 2 brokerage trade events
    # Internal transfers are skipped
    assert len(events) >= 4  # At minimum movements


def test_bit2me_internal_transfers_skipped(bit2me):
    """Test that internal transfers (pocket to pocket) are properly skipped."""
    # Response with only internal transfer
    internal_only = """{
      "total": 1,
      "data": [
        {
          "id": "internal-001",
          "date": "2025-11-15T10:00:00.000Z",
          "type": "transfer",
          "subtype": "internal",
          "method": "pocket",
          "status": "completed",
          "origin": {"amount": "50", "currency": "EUR", "class": "pocket"},
          "destination": {"amount": "50", "currency": "EUR", "class": "pocket"}
        }
      ]
    }"""

    def mock_api_return(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, internal_only)

    with patch.object(bit2me.session, 'request', side_effect=mock_api_return):
        movements = bit2me.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1800000000),
        )

    # Internal transfers should be skipped
    assert len(movements) == 0


def test_asset_from_bit2me():
    """Test asset conversion from Bit2me symbols."""
    # Standard assets
    assert asset_from_bit2me('BTC').identifier == A_BTC.identifier
    assert asset_from_bit2me('ETH').identifier == A_ETH.identifier
    assert asset_from_bit2me('EUR').identifier == A_EUR.identifier

    # Case insensitive
    assert asset_from_bit2me('btc').identifier == A_BTC.identifier
    assert asset_from_bit2me('Eth').identifier == A_ETH.identifier


def test_asset_from_bit2me_unknown():
    """Test that unknown assets raise proper exception."""
    with pytest.raises(UnknownAsset):
        asset_from_bit2me('COMPLETELY_UNKNOWN_ASSET_12345')
