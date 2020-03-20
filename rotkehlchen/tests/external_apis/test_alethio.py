from unittest.mock import patch

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.alethio import ALETHIO_TOKEN_BALANCES
from rotkehlchen.tests.utils.mock import MockResponse


def patch_alethio(alethio):
    def mock_response(url, *args):  # pylint: disable=unused-argument
        if 'tokenBalances' in url:
            if '0x9531C059098e3d194fF87FebB587aB07B30B1306' in url:
                data = ALETHIO_TOKEN_BALANCES
            else:
                raise AssertionError(
                    'Unexpected Alethio tokenBalance call during mocking in tests',
                )
        else:
            raise AssertionError('Unexpected Alethio call during mocking in tests')
        return MockResponse(200, data)

    alethio_patch = patch.object(alethio.session, 'get', side_effect=mock_response)
    return alethio_patch


def test_get_token_balances(alethio):
    alethio_patch = patch_alethio(alethio)
    with alethio_patch:
        balances = alethio.get_token_balances('0x9531C059098e3d194fF87FebB587aB07B30B1306')

    assert len(balances) == 3
    assert balances['DAI'] == FVal('5.7')
    assert balances['SAI'] == FVal('0')
    assert balances['USDC'] == FVal('20')
