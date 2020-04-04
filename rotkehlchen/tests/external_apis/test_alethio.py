from unittest.mock import patch

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.alethio import (
    ALETHIO_MULTIPAGE_TOKEN_BALANCES1,
    ALETHIO_MULTIPAGE_TOKEN_BALANCES2,
    ALETHIO_MULTIPAGE_TOKEN_BALANCES3,
    ALETHIO_SIMPLE_TOKEN_BALANCES,
)
from rotkehlchen.tests.utils.mock import MockResponse


def patch_alethio(alethio):
    def mock_response(url, *args):  # pylint: disable=unused-argument
        if 'tokenBalances' in url:
            if '0x9531C059098e3d194fF87FebB587aB07B30B1306' in url:
                data = ALETHIO_SIMPLE_TOKEN_BALANCES
            elif '0xa57Bd00134B2850B2a1c55860c9e9ea100fDd6CF' in url:
                data = ALETHIO_MULTIPAGE_TOKEN_BALANCES1
            else:
                raise AssertionError(
                    'Unexpected Alethio tokenBalance call during mocking in tests',
                )
        elif 'token-balances?filter' in url:
            if 'f432555e5c898f83fc5f00df631bd9c2801fea289' in url:
                data = ALETHIO_MULTIPAGE_TOKEN_BALANCES2
            elif 'fac9bb427953ac7fddc562adca86cf42d988047fd' in url:
                data = ALETHIO_MULTIPAGE_TOKEN_BALANCES3
            else:
                raise AssertionError(
                    'Unexpected Alethio tokenBalance call during mocking in tests',
                )
        else:
            raise AssertionError('Unexpected Alethio call during mocking in tests')
        return MockResponse(200, data)

    alethio_patch = patch.object(alethio.session, 'get', side_effect=mock_response)
    return alethio_patch


def test_get_simple_token_balances(alethio):
    """Test that getting token balances of an account works with alethio for single page"""
    alethio_patch = patch_alethio(alethio)
    with alethio_patch:
        balances = alethio.get_token_balances('0x9531C059098e3d194fF87FebB587aB07B30B1306')

    assert len(balances) == 3
    assert balances['DAI'] == FVal('5.7')
    assert balances['SAI'] == ZERO
    assert balances['USDC'] == FVal('20')


def test_get_multipage_token_balances(alethio):
    """Test that getting token balances of an account works with alethio for multiple pages"""
    alethio_patch = patch_alethio(alethio)
    with alethio_patch:
        balances = alethio.get_token_balances('0xa57Bd00134B2850B2a1c55860c9e9ea100fDd6CF')

    assert len(balances) == 13
    expected_balances = {
        'TUSD': ZERO,
        'PKG': FVal('100'),
        'BAT': ZERO,
        'REP': ZERO,
        'WBTC': ZERO,
        'AMB': FVal('0.1'),
        'LINK': ZERO,
        'DAI': FVal('106029.46635018318'),
        'SAI': FVal('24.974762270881137'),
        'USDC': FVal('1000'),
        'WETH': FVal('1139.6876129573913'),
        'KNC': ZERO,
        'ZRX': ZERO,
    }
    assert balances == expected_balances
