from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from requests.models import Response

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.tests.fixtures.messages import MockedWsMessage
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def mock_unauthorized_requests_get(url, params=None, **kwargs):
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    response._content = b'{"message": "No authorization token was found"}'
    return response


def test_gnosis_pay_skip_refund(database: 'DBHandler', gnosispay_credentials: None) -> None:
    """Test that gnosis pay skips refunds without error, since they are missing data linking
    them to onchain transactions.
    """
    gnosispay = init_gnosis_pay(database)
    assert gnosispay is not None

    def mocked_api(url, *args, **kwargs):
        if kwargs['params']['offset'] == 0:
            return MockResponse(200, """{"results": [{
                "createdAt": "XX",
                "clearedAt": "XX",
                "isPending": false,
                "transactionAmount": "2300",
                "transactionCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "billingAmount": "2300",
                "billingCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "transactionType": "20",
                "mcc": "5661",
                "merchant": {
                    "name": "I-RUN",
                    "city": "CASTELNAU D E",
                    "country": {"name": "France", "numeric": "250", "alpha2": "FR", "alpha3": "FRA"}
                },
                "country": {"name": "France", "numeric": "250", "alpha2": "FR", "alpha3": "FRA"},
                "transactions": [],
                "kind": "Refund",
                "refundCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "refundAmount": "2300"
            }]}""")  # noqa: E501
        else:
            return MockResponse(200, """{"results": []}""")

    with (
        patch.object(gnosispay.session, 'get', mocked_api),
        patch.object(gnosispay, 'write_txdata_to_db') as mock_write_txdata_to_db,
    ):
        gnosispay.get_and_process_transactions(after_ts=Timestamp(0))

    assert mock_write_txdata_to_db.call_count == 0


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_gnosis_pay_unauthorized(database, gnosispay_credentials):
    """Test that gnosis pay sends the session expired message"""
    gnosispay = init_gnosis_pay(database)

    # Patch to avoid requests in the Gnosis pay api
    with patch.object(
        target=gnosispay.session,
        attribute='get',
        side_effect=mock_unauthorized_requests_get,
    ):
        gnosispay.get_data_for_transaction(tx_hash='', tx_timestamp=0)

    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.GNOSISPAY_SESSIONKEY_EXPIRED,
        data={'error': 'No authorization token was found'},
    )
