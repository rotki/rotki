import pytest
from marshmallow import ValidationError

from rotkehlchen.chain.bitcoin.bch.utils import (
    force_address_to_legacy_address,
    force_addresses_to_legacy_addresses,
    is_valid_bitcoin_cash_address,
    validate_bch_address_input,
)


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
