from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from marshmallow import ValidationError

from rotkehlchen.chain.bitcoin.bch.constants import (
    BCH_GROUP_IDENTIFIER_PREFIX,
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
from rotkehlchen.constants.assets import A_BCH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.bitcoin_event import BitcoinEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import BTCAddress, BTCTxId, Location, TimestampMS
from rotkehlchen.utils.network import request_get

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.bch.manager import BitcoinCashManager
    from rotkehlchen.inquirer import Inquirer


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


@pytest.mark.parametrize('bch_accounts', [[
    '38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr',  # legacy, converted to cashaddr
    'qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa',  # cashaddr without the prefix
    'bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt',  # already in the api format
]])
def test_bch_tracked_accounts_use_the_api_format(
        bitcoin_cash_manager: BitcoinCashManager,
        bch_accounts: list[BTCAddress],
) -> None:
    """Test that the tracked accounts are kept in the CashAddr format the apis return, while
    both the display format the events use and the reverse mapping back to the api format
    still resolve to the address the user added.
    """
    bitcoin_cash_manager.refresh_tracked_accounts()
    assert set(bitcoin_cash_manager.tracked_accounts) == (expected := {
        'bitcoincash:pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g',
        'bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa',
        'bitcoincash:qpplh0vyfn67cupcmhq4g2dt3s50rlarmclu9vnndt',
    })
    assert bitcoin_cash_manager.tracked_accounts_set == expected
    for account in bch_accounts:  # the roundtrip gets back to what the user added
        assert bitcoin_cash_manager.get_display_address(
            bitcoin_cash_manager.get_api_address(account),
        ) == account

    # and an untracked address is left as it is instead of resolving to something else
    assert bitcoin_cash_manager.get_api_address(
        untracked := BTCAddress('1Mnwij9Zkk6HtmdNzyEUFgp6ojoLaZekP8'),
    ) == untracked


@pytest.mark.vcr
@pytest.mark.parametrize('bch_accounts', [['38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr']])
def test_query_bch_has_transactions_and_balances(
        bitcoin_cash_manager: BitcoinCashManager,
        bch_accounts: list[BTCAddress],
        inquirer: Inquirer,
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
            assert bitcoin_cash_manager.query_balances(
                addresses=bch_accounts,
            )[user_address].amount == expected_balance

        # reset health status so it tries to query health again in the next loop iteration
        bitcoin_cash_manager.last_haskoin_health = {}


@pytest.mark.parametrize('bch_accounts', [['bitcoincash:qz6v8t9ajq79rrlnckv34am9cgp3dyuhrcj3npwtyh']])  # noqa: E501
def test_deserialize_haskoin_real_coinbase_tx(
        bitcoin_cash_manager: BitcoinCashManager,
        bch_accounts: list[BTCAddress],
) -> None:
    """A real haskoin coinbase transaction (block 971877 of BCH) reports the coinbase input
    as {"coinbase": true, "pkscript": null, "value": null, "address": null, ...}. It used to
    raise a DeserializationError on its value and the whole transaction was skipped. It must
    deserialize as a zero-valued placeholder input without an address, so decoding produces
    the mining reward for the tracked address.
    """
    haskoin_raw_tx = {
        'txid': '08941f78ae955ec536de0db409e5a1cfef980e26d0c6a62c7245e195af72fde3',
        'size': 130,
        'version': 1,
        'locktime': 0,
        'fee': 0,
        'time': 1791383974,
        'deleted': False,
        'rbf': False,
        'weight': 520,
        'block': {'height': 971877, 'position': 0},
        'inputs': [{
            'coinbase': True,
            'txid': '0000000000000000000000000000000000000000000000000000000000000000',
            'output': 4294967295,
            'sigscript': '0365d40e1c4d696e656420627920416e74506f6f6c383036cf00610320e88c0eca0000e4ce028d490100000000',  # noqa: E501
            'sequence': 4294967295,
            'pkscript': None,
            'value': None,
            'address': None,
            'witness': [],
        }],
        'outputs': [{
            'address': 'bitcoincash:qz6v8t9ajq79rrlnckv34am9cgp3dyuhrcj3npwtyh',
            'value': 314805138,
            'pkscript': '76a914b4c3acbd903c518ff3c5991af765c2031693971e88ac',
            'spent': False,
        }],
    }
    tx = bitcoin_cash_manager.deserialize_tx_from_haskoin(haskoin_raw_tx)
    assert tx.is_coinbase is True
    assert len(tx.inputs) == 1
    assert tx.inputs[0].value == ZERO
    assert tx.inputs[0].address is None

    bitcoin_cash_manager.refresh_tracked_accounts()
    assert bitcoin_cash_manager.decode_transaction(tx) == [BitcoinEvent(
        tx_ref=BTCTxId('08941f78ae955ec536de0db409e5a1cfef980e26d0c6a62c7245e195af72fde3'),
        group_identifier=f'{BCH_GROUP_IDENTIFIER_PREFIX}08941f78ae955ec536de0db409e5a1cfef980e26d0c6a62c7245e195af72fde3',
        sequence_index=0,
        timestamp=TimestampMS(1791383974000),
        location=Location.BITCOIN_CASH,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_BCH,
        amount=FVal('3.14805138'),
        location_label=bch_accounts[0],
        notes='Receive 3.14805138 BCH as a mining reward',
    )]
