from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from marshmallow import ValidationError

from rotkehlchen.chain.bitcoin.bch.constants import (
    BLOCKCHAIN_INFO_HASKOIN_BASE_URL,
    HASKOIN_BASE_URL,
    MELROY_BASE_URL,
)
from rotkehlchen.chain.bitcoin.bch.utils import (
    force_address_to_legacy_address,
    force_addresses_to_legacy_addresses,
    is_valid_bitcoin_cash_address,
    legacy_to_cash_address,
    validate_bch_address_input,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.network import request_get

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.bch.manager import BitcoinCashManager
    from rotkehlchen.types import BTCAddress


def test_is_valid_bitcoin_cash_address():
    """Test that addresses follow the Bitcoin Cash CashAddr format."""
    assert is_valid_bitcoin_cash_address('bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa')
    assert is_valid_bitcoin_cash_address('qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa')
    assert is_valid_bitcoin_cash_address('bitcoincash:pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g')
    assert is_valid_bitcoin_cash_address('pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g')
    assert not is_valid_bitcoin_cash_address('BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4')
    assert not is_valid_bitcoin_cash_address('abcdefghijssfs')


def test_force_address_to_legacy_address():
    """Test that converting a btc/bch address to the legacy format works."""
    assert force_address_to_legacy_address('bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt') == '17CTr5NPYx7NcLp6w8mwZamfq7Xam8QrAe'  # noqa: E501
    assert force_address_to_legacy_address('38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr') == '38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr'  # noqa: E501


def test_force_addresses_to_legacy_addresses():
    """Test that converting btc/bch addresses to the legacy format works."""
    addresses = {
        'bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa',
        'bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt',
        '38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr',
        'pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g',
    }
    converted_addresses = {
        '1Mnwij9Zkk6HtmdNzyEUFgp6ojoLaZekP8',
        '17CTr5NPYx7NcLp6w8mwZamfq7Xam8QrAe',
        '38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr',
    }
    assert force_addresses_to_legacy_addresses(addresses) == converted_addresses


def test_legacy_to_cash_format():
    """Test that converting a legacy bch address to the CashAddr format works."""
    assert legacy_to_cash_address('38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr') == 'bitcoincash:pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g'  # noqa: E501
    assert legacy_to_cash_address('1Mnwij9Zkk6HtmdNzyEUFgp6ojoLaZekP8') == 'bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa'  # noqa: E501
    assert legacy_to_cash_address('bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa') is None
    assert legacy_to_cash_address('abcdefghijssfs') is None


def test_validate_bch_address_input():
    """Test that an address is properly validated for Bitcoin Cash."""
    empty_set = set()
    assert validate_bch_address_input('bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa', empty_set) is None  # noqa: E501
    assert validate_bch_address_input('qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa', empty_set) is None  # noqa: E501
    assert validate_bch_address_input('bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt', empty_set) is None  # noqa: E501
    assert validate_bch_address_input('qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt', empty_set) is None  # noqa: E501
    assert validate_bch_address_input('pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g', empty_set) is None  # noqa: E501
    assert validate_bch_address_input('38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr', empty_set) is None

    with pytest.raises(ValidationError) as exc_info:
        validate_bch_address_input(
            '17CTr5NPYx7NcLp6w8mwZamfq7Xam8QrAe',
            {'bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt'},
        )
    assert 'multiple times in the request data' in str(exc_info)

    with pytest.raises(ValidationError) as exc_info:
        validate_bch_address_input('ababkjk', empty_set)
    assert 'not a valid bitcoin cash address' in str(exc_info)


@pytest.mark.vcr
@pytest.mark.parametrize('bch_accounts', [['38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr']])
def test_query_bch_has_transactions_and_balances(
        bitcoin_cash_manager: 'BitcoinCashManager',
        bch_accounts: list['BTCAddress'],
) -> None:
    """Test that the bch have_transactions and get_balances work correctly from all apis."""
    user_address, expected_balance = bch_accounts[0], FVal('5.33798911')
    for api in (
        HASKOIN_BASE_URL,
        BLOCKCHAIN_INFO_HASKOIN_BASE_URL,
        MELROY_BASE_URL,
    ):

        def mock_request_get(url: str, *args, api_url=api, **kwargs):
            """Mock request_get to fail requests to apis other than the one we want to test."""
            if api_url not in url:
                raise RemoteError('Skip to next api')
            elif 'health' in url:
                return {'ok': True}

            return request_get(url, *args, **kwargs)

        with patch(
            'rotkehlchen.utils.network.request_get',
            side_effect=mock_request_get,
        ):
            assert bitcoin_cash_manager.have_transactions(
                accounts=bch_accounts,
            ) == {user_address: (True, expected_balance)}
            assert bitcoin_cash_manager.get_balances(
                accounts=bch_accounts,
            ) == {user_address: expected_balance}

        # reset health status so it tries to query health again in the next loop iteration
        bitcoin_cash_manager.last_haskoin_health = {}
