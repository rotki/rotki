import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.errors import InputError
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
