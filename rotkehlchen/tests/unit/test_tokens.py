import datetime
from contextlib import suppress
from typing import TYPE_CHECKING, Any, get_args
from unittest.mock import MagicMock, patch

import gevent
import pytest

from rotkehlchen.assets.utils import _query_or_get_given_token_info, get_or_create_evm_token
from rotkehlchen.chain.ethereum.tokens import EthereumTokens
from rotkehlchen.chain.evm.tokens import generate_multicall_chunks
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_OMG, A_WETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.constants import EVM_ACCOUNTS_DETAILS_TOKENS
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.constants import A_GNOSIS_EURE, A_LPT
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Location,
    SupportedBlockchain,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.manager import GnosisManager
    from rotkehlchen.db.dbhandler import DBHandler


ERC20_INFO_RESPONSE = ((True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04USDT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\nTether USD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))  # noqa: E501
ERC721_INFO_RESPONSE = ((True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06BLOCKS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'), (True, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\nArt Blocks\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))  # noqa: E501


@pytest.fixture(name='tokens')
def fixture_ethereumtokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument
    return EthereumTokens(database, ethereum_inquirer)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
    with patch(
        'rotkehlchen.globaldb.handler.GlobalDBHandler.get_token_detection_data',
        side_effect=lambda *args, **kwargs: ([  # mock the returned list to avoid changing this test with every assets version  # noqa: E501
            EvmTokenDetectionData(
                identifier=A_WETH.identifier,
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                decimals=18,
            ), EvmTokenDetectionData(
                identifier=A_LPT.identifier,
                address=string_to_evm_address('0x58b6A8A3302369DAEc383334672404Ee733aB239'),
                decimals=18,
            ), EvmTokenDetectionData(
                identifier=A_OMG.identifier,
                address=string_to_evm_address('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'),
                decimals=18,
            ), EvmTokenDetectionData(
                identifier=A_DAI.identifier,
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                decimals=18,
            ),
        ], []),
    ):
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
    Note: It is hard to VCR because https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=70915550
    """
    # We don't need to query the chain here, so mock tokens list
    evm_tokens_patch = patch(
        'rotkehlchen.globaldb.handler.GlobalDBHandler.get_token_detection_data',
        new=lambda chain_id=ChainID.ETHEREUM, exceptions=None, protocol=None: ([], []),
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
        freezer.move_to(datetime.datetime.fromtimestamp(continuation, tz=datetime.UTC))
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
def test_flaky_binding_parameter_zero(
        database: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
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
    stuff: list[tuple[Any, ...]] = []
    # Populate some data in the evm_accounts_details table, since this is what's used in the bug
    for idx, address in enumerate(ethereum_accounts):
        if idx % 2 == 0:
            stuff.append((address, 1, 'last_queried_timestamp', 42))
        else:
            stuff.extend((
                (address, 1, 'tokens', 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),  # noqa: E501
                (address, 1, 'tokens', 'eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96'),  # noqa: E501
            ))

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
            database.get_tokens_for_address(
                cursor=cursor,
                address=address,
                blockchain=SupportedBlockchain.ETHEREUM,
                token_exceptions=set(),
            )


@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_old_curve_gauge(ethereum_inquirer: 'EthereumInquirer'):
    """Test that querying new and old gauges get the data correctly.
    Old one should pick the default values provided and the new one should
    get the values from the chain
    """
    # old gauge
    gauge_address = string_to_evm_address('0xC2b1DF84112619D190193E48148000e3990Bf627')
    with suppress(InputError):
        GlobalDBHandler.delete_asset_by_identifier(evm_address_to_identifier(
            address=gauge_address,
            chain_id=ChainID.ETHEREUM,
        ))

    gauge_token = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=gauge_address,
        chain_id=ethereum_inquirer.chain_id,
        evm_inquirer=ethereum_inquirer,
        decimals=18,
        name='USDK Gauge Deposit',
        symbol='USDK curve-gauge',
    )
    assert gauge_token.name == 'USDK Gauge Deposit'
    assert gauge_token.symbol == 'USDK curve-gauge'
    assert gauge_token.decimals == 18

    # new gauge
    gauge_address = string_to_evm_address('0x182B723a58739a9c974cFDB385ceaDb237453c28')
    with suppress(InputError):
        GlobalDBHandler.delete_asset_by_identifier(evm_address_to_identifier(
            address=gauge_address,
            chain_id=ChainID.ETHEREUM,
        ))

    gauge_token = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=gauge_address,
        chain_id=ethereum_inquirer.chain_id,
        evm_inquirer=ethereum_inquirer,
        fallback_decimals=18,
        fallback_name='stETH Gauge Deposit',
        fallback_symbol='stETH curve-gauge',
    )
    assert gauge_token.name == 'Curve.fi steCRV Gauge Deposit'
    assert gauge_token.symbol == 'steCRV-gauge'
    assert gauge_token.decimals == 18


@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_chain_is_not_queried_when_details(ethereum_inquirer: 'EthereumInquirer'):
    """Test that if we provide the values of name, decimals and symbol we don't query
    the chain without need
    """
    lido_address = string_to_evm_address('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32')
    with suppress(InputError):
        GlobalDBHandler.delete_asset_by_identifier(evm_address_to_identifier(
            address=lido_address,
            chain_id=ChainID.ETHEREUM,
        ))

    with patch(
        'rotkehlchen.assets.utils._query_or_get_given_token_info',
        side_effect=_query_or_get_given_token_info,
    ) as patched_query:
        new_token = get_or_create_evm_token(
            userdb=ethereum_inquirer.database,
            evm_address=lido_address,
            chain_id=ethereum_inquirer.chain_id,
            evm_inquirer=ethereum_inquirer,
            decimals=17,
            name='new LDO',
            symbol='nLDO',
        )
        assert patched_query.call_count == 0

    assert new_token.name == 'new LDO'
    assert new_token.symbol == 'nLDO'
    assert new_token.decimals == 17


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x7bF5421a72E9bcDA25A706450af95D5645C9d33f']])
def test_monerium_queries(
        gnosis_manager: 'GnosisManager',
        gnosis_accounts: list[ChecksumEvmAddress],
        inquirer: Inquirer,
):
    """Test that we query balances for the new monerium eure but not the old one"""
    new_eure = get_or_create_evm_token(  # ensure that the new eure is in the db
        userdb=gnosis_manager.node_inquirer.database,
        evm_address=string_to_evm_address('0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
        chain_id=(chain_id := gnosis_manager.node_inquirer.chain_id),
        evm_inquirer=gnosis_manager.node_inquirer,
    )
    with patch(
        'rotkehlchen.globaldb.handler.GlobalDBHandler.get_token_detection_data',
        new=lambda *args, **kwargs: ([
            EvmTokenDetectionData(
                identifier=new_eure.identifier,
                address=new_eure.evm_address,
                decimals=new_eure.decimals,  # type: ignore
            ), EvmTokenDetectionData(
                identifier=A_GNOSIS_EURE.identifier,
                address=string_to_evm_address('0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
                decimals=18,
            ),
        ], []),
    ):
        tokens = gnosis_manager.tokens.detect_tokens(
            only_cache=False,
            addresses=gnosis_accounts,
        )[gnosis_accounts[0]][0]
        assert new_eure in tokens  # type: ignore

    # insert the old eure and see that is not queried
    with gnosis_manager.node_inquirer.database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO evm_accounts_details '
            '(account, chain_id, key, value) VALUES (?, ?, ?, ?)',
            (
                gnosis_accounts[0],
                chain_id.serialize_for_db(),
                EVM_ACCOUNTS_DETAILS_TOKENS,
                A_GNOSIS_EURE.identifier,
            ),
        )

    tokens_second_query = gnosis_manager.tokens.query_tokens_for_addresses(
        addresses=gnosis_accounts,
    )[0][gnosis_accounts[0]]
    assert new_eure in tokens_second_query
    assert A_GNOSIS_EURE not in tokens_second_query


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbe4f0cdf3834bD876813A1037137DcFAD79AcD99']])
def test_erc721_token_ownership_verification(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        database: 'DBHandler',
):
    """Test that when a user has historical events for two NFTs from the same collection
    but only currently owns one, we correctly identify only the currently owned NFT.
    """
    token_7776 = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_inquirer=ethereum_inquirer,
        evm_address=(collection_address := string_to_evm_address('0xD3D9ddd0CF0A5F0BFB8f7fcEAe075DF687eAEBaB')),  # noqa: E501
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        collectible_id='7776',
    )
    token_7809 = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_inquirer=ethereum_inquirer,
        evm_address=collection_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        collectible_id='7809',
    )

    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                event_identifier='xxx',
                sequence_index=0,
                timestamp=TimestampMS(1645260370000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location_label=(user_address := ethereum_accounts[0]),
                amount=ONE,
                asset=token_7776,
            ), HistoryEvent(
                event_identifier='xxy',
                sequence_index=0,
                timestamp=TimestampMS(1645260470000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                amount=ONE,
                location_label=user_address,
                asset=token_7776,
            ), HistoryEvent(
                event_identifier='xyx',
                sequence_index=0,
                timestamp=TimestampMS(1645260570000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=ONE,
                location_label=user_address,
                asset=token_7776,
            ), HistoryEvent(
                event_identifier='yxx',
                sequence_index=0,
                timestamp=TimestampMS(1645260670000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=ONE,
                location_label=user_address,
                asset=token_7809,
            ), HistoryEvent(
                event_identifier='yyx',
                sequence_index=0,
                timestamp=TimestampMS(1645260770000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                amount=ONE,
                location_label=user_address,
                asset=token_7809,
            ), HistoryEvent(
                event_identifier='yyy',
                sequence_index=0,
                timestamp=TimestampMS(1645260870000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=ONE,
                location_label=user_address,
                asset=token_7809,
            )],
        )

    # regression test: dai token added here to ensure detected erc20 tokens
    # aren't removed when erc721 tokens are detected
    # see https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=112828923
    with patch('rotkehlchen.chain.ethereum.tokens.EthereumTokens._detect_tokens', return_value={ethereum_accounts[0]: [A_DAI]}):  # noqa: E501
        user_tokens = EthereumTokens(database, ethereum_inquirer).detect_tokens(
            only_cache=False,
            addresses=ethereum_accounts,
        )
        assert user_tokens[user_address][0] == [A_DAI, token_7776]


def test_superfluid_constant_flow_nfts_are_in_token_exceptions(
        blockchain: 'ChainsAggregator',
        globaldb: 'GlobalDBHandler',
) -> None:
    for chain_id in get_args(SUPPORTED_CHAIN_IDS):
        manager = getattr(blockchain, chain_id.to_name())
        for token in manager.tokens.token_exceptions:
            get_or_create_evm_token(
                userdb=blockchain.database,
                evm_address=token,
                chain_id=chain_id,
                token_kind=EvmTokenKind.ERC721,
                symbol='xxx',
                name='yyy',
                decimals=18,
            )

        _, erc721_tokens = globaldb.get_token_detection_data(
            chain_id=chain_id,
            exceptions=(exceptions := manager.tokens._per_chain_token_exceptions()),
        )
        assert all(i.address not in exceptions for i in erc721_tokens)
