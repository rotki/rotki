
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_CRV
from rotkehlchen.exchanges.htx import Htx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse


def test_accounts(htx_exchange: Htx):
    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, """{"status": "ok", "data": [{"id": 50, "type": "spot", "subtype": "", "state": "working"}, {"id": 292, "type": "point", "subtype": "", "state": "working"}]}""")  # noqa: E501

    with patch.object(htx_exchange.session, 'get', side_effect=mock_api_return):
        accounts = htx_exchange.get_accounts()

    assert {account['type'] for account in accounts} == {'spot', 'point'}


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_balances(htx_exchange: Htx):
    balance_response = """
    {
        "status": "ok",
        "data": {"id": 50, "type": "spot", "state": "working", "list": [
            {"currency": "atom", "type": "trade", "balance": "1.100000007177861711", "available": "1.100000007177861711", "debt": "0", "seq-num": "11"},
            {"currency": "ksm", "type": "frozen", "balance": "0", "debt": "0", "seq-num": "0"},
            {"currency": "crv", "type": "trade", "balance": "0.100000007177861711", "available": "0.100000007177861711", "debt": "0", "seq-num": "0"}
        ]}
    }"""  # noqa: E501

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        if 'balance' in url:
            return MockResponse(200, balance_response)
        else:
            return MockResponse(200, """{"status": "ok", "data": [{"id": 50, "type": "spot", "subtype": "", "state": "working"}]}""")  # noqa: E501

    with patch.object(htx_exchange.session, 'get', side_effect=mock_api_return):
        balances, _ = htx_exchange.query_balances()

    assert balances == {
        Asset('ATOM'): Balance(amount=FVal('1.100000007177861711'), usd_value=FVal('1.6500000107667925665')),  # noqa: E501
        A_CRV: Balance(amount=FVal('0.100000007177861711'), usd_value=FVal('0.1500000107667925665')),  # noqa: E501
    }
