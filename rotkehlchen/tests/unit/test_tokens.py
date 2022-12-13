from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from flaky import flaky

from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.evm.tokens import EvmTokens, generate_multicall_chunks
from rotkehlchen.constants.assets import A_OMG
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LPT
from rotkehlchen.utils.misc import ts_now


@pytest.fixture(name='evmtokens')
def fixture_evmtokens(ethereum_manager, database, inquirer):  # pylint: disable=unused-argument
    return EvmTokens(database, ethereum_manager)


@flaky(max_runs=3, min_passes=1)  # failed in a flaky way sometimes in the CI due to etherscan
@pytest.mark.parametrize('ignored_assets', [[A_LPT]])
def test_detect_tokens_for_addresses(evmtokens):
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

    evmtokens.manager.multicall = MagicMock(side_effect=evmtokens.manager.multicall)

    evmtokens.detect_tokens(False, [addr1, addr2])
    assert evmtokens.manager.multicall.call_count == 0  # don't use multicall for detection
    result, token_usd_prices = evmtokens.query_tokens_for_addresses([addr1, addr2])
    assert evmtokens.manager.multicall.call_count == 1  # do use multicall one time for balances query  # noqa: E501

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


def test_last_queried_ts(evmtokens, freezer):
    """
    Checks that after detecting evm tokens last_queried_timestamp is updated and there
    are no duplicates.
    """
    # We don't need to query the chain here, so mock tokens list
    evm_tokens_patch = patch(
        'rotkehlchen.globaldb.handler.GlobalDBHandler.get_ethereum_tokens',
        new=lambda _, exceptions=None, except_protocols=None, protocol=None: [],
    )
    beginning = ts_now()
    address = '0x4bBa290826C253BD854121346c370a9886d1bC26'
    with evm_tokens_patch:
        # Detect for the first time
        evmtokens.detect_tokens(
            only_cache=False,
            addresses=[address],
        )
        after_first_query = evmtokens.db.conn.execute(
            'SELECT key, value FROM accounts_details',
        ).fetchall()
        assert len(after_first_query) == 1
        assert after_first_query[0][0] == 'last_queried_timestamp'
        assert int(after_first_query[0][1]) >= beginning

        continuation = beginning + 10
        freezer.move_to(datetime.fromtimestamp(continuation))
        # Detect again
        evmtokens.detect_tokens(
            only_cache=False,
            addresses=['0x4bBa290826C253BD854121346c370a9886d1bC26'],
        )
        # Check that last_queried_timestamp was updated and that there are no duplicates
        after_second_query = evmtokens.db.conn.execute(
            'SELECT key, value FROM accounts_details',
        ).fetchall()
        assert len(after_second_query) == 1
        assert after_second_query[0][0] == 'last_queried_timestamp'
        assert int(after_second_query[0][1]) >= continuation
