import datetime
from unittest.mock import MagicMock, patch

import pytest
from flaky import flaky

from rotkehlchen.chain.ethereum.tokens import EthereumTokens
from rotkehlchen.chain.evm.tokens import generate_multicall_chunks
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_OMG, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LPT
from rotkehlchen.types import ChainID
from rotkehlchen.utils.misc import ts_now


@pytest.fixture(name='tokens')
def fixture_ethereumtokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument  # noqa: E501
    return EthereumTokens(database, ethereum_inquirer)


@pytest.mark.vcr
@flaky(max_runs=3, min_passes=1)  # failed in a flaky way sometimes in the CI due to etherscan
@pytest.mark.parametrize('ignored_assets', [[A_LPT]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x8d89170b92b2Be2C08d57C48a7b190a2f146720f',
    '0xB756AD52f3Bf74a7d24C67471E0887436936504C',
    '0xc32cac63823B556E6Ebf61bB74149f08Bf1AAb34',
]])
@pytest.mark.parametrize('mocked_proxies', [{
    '0xc32cac63823B556E6Ebf61bB74149f08Bf1AAb34': '0x394C1D68498DEB24AC9F5502DD5450a0353e17dc',
}])
def test_detect_tokens_for_addresses(rotkehlchen_api_server, ethereum_accounts):
    """
    Detect tokens, query balances and check that ignored assets are not queried.

    This is going to be a bit slow test since it actually queries etherscan without any mocks.
    By doing so we can test that the whole behavior with etherscan works fine and our
    chosen chunk length for it is also acceptable.

    USD price queries are mocked so we don't care about the result.
    Just check that all prices are included
    """
    addr1, addr2, addr3 = ethereum_accounts
    addr3_proxy = string_to_evm_address('0x394C1D68498DEB24AC9F5502DD5450a0353e17dc')

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    tokens = rotki.chains_aggregator.ethereum.tokens
    tokens.evm_inquirer.multicall = MagicMock(side_effect=tokens.evm_inquirer.multicall)
    detection_result = tokens.detect_tokens(False, [addr1, addr2, addr3])
    assert A_WETH in detection_result[addr3][0], 'WETH is owned by the proxy, but should be returned in the proxy owner address'  # noqa: E501
    assert tokens.evm_inquirer.multicall.call_count == 0, 'multicall should not be used for tokens detection'  # noqa: E501
    result, token_usd_prices = tokens.query_tokens_for_addresses(
        [addr1, addr2, addr3, addr3_proxy],
    )
    assert tokens.evm_inquirer.multicall.call_count == 1, 'multicall should have been used one time for balances query'  # noqa: E501
    assert len(result[addr1]) == 2
    balance = result[addr1][A_OMG]
    assert isinstance(balance, FVal)
    assert balance == FVal('0.036108311660753218')
    assert len(result[addr2]) >= 1
    assert len(result[addr3]) >= 1
    assert len(result[addr3_proxy]) >= 1
    assert A_WETH in result[addr3_proxy], 'WETH (which is owned by the proxy) is in the result of the proxy'  # noqa: E501
    assert A_WETH not in result[addr3], 'WETH is not in the result of the proxy owner address'  # noqa: E501

    # test that  ignored assets are not queried
    assert A_LPT not in result[addr1] and A_LPT not in result[addr2]
    found_tokens = set(result[addr1].keys()).union(
        set(result[addr2].keys()),
    ).union(
        set(result[addr3].keys()),
    ).union(
        set(result[addr3_proxy].keys()),
    )
    assert len(token_usd_prices) == len(found_tokens)


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


def test_last_queried_ts(tokens, freezer):
    """
    Checks that after detecting evm tokens last_queried_timestamp is updated and there
    are no duplicates.
    """
    # We don't need to query the chain here, so mock tokens list
    evm_tokens_patch = patch(
        'rotkehlchen.globaldb.handler.GlobalDBHandler.get_evm_tokens',
        new=lambda _, chain_id=ChainID.ETHEREUM, exceptions=None, protocol=None: [],
    )
    beginning = ts_now()
    address = '0x4bBa290826C253BD854121346c370a9886d1bC26'
    with evm_tokens_patch:
        # Detect for the first time
        tokens.detect_tokens(
            only_cache=False,
            addresses=[address],
        )
        after_first_query = tokens.db.conn.execute(
            'SELECT key, value FROM evm_accounts_details',
        ).fetchall()
        assert len(after_first_query) == 1
        assert after_first_query[0][0] == 'last_queried_timestamp'
        assert int(after_first_query[0][1]) >= beginning

        continuation = beginning + 10
        freezer.move_to(datetime.datetime.fromtimestamp(continuation, tz=datetime.timezone.utc))
        # Detect again
        tokens.detect_tokens(
            only_cache=False,
            addresses=['0x4bBa290826C253BD854121346c370a9886d1bC26'],
        )
        # Check that last_queried_timestamp was updated and that there are no duplicates
        after_second_query = tokens.db.conn.execute(
            'SELECT key, value FROM evm_accounts_details',
        ).fetchall()
        assert len(after_second_query) == 1
        assert after_second_query[0][0] == 'last_queried_timestamp'
        assert int(after_second_query[0][1]) >= continuation
