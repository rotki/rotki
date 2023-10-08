import datetime
from unittest.mock import MagicMock, patch

import gevent
import pytest

from rotkehlchen.assets.utils import _query_or_get_given_token_info
from rotkehlchen.chain.ethereum.tokens import EthereumTokens
from rotkehlchen.chain.evm.tokens import generate_multicall_chunks
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_OMG, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LPT
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, EvmTokenKind, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

ERC20_INFO_RESPONSE = ((True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04USDT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\nTether USD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))  # noqa: E501
ERC721_INFO_RESPONSE = ((True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06BLOCKS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\nArt Blocks\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))  # noqa: E501


@pytest.fixture(name='tokens')
def fixture_ethereumtokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument
    return EthereumTokens(database, ethereum_inquirer)


# TODO: This needs VCR, but I removed it due to inability to make it work.
# Recording a cassette works. But rerunning it with the cassete seems to fail when
# trying to replay the 2nd request, saying it differs.
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
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.freeze_time('2023-02-18 22:31:11 GMT')
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
    assert tokens.evm_inquirer.multicall.call_count >= 1, 'multicall should have been used for balances query'  # noqa: E501
    assert len(result[addr1]) >= 1
    balance = result[addr1][A_OMG]
    assert isinstance(balance, FVal)
    assert balance == FVal('0.036108311660753218')
    assert len(result[addr2]) >= 1
    assert len(result[addr3]) >= 1
    assert len(result[addr3_proxy]) >= 1
    assert A_WETH in result[addr3_proxy], 'WETH (which is owned by the proxy) is in the result of the proxy'  # noqa: E501
    assert A_WETH not in result[addr3], 'WETH is not in the result of the proxy owner address'

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


def test_cache_is_per_token_type(ethereum_inquirer):
    """This test makes sure that different info cache is used per token type."""
    address = make_evm_address()

    def query_token_info(token_kind):
        """
        Util function to request token info. Doesn't pass name, symbol or decimals because they
        should be retrieved from the chain (chain calls are mocked below).
        """
        return _query_or_get_given_token_info(
            evm_inquirer=ethereum_inquirer,
            evm_address=address,
            name=None,
            symbol=None,
            decimals=None,
            token_kind=token_kind,
        )

    def patch_multicall_2(return_value):
        """
        This patch method together with ERC20_INFO_RESPONSE and ERC721_INFO_RESPONSE mocks
        tokens info.
        """
        return patch.object(
            ethereum_inquirer,
            'multicall_2',
            return_value=return_value,
        )

    with patch_multicall_2(ERC20_INFO_RESPONSE):
        erc20_token_data = query_token_info(EvmTokenKind.ERC20)

    with patch_multicall_2(ERC721_INFO_RESPONSE):
        erc721_token_data = query_token_info(EvmTokenKind.ERC721)

    with patch.object(  # disable chain calls
        ethereum_inquirer,
        'multicall_2',
        new=MagicMock(side_effect=AssertionError('Chain calls should not be made')),
    ):
        erc20_cached_data = query_token_info(EvmTokenKind.ERC20)
        erc721_cached_data = query_token_info(EvmTokenKind.ERC721)

    assert erc20_token_data == erc20_cached_data == ('Tether USD', 'USDT', 6)
    assert erc721_token_data == erc721_cached_data == ('Art Blocks', 'BLOCKS', 0)


def _do_read(database):
    with database.conn.read_ctx() as cursor:
        database.get_settings(cursor)
        database.get_all_external_service_credentials()
        database.get_blockchain_accounts(cursor)


def _do_spawn(database):
    while True:
        gevent.spawn(_do_read, database)
        with database.user_write() as write_cursor:
            database.set_setting(write_cursor, 'last_write_ts', 15)
            gevent.sleep(0.1)
            database.set_setting(write_cursor, 'last_write_ts', 15)


@pytest.mark.parametrize('number_of_eth_accounts', [100])
@pytest.mark.parametrize('sql_vm_instructions_cb', [10])
def test_flaky_binding_parameter_zero(database, ethereum_accounts):
    """Test that reproduces https://github.com/rotki/rotki/issues/5432 reliably.

    Seems to be an sqlite driver implementation error that causes a wrong instance of
    "Error binding parameter 0 - probably unsupported type" flakily. Happened once
    in a blue moon for our users so was hard to reproduce.

    Happens only if opening a parallel write context in the same connection from which
    the read only get_tokens_for_address is done. Makes no sense. As a read context
    should not be affected. Our current fix in the code is to repeat the cursor.execute()
    without any delay. It works splendid. Same solution the coveragepy people used:
    https://github.com/nedbat/coveragepy/issues/1010
    """
    stuff = []
    # Populate some data in the evm_accounts_details table, since this is what's used in the bug
    for idx, address in enumerate(ethereum_accounts):
        if idx % 2 == 0:
            stuff.append((address, 1, 'last_queried_timestamp', 42))
        else:
            stuff.append((address, 1, 'tokens', 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'))  # noqa: E501
            stuff.append((address, 1, 'tokens', 'eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96'))  # noqa: E501

    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO evm_accounts_details '
            '(account, chain_id, key, value) VALUES (?, ?, ?, ?)',
            stuff,
        )

    # Create the conditions for the bug to hit. Can verify by removing the retry in dbhandler.py
    gevent.spawn(_do_spawn, database)
    gevent.sleep(.1)
    with database.conn.read_ctx() as cursor:
        for address in ethereum_accounts:
            database.get_tokens_for_address(cursor, address, SupportedBlockchain.ETHEREUM)
