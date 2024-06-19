
import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_htx
from rotkehlchen.constants.assets import A_CRV
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.htx import Htx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location


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


def test_assets_are_known(htx_exchange: Htx, globaldb):
    with patch('rotkehlchen.exchanges.htx.Htx._sign_request', return_value={}):
        tickers = htx_exchange._query('/v2/settings/common/symbols')
    for ticker in tickers:
        if ticker['te'] is False:  # skip if trade disabled
            continue
        try:
            asset_from_htx(ticker['bcdn'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in HTX. '
                f'Support for it has to be added',
            ))
        except UnsupportedAsset as e:
            if globaldb.is_asset_symbol_unsupported(Location.HTX, ticker['bcdn']) is False:
                test_warnings.warn(UserWarning(
                    f'Found unsupported asset {e.identifier} in HTX. '
                    f'Support for it has to be added',
                ))
