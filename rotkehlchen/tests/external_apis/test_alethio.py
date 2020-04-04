from unittest.mock import patch

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
            elif url == 'https://api.aleth.io/v1/accounts/0xa57Bd00134B2850B2a1c55860c9e9ea100fDd6CF/tokenBalances':  # noqa: E501
                data = ALETHIO_MULTIPAGE_TOKEN_BALANCES1
            elif 'f432555e5c898f83fc5f00df631bd9c2801fea289' in url:
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
    assert balances['SAI'] == FVal('0')
    assert balances['USDC'] == FVal('20')


def test_get_multipage_token_balances(alethio):
    """Test that getting token balances of an account works with alethio for multiple pages"""
    alethio_patch = patch_alethio(alethio)
    with alethio_patch:
        balances = alethio.get_token_balances('0xa57Bd00134B2850B2a1c55860c9e9ea100fDd6CF')

    assert len(balances) == 22
    assert balances['DAI'] == FVal('5.7')
    assert balances['SAI'] == FVal('0')
    assert balances['USDC'] == FVal('20')
