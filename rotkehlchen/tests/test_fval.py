import pytest
from rotkehlchen.fval import FVal
from rotkehlchen.utils import rlk_jsonloads, rlk_jsondumps


def test_simple_arithmetic():
    a = FVal(5.21)
    b = FVal(2.12)
    c = FVal(-23.124)
    d = FVal(5006337207657766294397)
    e = FVal(0)
    FVal(b'0')

    assert a + b == FVal('7.33')
    assert a - b == FVal('3.09')
    assert a * b == FVal('11.0452')
    assert a / b == FVal('2.457547169811320754716981132')
    assert a ** 3 == FVal('141.420761')
    assert a.fma(b, FVal(3.14)) == FVal('14.1852')
    assert -a == FVal('-5.21')
    assert abs(a) == FVal('5.21')
    assert abs(c) == FVal('23.124')
    assert d == FVal('5006337207657766294397')
    assert e == FVal('0.0')

    a += b
    assert a == FVal('7.33')

    # For the moment not allowing operations against floats
    with pytest.raises(NotImplementedError):
        a + 5.23


def test_arithmetic_with_int():
    a = FVal(5.21)

    assert a - 2 == FVal('3.21')
    assert a + 2 == FVal('7.21')
    assert a * 2 == FVal('10.42')
    assert a / 2 == FVal('2.605')
    assert a ** 3 == FVal('141.420761')

    # and now the reverse operations
    assert 2 + a == FVal('7.21')
    assert 2 - a == FVal('-3.21')
    assert 2 * a == FVal('10.42')
    assert 2 / a == FVal('0.3838771593090211132437619962')


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
    data = {'a': 3.14, 'b': 5, 'c': 'foo', 'd': '5.42323143', 'e': {'u1': '3.221'},
            'f': [2.1, 'boo', 3, '4.2324']}
    strdata = rlk_jsondumps(data)
    # stupid test, as it will fail if different python version is used. Should just
    # have used decoding again to make sure they are the same but was lazy
    assert strdata == '{"a": 3.14, "b": 5, "c": "foo", "d": "5.42323143", "e": {"u1": "3.221"}, "f": [2.1, "boo", 3, "4.2324"]}'


def test_decoding():
    strdata = """
    {"a": 3.14, "b":5, "c": "foo", "d": "5.42323143", "e": { "u1": "3.221"}, "f": [2.1, "boo", 3, "4.2324"]}"""

    data = rlk_jsonloads(strdata)
    assert isinstance(data['a'], FVal)
    assert data['a'] == FVal('3.14')
    assert isinstance(data['b'], int)
    assert data['b'] == 5
    assert isinstance(data['c'], (str, bytes))
    assert data['c'] == 'foo'
    assert isinstance(data['d'], FVal)
    assert data['d'] == FVal('5.42323143')

    assert isinstance(data['e']['u1'], FVal)
    assert data['e']['u1'] == FVal('3.221')

    assert isinstance(data['f'][0], FVal)
    assert data['f'][0] == FVal('2.1')
    assert isinstance(data['f'][1], (str, bytes))
    assert data['f'][1] == "boo"
    assert isinstance(data['f'][2], int)
    assert data['f'][2] == 3
    assert isinstance(data['f'][3], FVal)
    assert data['f'][3] == FVal('4.2324')


def test_conversion():
    a = 2.0123
    b = FVal('2.0123')
    c = float(b)
    assert a == c
