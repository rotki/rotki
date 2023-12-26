import math

import pytest

from rotkehlchen.constants import ZERO
from rotkehlchen.errors.serialization import ConversionError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.serialization import rlk_jsondumps


def test_simple_arithmetic():
    a = FVal(5.21)
    b = FVal(2.12)
    c = FVal(-23.124)
    d = FVal(5006337207657766294397)
    e = ZERO
    f = FVal('1.49298E+12')
    g = FVal('5.23267356186572e+8')
    FVal(b'0')

    assert a + b == FVal('7.33')
    assert a - b == FVal('3.09')
    assert a * b == FVal('11.0452')
    assert a / b == FVal('2.457547169811320754716981132')
    assert a ** 3 == FVal('141.420761')
    assert a.fma(b, FVal('3.14')) == FVal('14.1852')
    assert c // b == FVal('-10')
    assert -a == FVal('-5.21')
    assert abs(a) == FVal('5.21')
    assert abs(c) == FVal('23.124')
    assert d == FVal('5006337207657766294397')
    assert e == FVal('0.0')
    assert f == FVal('1492980000000')
    assert g == FVal('523267356.186572')

    a += b
    assert a == FVal('7.33')

    # For the moment not allowing operations against floats
    with pytest.raises(NotImplementedError):
        _ = a + 5.23


def test_arithmetic_with_int():
    a = FVal(5.21)

    assert a - 2 == FVal('3.21')
    assert a + 2 == FVal('7.21')
    assert a * 2 == FVal('10.42')
    assert a / 2 == FVal('2.605')
    assert a ** 3 == FVal('141.420761')
    assert a // 2 == FVal('2')

    # and now the reverse operations
    assert 2 + a == FVal('7.21')
    assert 2 - a == FVal('-3.21')
    assert 2 * a == FVal('10.42')
    assert 2 / a == FVal('0.3838771593090211132437619962')
    assert 2 // a == FVal('0')


def test_comparison():
    a = FVal('1.348938409')
    b = FVal('0.123432434')
    c = FVal('1.348938410')
    d = FVal('1.348938409')

    assert a > b
    assert a >= b
    assert b < a
    assert b <= a
    assert c > a
    assert c >= a
    assert a < c
    assert a <= c
    assert a == d
    assert a <= d
    assert a >= d


def test_int_comparison():
    a = FVal('1.348938409')
    b = 1
    c = FVal('3.0')
    d = FVal('3')
    e = 3

    assert a > b
    assert a >= b
    assert b < a
    assert b <= a

    assert c >= d
    assert c <= d
    assert d <= c
    assert d >= c
    assert d == c

    assert c >= e
    assert c <= e
    assert e <= c
    assert e >= c
    assert e == c


def test_representation():
    a = FVal(2.01)
    b = FVal('2.01')
    assert a == b

    a = FVal(2.00)
    b = FVal('2.0')
    c = FVal(2)
    assert a == b
    assert b == c


def test_encoding():
    data = {'a': math.pi, 'b': 5, 'c': 'foo', 'd': '5.42323143', 'e': {'u1': '3.221'},
            'f': [2.1, 'boo', 3, '4.2324']}
    strdata = rlk_jsondumps(data)
    # stupid test, as it will fail if different python version is used. Should just
    # have used decoding again to make sure they are the same but was lazy
    assert strdata == (
        '{"a": 3.141592653589793, "b": 5, "c": "foo", "d": "5.42323143", '
        '"e": {"u1": "3.221"}, "f": [2.1, "boo", 3, "4.2324"]}'
    )


def test_conversion():
    a = 2.0123
    b = FVal('2.0123')
    c = float(b)
    d = FVal('3.0')
    assert a == c
    assert d.to_int(exact=True) == 3
    with pytest.raises(ConversionError):
        b.to_int(exact=True)


def test_to_percentage():
    assert FVal('0.5').to_percentage() == '50.0000%'
    assert FVal('0.5').to_percentage(with_perc_sign=False) == '50.0000'
    assert FVal('0.2345').to_percentage() == '23.4500%'
    assert FVal('0.2345').to_percentage(precision=2) == '23.45%'
    assert FVal('0.2345').to_percentage(precision=0) == '23%'
    assert FVal('0.5324').to_percentage(precision=1, with_perc_sign=False) == '53.2'
    assert FVal('0.2345').to_percentage(precision=0, with_perc_sign=False) == '23'
    assert FVal('1.5321').to_percentage() == '153.2100%'


def test_initialize_with_bool_fails():
    """
    Test that initializing with a bool fails

    Essentially due to the following:
    https://stackoverflow.com/questions/37888620/comparing-boolean-and-int-using-isinstance

    I realized isinstance(True, int) == True which lead to fval being also initializable
    with booleans. This test is here to make sure this does not happen anymore
    """

    with pytest.raises(ValueError):
        FVal(True)
    with pytest.raises(ValueError):
        FVal(False)
