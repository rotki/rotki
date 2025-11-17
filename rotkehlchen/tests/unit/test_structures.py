from collections import defaultdict

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_EUR, A_USD
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal


def test_balance_addition():
    a = Balance(amount=FVal('1.5'), usd_value=FVal('1.6'))
    b = Balance(amount=FVal('2.5'), usd_value=FVal('2.7'))
    c = Balance(amount=FVal('3'), usd_value=FVal('3.21'))

    result = Balance(amount=FVal('7'), usd_value=FVal('7.51'))
    assert result == a + b + c
    assert a + b + c == result
    result += c
    assert result == Balance(amount=FVal('10'), usd_value=FVal('10.72'))

    with pytest.raises(InputError):
        result = a + 5

    d = {'amount': 10, 'usd_value': 11}
    e = {'amount': '5', 'usd_value': '6'}
    f = {'amount': FVal('20'), 'usd_value': FVal('22')}
    result = Balance(amount=FVal('38'), usd_value=FVal('42.21'))
    assert result == c + d + e + f
    assert c + d + e + f == result

    with pytest.raises(InputError):
        result = a + {'foo': 1}
    with pytest.raises(InputError):
        result = a + {'amount': 'fasd', 'usd_value': 1}
    with pytest.raises(InputError):
        result = a + {'amount': 1, 'usd_value': 'dsad'}


def test_balance_raddition():
    a = Balance(amount=FVal('1.5'), usd_value=FVal('1.6'))
    b = Balance(amount=FVal('2.5'), usd_value=FVal('2.7'))
    c = Balance(amount=FVal('3'), usd_value=FVal('3.21'))

    result = sum([a, b, c])

    assert isinstance(result, Balance)
    assert result.amount == FVal('7')
    assert result.usd_value == FVal('7.51')


def test_balance_sheet_addition():
    a = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_USD:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1.5'), usd_value=FVal('450'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    b = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('3.5'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('900'))}),  # noqa: E501
            A_BTC:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1'), usd_value=FVal('10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('10'), usd_value=FVal('10.2'))}),  # noqa: E501
        }),
    )
    assert a != b
    c = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('3.5'))}),  # noqa: E501
            A_USD:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('4.5'), usd_value=FVal('1350'))}),  # noqa: E501
            A_BTC:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1'), usd_value=FVal('10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('15'), usd_value=FVal('15.3'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    assert a + b == c


def test_balance_sheet_raddition():
    a = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_USD:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1.5'), usd_value=FVal('450'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    b = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('3.5'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('900'))}),  # noqa: E501
            A_BTC:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1'), usd_value=FVal('10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('10'), usd_value=FVal('10.2'))}),  # noqa: E501
        }),
    )
    c = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('3.5'))}),  # noqa: E501
            A_USD:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('4.5'), usd_value=FVal('1350'))}),  # noqa: E501
            A_BTC:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1'), usd_value=FVal('10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('15'), usd_value=FVal('15.3'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )

    result = sum([a, b])

    assert isinstance(result, BalanceSheet)
    assert result == c


def test_default_balance_sheet():
    a = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_USD:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1.5'), usd_value=FVal('450'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))}),  # noqa: E501
            A_ETH:  defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    b = BalanceSheet()  # test no args init gives empty default dicts properly
    assert isinstance(b.assets, dict)
    assert len(b.assets) == 0
    assert isinstance(b.liabilities, dict)
    assert len(b.liabilities) == 0
    assert a != b
    b += a
    assert a == b


def test_balance_sheet_subtraction():
    a = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_USD: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('900'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    b = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('3.5'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1.5'), usd_value=FVal('450'))}),  # noqa: E501
            A_BTC: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1'), usd_value=FVal('10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('10'), usd_value=FVal('10.2'))}),  # noqa: E501
        }),
    )
    assert a != b
    c = BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            A_EUR: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('-3'), usd_value=FVal('-3.5'))}),  # noqa: E501
            A_USD: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('1.5'), usd_value=FVal('450'))}),  # noqa: E501
            A_BTC: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('-1'), usd_value=FVal('-10000'))}),  # noqa: E501
        }),
        liabilities=defaultdict(lambda: defaultdict(Balance), {
            A_DAI: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('-5'), usd_value=FVal('-5.1'))}),  # noqa: E501
            A_ETH: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))}),  # noqa: E501
        }),
    )
    assert a - b == c


def test_balance_sheet_serialize():
    a = BalanceSheet(
        assets={
            A_USD: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))},
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('900'))},
        },
        liabilities={
            A_DAI: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))},
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))},
        },
    )
    assert a.serialize() == {
        'assets': {
            'USD': {DEFAULT_BALANCE_LABEL: {'amount': '2', 'usd_value': '2', 'value': '0'}},
            'ETH': {DEFAULT_BALANCE_LABEL: {'amount': '3', 'usd_value': '900', 'value': '0'}},
        },
        'liabilities': {
            ethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F'): {DEFAULT_BALANCE_LABEL: {'amount': '5', 'usd_value': '5.1', 'value': '0'}},  # noqa: E501
            'ETH': {DEFAULT_BALANCE_LABEL: {'amount': '0.5', 'usd_value': '150', 'value': '0'}},
        },
    }


def test_balance_sheet_to_dict():
    a = BalanceSheet(
        assets={
            A_USD: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('2'), usd_value=FVal('2'))},
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('3'), usd_value=FVal('900'))},
        },
        liabilities={
            A_DAI: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('5'), usd_value=FVal('5.1'))},
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=FVal('0.5'), usd_value=FVal('150'))},
        },
    )
    assert a.to_dict() == {
        'assets': {
            'USD': {DEFAULT_BALANCE_LABEL: {'amount': FVal('2'), 'usd_value': FVal('2'), 'value': ZERO}},  # noqa: E501
            'ETH': {DEFAULT_BALANCE_LABEL: {'amount': FVal('3'), 'usd_value': FVal('900'), 'value': ZERO}},  # noqa: E501
        },
        'liabilities': {
            ethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F'): {DEFAULT_BALANCE_LABEL: {'amount': FVal('5'), 'usd_value': FVal('5.1'), 'value': ZERO}},  # noqa: E501
            'ETH': {DEFAULT_BALANCE_LABEL: {'amount': FVal('0.5'), 'usd_value': FVal('150'), 'value': ZERO}},  # noqa: E501
        },
    }
