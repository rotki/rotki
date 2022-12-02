from unittest.mock import MagicMock

import pytest
from flaky import flaky

from rotkehlchen.chain.ethereum.tokens import EthereumTokens
from rotkehlchen.chain.evm.tokens import generate_multicall_chunks
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_OMG
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LPT


@pytest.fixture(name='tokens')
def fixture_ethereumtokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument  # noqa: E501
    return EthereumTokens(database, ethereum_inquirer)


@flaky(max_runs=3, min_passes=1)  # failed in a flaky way sometimes in the CI due to etherscan
@pytest.mark.parametrize('ignored_assets', [[A_LPT]])
def test_detect_tokens_for_addresses(tokens):
    """
    Detect tokens, query balances and check that ignored assets are not queried.

    This is going to be a bit slow test since it actually queries etherscan without any mocks.
    By doing so we can test that the whole behavior with etherscan works fine and our
    chosen chunk length for it is also acceptable.

    USD price queries are mocked so we don't care about the result.
    Just check that all prices are included
    """
    addr1 = string_to_evm_address('0x8d89170b92b2Be2C08d57C48a7b190a2f146720f')
    addr2 = string_to_evm_address('0xB756AD52f3Bf74a7d24C67471E0887436936504C')

    tokens.evm_inquirer.multicall = MagicMock(side_effect=tokens.evm_inquirer.multicall)

    tokens.detect_tokens(False, [addr1, addr2])
    assert tokens.evm_inquirer.multicall.call_count == 0  # don't use multicall for detection
    result, token_usd_prices = tokens.query_tokens_for_addresses([addr1, addr2])
    assert tokens.evm_inquirer.multicall.call_count == 1  # do use multicall one time for balances query  # noqa: E501

    assert len(result[addr1]) == 2
    balance = result[addr1][A_OMG]
    assert isinstance(balance, FVal)
    assert balance == FVal('0.036108311660753218')
    assert len(result[addr2]) >= 1

    # test that  ignored assets are not queried
    assert A_LPT not in result[addr1] and A_LPT not in result[addr2]

    assert len(token_usd_prices) == len(set(result[addr1].keys()).union(set(result[addr2].keys())))


def test_generate_chunks():
    generated_chunks = generate_multicall_chunks(
        chunk_length=17,
        addresses_to_tokens={
            'acc1': ['token1'],
            'acc2': ['token2', 'token3', 'token4', 'token5', 'token6'],
            'acc3': ['token7', 'token8', 'token9', 'token10', 'token11', 'token12', 'token13', 'token14', 'token15', 'token16'],  # noqa: E501
        },
    )
    expected_chunks = [
        [
            ('acc1', ['token1']),
            ('acc2', ['token2', 'token3']),
        ],
        [
            ('acc2', ['token4', 'token5', 'token6']),
        ],
        [
            ('acc3', ['token7', 'token8', 'token9', 'token10', 'token11', 'token12', 'token13', 'token14', 'token15', 'token16']),  # noqa: E501
        ],
    ]
    assert generated_chunks == expected_chunks
