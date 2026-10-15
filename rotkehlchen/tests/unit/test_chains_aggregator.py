import datetime
from contextlib import ExitStack, contextmanager
from functools import partial
from threading import Event
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.activity_retries import ActivityRetryTracker
from rotkehlchen.chain.aggregator import ChainsAggregator, _module_name_to_class
from rotkehlchen.chain.evm.constants import LAST_SPAM_TXS_CACHE
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    SerializableChainIndexerOrder,
    string_to_evm_address,
)
from rotkehlchen.concurrency import TaskCancelledError, result_of, spawn
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.timing import EVMLIKE_ACCOUNTS_DETECTION_RETRY
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.errors.misc import NoAvailableIndexers, RecoverableRemoteError, RemoteError
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    SPAM_PROTOCOL,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    AddressbookType,
    ChainID,
    ChecksumEvmAddress,
    HexColorCode,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.chain.base.manager import BaseManager
    from rotkehlchen.chain.gnosis.manager import GnosisManager
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
    from rotkehlchen.tasks.manager import TaskManager


@pytest.mark.parametrize('ethereum_modules', [[]])
def test_module_activation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        module = blockchain.activate_module(module_name)
        assert isinstance(module, expected_module_type)
        assert blockchain.eth_modules[module_name] == module


@pytest.mark.parametrize('ethereum_modules', [AVAILABLE_MODULES_MAP.keys()])
def test_module_deactivation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        assert isinstance(blockchain.eth_modules[module_name], expected_module_type)
        blockchain.deactivate_module(module_name)
        assert module_name not in blockchain.eth_modules


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_detect_evm_accounts(blockchain: ChainsAggregator) -> None:
    """
    Tests that the detection of EVM accounts activity in chains where they are not tracked yet
    works as expected.
    """
    # Is a contract in ethereum mainnet. Now added to chains where it has activity (optimism, avax)
    eth_addy_contract = string_to_evm_address('0x06FAC6fd222E59D3D8602795fdD88769bCB998Bd')

    # Is an EOA in optimism. Has activity in all chains. Should be added to optimism, and avax
    addy_eoa_1 = string_to_evm_address('0xFaa7Fa8B22704057B8345Ed8C9bE7d5081eefb81')

    # Is an EOA in ethereum mainnet. Has activity only in ethereum and in optimism. Should be
    # added to optimism and should not be added to avax
    addy_eoa_2 = string_to_evm_address('0xeFB06924caC08837153f6544d029A8208b236196')
    # polygon and mainnet - auto-detected on most of the other chains.
    addy_eoa_3 = string_to_evm_address('0xDC50D9Ca7f5D062Acb2f9f8369da9919D9F08F8E')
    # arbitrum and mainnet - auto-detected on polygon
    addy_eoa_4 = string_to_evm_address('0x1cdE61EC6C5De8E479d463a1abeaF588E36F5326')

    # Is an EOA that is initially already added everywhere. Has activity in all chains.
    # Since is already added, should not be added again.
    everywhere_addy = string_to_evm_address('0x0cBc2327D4E4aA011807C20ea81FAba73Ad603ab')

    # Labels are as follows:
    # addy_eoa_2 - same label set on both ethereum and polygon initially - Updated to multichain
    # addy_eoa_3 - label set only on ethereum initially - Updated to multichain
    # addy_eoa_4 - different labels on ethereum and arbitrum one - Not updated to multichain

    initial_accounts_data = []
    addies_to_start_with = [
        (SupportedBlockchain.ETHEREUM, eth_addy_contract, None),
        (SupportedBlockchain.OPTIMISM, addy_eoa_1, None),
        (SupportedBlockchain.ETHEREUM, addy_eoa_2, (label1 := 'Label 1')),
        (SupportedBlockchain.POLYGON_POS, addy_eoa_2, label1),
        (SupportedBlockchain.ETHEREUM, addy_eoa_3, (label2 := 'Label 2')),
        (SupportedBlockchain.ETHEREUM, addy_eoa_4, 'Label 3'),
        (SupportedBlockchain.ARBITRUM_ONE, addy_eoa_4, 'Label 4'),
        (SupportedBlockchain.ETHEREUM, everywhere_addy, None),
        (SupportedBlockchain.OPTIMISM, everywhere_addy, None),
        (SupportedBlockchain.AVALANCHE, everywhere_addy, None),
        (SupportedBlockchain.POLYGON_POS, everywhere_addy, None),
        (SupportedBlockchain.ARBITRUM_ONE, everywhere_addy, None),
        (SupportedBlockchain.BASE, everywhere_addy, None),
        (SupportedBlockchain.GNOSIS, everywhere_addy, None),
        (SupportedBlockchain.SCROLL, everywhere_addy, None),
        (SupportedBlockchain.BINANCE_SC, everywhere_addy, None),
        (SupportedBlockchain.MONAD, everywhere_addy, None),
    ]

    for chain, addy, label in addies_to_start_with:
        with blockchain.database.user_write() as write_cursor:
            blockchain.modify_blockchain_accounts(
                write_cursor=write_cursor,
                blockchain=chain,
                accounts=[addy],
                append_or_remove='append',
            )
        initial_accounts_data.append(BlockchainAccountData(
            chain=chain,
            address=addy,
            label=label,
        ))

    with blockchain.database.user_write() as write_cursor:
        blockchain.database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=initial_accounts_data,
        )

    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=blockchain,
            eth_contract_addresses=[eth_addy_contract, everywhere_addy],
            ethereum_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1, addy_eoa_2],
            optimism_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1, addy_eoa_2],
            avalanche_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1],
            polygon_pos_addresses=[everywhere_addy, addy_eoa_3, addy_eoa_4],
            arbitrum_one_addresses=[everywhere_addy, addy_eoa_3],
            base_addresses=[everywhere_addy, addy_eoa_3],
            gnosis_addresses=[everywhere_addy, addy_eoa_3],
            scroll_addresses=[everywhere_addy, addy_eoa_3],
            binance_sc_addresses=[everywhere_addy, addy_eoa_3],
            monad_addresses=[everywhere_addy, addy_eoa_3],
        )

        blockchain.detect_evm_accounts()

    assert set(blockchain.accounts.eth) == {addy_eoa_1, addy_eoa_2, addy_eoa_3, addy_eoa_4, eth_addy_contract, everywhere_addy}  # noqa: E501
    assert set(blockchain.accounts.optimism) == {addy_eoa_1, addy_eoa_2, eth_addy_contract, everywhere_addy}  # noqa: E501
    assert set(blockchain.accounts.avax) == {addy_eoa_1, everywhere_addy, eth_addy_contract}
    assert set(blockchain.accounts.polygon_pos) == {addy_eoa_2, addy_eoa_3, addy_eoa_4, everywhere_addy}  # noqa: E501
    assert set(blockchain.accounts.arbitrum_one) == {addy_eoa_3, addy_eoa_4, everywhere_addy}
    assert set(blockchain.accounts.base) == {addy_eoa_3, everywhere_addy}
    assert set(blockchain.accounts.gnosis) == {addy_eoa_3, everywhere_addy}
    assert set(blockchain.accounts.scroll) == {addy_eoa_3, everywhere_addy}
    assert set(blockchain.accounts.binance_sc) == {addy_eoa_3, everywhere_addy}
    assert set(blockchain.accounts.monad) == {addy_eoa_3, everywhere_addy}

    # Also check the db
    expected_accounts_data = initial_accounts_data + [
        BlockchainAccountData(chain=chain, address=address, label=label)
        for chain, address, label in (
            (SupportedBlockchain.ETHEREUM, addy_eoa_1, None),
            (SupportedBlockchain.AVALANCHE, addy_eoa_1, None),
            (SupportedBlockchain.AVALANCHE, eth_addy_contract, None),
            (SupportedBlockchain.OPTIMISM, eth_addy_contract, None),
            (SupportedBlockchain.OPTIMISM, addy_eoa_2, label1),
            (SupportedBlockchain.POLYGON_POS, addy_eoa_4, None),
            (SupportedBlockchain.POLYGON_POS, addy_eoa_3, label2),
            (SupportedBlockchain.ARBITRUM_ONE, addy_eoa_3, label2),
            (SupportedBlockchain.BASE, addy_eoa_3, label2),
            (SupportedBlockchain.GNOSIS, addy_eoa_3, label2),
            (SupportedBlockchain.SCROLL, addy_eoa_3, label2),
            (SupportedBlockchain.BINANCE_SC, addy_eoa_3, label2),
            (SupportedBlockchain.MONAD, addy_eoa_3, label2),
        )
    ]

    with blockchain.database.conn.read_ctx() as cursor:
        raw_accounts = blockchain.database.get_blockchain_accounts(cursor)

    accounts_in_db = [
        BlockchainAccountData(
            chain=chain,
            address=account,
            label=DBAddressbook(blockchain.database).get_addressbook_entry_name(
                book_type=AddressbookType.PRIVATE,
                chain_address=OptionalChainAddress(address=account, blockchain=chain),  # type: ignore[arg-type]  # account will be ChecksumAddress here
            ),
        )
        for chain in (
            SupportedBlockchain.ETHEREUM,
            SupportedBlockchain.OPTIMISM,
            SupportedBlockchain.AVALANCHE,
            SupportedBlockchain.POLYGON_POS,
            SupportedBlockchain.ARBITRUM_ONE,
            SupportedBlockchain.BASE,
            SupportedBlockchain.GNOSIS,
            SupportedBlockchain.SCROLL,
            SupportedBlockchain.BINANCE_SC,
            SupportedBlockchain.MONAD,
        ) for account in raw_accounts.get(chain)
    ]

    assert set(accounts_in_db) == set(expected_accounts_data)
    assert len(accounts_in_db) == len(expected_accounts_data)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2023-06-19 05:16:10 GMT')
@pytest.mark.parametrize('polygon_pos_accounts', [[make_evm_address()]])  # to connect to nodes
@pytest.mark.skip(reason='requires a credentialed Polygon RPC cassette')
def test_detect_evm_accounts_spam_tx(polygon_pos_manager: PolygonPOSManager) -> None:
    """
    Test that an account with only erc20 transfers of spam tokens gets marked as spam
    and does not get detected as a tracked account in the EVM chain.

    The tested address has received the following spam tokens
    eip155:137/erc20:0x91bD4023A21bc12814905f251eb348e298DBC0F0
    eip155:137/erc20:0xD6198855979714255d711A4bB8BF1763d28A473B
    eip155:137/erc20:0xb76c90B51338016011Eaf27C348E3D84A623C5BF
    eip155:137/erc20:0x5522962DCE6BE2a009D29E5699a67C38b392beb9
    eip155:137/erc20:0xd9503c336512120Aa6834Ab5d9258a32940bB2C6
    eip155:137/erc20:0x9715A23D25399EF10D819e4999689de3d14eB7e2
    eip155:137/erc20:0xb266edC3706fC2A48ECFef7DD8831435f12D9966
    eip155:137/erc20:0x06732174B52743C374445E88C9b01031Bd0FB28f
    eip155:137/erc20:0xE2Ee00F49464d6B60771dc118A1bb4eb362bd154
    eip155:137/erc20:0x37CC5F5610d91325c8A8C0eD74d26A01F19e7B51

    first we check that it is marked as spammed by:
    - ignoring the first asset
    - adding the second as spam asset

    to verify that the address has been spammed all the remaining assets are ignored
    """
    evm_address = string_to_evm_address('0xc1C736F2Ac0e0019A188982c7c8C063976A4d8d9')
    db = polygon_pos_manager.node_inquirer.database
    with db.user_write() as write_cursor:
        db.add_to_ignored_assets(
            write_cursor=write_cursor,
            asset=Asset('eip155:137/erc20:0x91bD4023A21bc12814905f251eb348e298DBC0F0'),
        )
    get_or_create_evm_token(
        userdb=polygon_pos_manager.node_inquirer.database,
        evm_address=string_to_evm_address('0xD6198855979714255d711A4bB8BF1763d28A473B'),
        chain_id=ChainID.POLYGON_POS,
        protocol=SPAM_PROTOCOL,
    )
    assert polygon_pos_manager.transactions.address_has_been_spammed(evm_address) is True

    spam_assets = [
        Asset('eip155:137/erc20:0xb76c90B51338016011Eaf27C348E3D84A623C5BF'),
        Asset('eip155:137/erc20:0x5522962DCE6BE2a009D29E5699a67C38b392beb9'),
        Asset('eip155:137/erc20:0xd9503c336512120Aa6834Ab5d9258a32940bB2C6'),
        Asset('eip155:137/erc20:0x9715A23D25399EF10D819e4999689de3d14eB7e2'),
        Asset('eip155:137/erc20:0xb266edC3706fC2A48ECFef7DD8831435f12D9966'),
        Asset('eip155:137/erc20:0x06732174B52743C374445E88C9b01031Bd0FB28f'),
        Asset('eip155:137/erc20:0xE2Ee00F49464d6B60771dc118A1bb4eb362bd154'),
        Asset('eip155:137/erc20:0x37CC5F5610d91325c8A8C0eD74d26A01F19e7B51'),
    ]
    with db.user_write() as write_cursor:
        for asset in spam_assets:
            db.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)

    assert polygon_pos_manager.transactions.address_has_been_spammed(evm_address) is True


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-05-03 10:45:00 GMT')
@pytest.mark.parametrize('gnosis_accounts', [[make_evm_address()]])  # to connect to nodes
def test_detect_evm_accounts_spam_tx_gnosis(
        gnosis_manager: GnosisManager,
        allow_gnosis_etherscan: None,
) -> None:
    """
    Test that an account with only erc20 transfers of spam tokens gets marked as spam
    and does not get detected as a tracked account in the EVM chain.

    The tested address has received the following spam tokens:
    eip155:100/erc20:0x8786B9c1a0C676B191284A4Bc7e448321197BB05
    eip155:100/erc20:0xC1BeC4618B212441E367ED363540D5D665e8e4F0
    """
    # This evm address has only received spam transactions
    evm_address = string_to_evm_address('0xF5d90Ac6747CB3352F05BF61f48b991ACeaE28eB')
    database = gnosis_manager.node_inquirer.database

    # check that the cache is not set
    with database.conn.read_ctx() as cursor:
        result = database.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.LAST_QUERY_TS,
            location=gnosis_manager.node_inquirer.chain_name,
            location_name=LAST_SPAM_TXS_CACHE,
            account_id=evm_address,
        )
    assert result is None

    for spam_asset in (
        '0x8786B9c1a0C676B191284A4Bc7e448321197BB05',
        '0xC1BeC4618B212441E367ED363540D5D665e8e4F0',
    ):  # spam tokens received by the address
        get_or_create_evm_token(
            userdb=gnosis_manager.node_inquirer.database,
            evm_address=string_to_evm_address(spam_asset),
            chain_id=ChainID.GNOSIS,
            protocol=SPAM_PROTOCOL,
        )

    assert gnosis_manager.transactions.address_has_been_spammed(evm_address) is True

    # check that the cache is updated
    with database.conn.read_ctx() as cursor:
        result = database.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.LAST_QUERY_TS,
            location=gnosis_manager.node_inquirer.chain_name,
            location_name=LAST_SPAM_TXS_CACHE,
            account_id=evm_address,
        )
    assert result is not None

    block_number = gnosis_manager.node_inquirer.get_blocknumber_by_time(ts=result, closest='before')  # noqa: E501
    with patch('requests.get') as mocked_get:
        assert gnosis_manager.transactions.address_has_been_spammed(evm_address) is True
        # verify that the gnosiscan API get's queried with the last recorded blocknumber
        assert all(f'startBlock={block_number}' in call.args[0] for call in mocked_get.mock_calls), "URL must contain 'startBlock=' and correct block number"  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', [{
    'evm_indexers_order': SerializableChainIndexerOrder(
        order={ChainID.BASE: [EvmIndexer.BLOCKSCOUT]},
    ),
}])
@pytest.mark.freeze_time(datetime.datetime.fromtimestamp(1717416305, tz=datetime.UTC))
@pytest.mark.parametrize('base_accounts', [['0xeA2B3D309bC480Fe385BBF8aEF6D45D81825A784']])
def test_detect_spammed_transaction_new_token(
        base_manager: BaseManager,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    """Check that the functionality to detect accounts that have been sent only spam tokens
    works correctly when the received token hasn't been previously tracked.
    The address used in this test has only one transaction in the time range of
    [1717116105, 1717116305] where it received a spam token that is not in the database.
    """
    with patch.object(
        base_manager.node_inquirer.database,
        'get_dynamic_cache',
        side_effect=lambda *args, **kwargs: 1717116105,
    ):
        assert base_manager.transactions.address_has_been_spammed(
            address=base_accounts[0],
        ) is True


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
    '0xC0FfEE254729296a45a3885639AC7E10F9d54979',
]])
def test_get_active_addresses(blockchain: ChainsAggregator) -> None:
    """`get_active_addresses` honors the `disabled_chain_queries` setting:
    - missing key   => returns all tracked addresses
    - empty frozen  => returns ()
    - subset frozen => returns the complement
    """
    from rotkehlchen.db.settings import CachedSettings
    addr_a, addr_b = blockchain.accounts.eth

    # 1. Missing key => all tracked addresses returned
    CachedSettings().update_entry('disabled_chain_queries', {})
    assert blockchain.get_active_addresses(SupportedBlockchain.ETHEREUM) == (addr_a, addr_b)

    # 2. Empty frozenset => entire chain disabled
    CachedSettings().update_entry(
        'disabled_chain_queries',
        {SupportedBlockchain.ETHEREUM: frozenset()},
    )
    assert blockchain.get_active_addresses(SupportedBlockchain.ETHEREUM) == ()

    # 3. Subset disabled => complement returned
    CachedSettings().update_entry(
        'disabled_chain_queries',
        {SupportedBlockchain.ETHEREUM: frozenset({addr_a})},
    )
    assert blockchain.get_active_addresses(SupportedBlockchain.ETHEREUM) == (addr_b,)

    # Reset for other tests in the same session
    CachedSettings().update_entry('disabled_chain_queries', {})


@pytest.mark.parametrize('ethereum_modules', [[]])
@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_modify_blockchain_accounts_flushes_balance_cache(
        blockchain: ChainsAggregator,
) -> None:
    """Regression test for balance result-cache invalidation on account changes.

    The cached per-chain balance method was renamed to `_query_chain_balances` in commit
    8fe3fdd874, but the `flush_cache` calls in `modify_blockchain_accounts` kept using the
    old `query_balances` name, so the cache key never matched and the entry was never
    invalidated. A non-ignore-cache balance query within the cache TTL would then return
    stale balances (e.g. missing a newly added account).
    """
    chain = SupportedBlockchain.ETHEREUM
    keys_before = set(blockchain.results_cache)
    # Populate the cached full-chain balance query the way a non-ignore-cache query does.
    # With no accounts the method short-circuits (no network) but still caches its result.
    blockchain._query_chain_balances(blockchain=chain, ignore_cache=False, addresses=None)
    cached_keys = set(blockchain.results_cache) - keys_before
    assert len(cached_keys) == 1, 'the full-chain balance query should have been cached'

    with blockchain.database.user_write() as write_cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=chain,
            accounts=[make_evm_address()],
            append_or_remove='append',
        )

    assert cached_keys.isdisjoint(blockchain.results_cache), (
        'adding an account must invalidate the cached chain balance query'
    )


@pytest.mark.parametrize('ethereum_modules', [[]])
@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_query_balances_skips_chains_without_accounts(
        blockchain: ChainsAggregator,
) -> None:
    """Regression test: a full balance refresh must not touch the balances cache for
    chains that have no tracked accounts.

    Previously the refresh loop called `_update_blockchain_balances_cache` (which opens a
    committed write transaction) for every supported chain on each refresh, even the ~14 a
    typical user has no accounts on, deleting nothing each time.
    """
    with patch.object(
        blockchain,
        '_update_blockchain_balances_cache',
        wraps=blockchain._update_blockchain_balances_cache,
    ) as update_mock:
        blockchain.query_balances(blockchain=None, ignore_cache=False)

    updated_chains = {call.kwargs['blockchain'] for call in update_mock.call_args_list}
    # with no accounts anywhere, only the beaconchain branch (handled before the guard)
    # may update the cache; no account-less evm/bitcoin chain should.
    assert updated_chains <= {SupportedBlockchain.ETHEREUM_BEACONCHAIN}, (
        f'cache update ran for account-less chains: {updated_chains}'
    )


@pytest.mark.parametrize('ethereum_modules', [[]])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('optimism_accounts', [[make_evm_address()]])
def test_query_balances_partial_chain_failure(blockchain: ChainsAggregator) -> None:
    """When querying all chains, a chain whose query fails keeps the balances of its last
    successful query and is reported in failed_chains, instead of the failure discarding
    the balances of the chains that were queried fine. Querying the failing chain alone,
    or having every chain fail, still raises."""
    chains_aggregator = blockchain  # the mock below shadows the fixture name with the chain
    eth_address, optimism_address = chains_aggregator.accounts.eth[0], chains_aggregator.accounts.optimism[0]  # noqa: E501
    chains_aggregator.balances.optimism[optimism_address].assets[A_ETH][DEFAULT_BALANCE_LABEL] = Balance(amount=FVal(5), value=FVal(10))  # from a previous successful query  # noqa: E501
    failing_chains = {SupportedBlockchain.OPTIMISM}

    def mock_query_chain(blockchain: SupportedBlockchain, **kwargs: Any) -> None:
        if blockchain in failing_chains:
            raise RemoteError(f'Error querying information from {blockchain!s}')
        if blockchain == SupportedBlockchain.ETHEREUM:
            chains_aggregator.balances.eth[eth_address].assets[A_ETH][DEFAULT_BALANCE_LABEL] = Balance(amount=ONE, value=FVal(2))  # noqa: E501

    with (
        patch.object(chains_aggregator, '_query_chain_balances', side_effect=mock_query_chain),
        patch.object(chains_aggregator, 'query_eth2_balances', side_effect=lambda **kwargs: mock_query_chain(SupportedBlockchain.ETHEREUM_BEACONCHAIN)),  # noqa: E501
        patch.object(chains_aggregator, '_update_blockchain_balances_cache') as cache_mock,
    ):
        update = chains_aggregator.query_balances(ignore_cache=True)
        assert update.failed_chains == {SupportedBlockchain.OPTIMISM: 'Error querying information from optimism'}  # noqa: E501
        assert update.per_account.eth[eth_address].assets[A_ETH][DEFAULT_BALANCE_LABEL] == Balance(amount=ONE, value=FVal(2))  # noqa: E501
        assert update.per_account.optimism[optimism_address].assets[A_ETH][DEFAULT_BALANCE_LABEL] == Balance(amount=FVal(5), value=FVal(10))  # noqa: E501
        assert update.totals.assets[A_ETH][DEFAULT_BALANCE_LABEL] == Balance(amount=FVal(6), value=FVal(12))  # noqa: E501
        assert {call.kwargs['blockchain'] for call in cache_mock.call_args_list} == {
            SupportedBlockchain.ETHEREUM,
            SupportedBlockchain.ETHEREUM_BEACONCHAIN,
        }  # only the chains that succeeded get their cache updated

        with pytest.raises(RemoteError):  # a single chain query still raises
            chains_aggregator.query_balances(blockchain=SupportedBlockchain.OPTIMISM, ignore_cache=True)  # noqa: E501

        failing_chains.update({SupportedBlockchain.ETHEREUM, SupportedBlockchain.ETHEREUM_BEACONCHAIN})  # noqa: E501
        with pytest.raises(RemoteError):  # so does all queried chains failing
            chains_aggregator.query_balances(ignore_cache=True)


@pytest.mark.parametrize(('evm_result', 'core_result', 'expected'), [
    (HasChainActivity.NONE, True, True),  # no HyperEVM activity but active in Core
    (HasChainActivity.NONE, False, False),
    (HasChainActivity.NONE, RemoteError('core'), None),
    (HasChainActivity.TRANSACTIONS, RemoteError('core'), True),  # HyperEVM is enough
    (RemoteError('evm'), True, True),  # HyperEVM lookup failed but Core is active
    (RemoteError('evm'), False, None),  # a HyperEVM failure is not mistaken for inactivity
    (RemoteError('evm'), RemoteError('core'), None),
])
def test_hyperliquid_activity_checks_core(
        blockchain: ChainsAggregator,
        evm_result: HasChainActivity | RemoteError,
        core_result: bool | RemoteError,
        expected: bool | None,
) -> None:
    with (
        patch.object(
            blockchain.hyperliquid.node_inquirer,
            'has_activity',
            side_effect=[evm_result],
        ),
        patch.object(
            HyperliquidAPI,
            'has_core_activity',
            side_effect=[core_result],
        ),
    ):
        assert blockchain._check_single_chain_activity(
            address=make_evm_address(),
            chain=SupportedBlockchain.HYPERLIQUID,
        ) is expected


@pytest.mark.parametrize(('error', 'is_retried'), [
    (RecoverableRemoteError('rate limited'), True),
    (RemoteError('malformed response'), False),  # permanent errors wait for the full detection
    (NoAvailableIndexers('no indexer'), False),  # won't go away by itself
])
def test_detect_evm_accounts_retries_only_failed_pairs(
        blockchain: ChainsAggregator,
        error: RemoteError,
        is_retried: bool,
) -> None:
    """Only recoverable failures are retried, and only for the failed (address, chain) pairs.
    The timestamp of the full detection is not touched by the failures."""
    with blockchain.database.user_write() as write_cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[(address := make_evm_address())],
            append_or_remove='append',
        )

    with patch.object(
        blockchain.hyperliquid.node_inquirer,
        'has_activity',
        side_effect=error,
    ), patch.object(HyperliquidAPI, 'has_core_activity', side_effect=error):
        blockchain.detect_evm_accounts(chains=[SupportedBlockchain.HYPERLIQUID])

    with blockchain.database.conn.read_ctx() as cursor:
        assert ts_now() - int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS.value,),
        ).fetchone()[0]) < 10  # full detection timestamp is never backdated

    failed_pairs = set(blockchain._activity_retries._pending)
    if is_retried:
        assert (address, SupportedBlockchain.HYPERLIQUID) in failed_pairs
        assert {chain for _, chain in failed_pairs} == {SupportedBlockchain.HYPERLIQUID}
    else:
        assert failed_pairs == set()

    assert blockchain.should_retry_activity_checks() is False  # not due yet
    if is_retried:
        blockchain._activity_retries._due_ts = Timestamp(ts_now() - 1)
        assert blockchain.should_retry_activity_checks() is True

    with patch.object(
        blockchain.hyperliquid.node_inquirer,
        'has_activity',
        return_value=HasChainActivity.NONE,
    ) as evm_mock, patch.object(
        HyperliquidAPI,
        'has_core_activity',
        return_value=True,
    ):
        added = blockchain.retry_failed_activity_checks()

    # only the failed pairs were checked again, not every untracked address/chain combination
    assert evm_mock.call_count == len(failed_pairs)
    assert {(chain, account) for chain, account in added} == {
        (chain, account) for account, chain in failed_pairs
    }
    for account, chain in failed_pairs:
        assert account in blockchain.accounts.get(chain)

    assert blockchain.should_retry_activity_checks() is False


def test_recoverable_failure_outside_detection_is_not_retried_immediately(
        blockchain: ChainsAggregator,
) -> None:
    """A recoverable failure from any path (e.g. adding an account) schedules the retry after
    EVMLIKE_ACCOUNTS_DETECTION_RETRY, instead of making the next scheduler tick retry it."""
    with patch.object(
        blockchain.hyperliquid.node_inquirer,
        'has_activity',
        side_effect=RecoverableRemoteError('timeout'),
    ), patch.object(HyperliquidAPI, 'has_core_activity', side_effect=RecoverableRemoteError('x')):
        assert blockchain._check_single_chain_activity(
            address=(address := make_evm_address()),
            chain=SupportedBlockchain.HYPERLIQUID,
        ) is None

    assert (address, SupportedBlockchain.HYPERLIQUID) in blockchain._activity_retries._pending
    assert blockchain.should_retry_activity_checks() is False
    assert blockchain._activity_retries._due_ts >= ts_now() + EVMLIKE_ACCOUNTS_DETECTION_RETRY - 10


def test_retry_skips_chains_excluded_from_detection_since_the_failure(
        blockchain: ChainsAggregator,
) -> None:
    with blockchain.database.user_write() as write_cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[(address := make_evm_address())],
            append_or_remove='append',
        )

    blockchain._activity_retries.record_failures([(address, SupportedBlockchain.HYPERLIQUID)])
    with (
        patch.object(blockchain.database, 'get_chains_to_detect_evm_accounts', return_value=[]),
        patch.object(blockchain, 'check_chains_and_add_accounts') as check_mock,
    ):
        assert blockchain.retry_failed_activity_checks() == []

    assert check_mock.call_count == 0
    assert blockchain._activity_retries.has_pending() is False


def test_untracked_submitted_address_is_retried(blockchain: ChainsAggregator) -> None:
    """An address the user submitted whose only checks failed is tracked nowhere, but the
    retry must still reconsider it, also after a retry that fails again. The full detection
    also must not forget it."""
    address = make_evm_address()
    error = RecoverableRemoteError('rate limited')
    with (
        patch(
            'rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.has_activity',
            side_effect=error,
        ),
        patch('rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.is_contract', return_value=False),  # noqa: E501
        patch.object(HyperliquidAPI, 'has_core_activity', side_effect=error),
        patch.object(blockchain.zksync_lite, '_query_api', side_effect=error),
    ):
        blockchain.add_accounts_to_all_evm([address])
        # a full detection does not redo untracked addresses, so it keeps the pending check
        blockchain.detect_evm_accounts(chains=[SupportedBlockchain.HYPERLIQUID])
        pending = {
            check for check, submitted in blockchain._activity_retries._pending.items()
            if check[0] == address and submitted is True
        }
        assert (address, SupportedBlockchain.HYPERLIQUID) in pending

        blockchain._activity_retries._due_ts = Timestamp(ts_now() - 1)
        assert blockchain.retry_failed_activity_checks() == []  # fails again

    # still pending, and still submitted. Otherwise the next retry would skip it as untracked
    assert blockchain._activity_retries._pending[address, SupportedBlockchain.HYPERLIQUID] is True
    blockchain._activity_retries._due_ts = Timestamp(ts_now() - 1)
    assert blockchain.should_retry_activity_checks() is True
    with (
        patch(
            'rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.has_activity',
            return_value=HasChainActivity.NONE,
        ),
        patch.object(HyperliquidAPI, 'has_core_activity', return_value=True),
        patch.object(blockchain.zksync_lite, '_query_api', return_value={'list': []}),
    ):
        assert (SupportedBlockchain.HYPERLIQUID, address) in blockchain.retry_failed_activity_checks()  # noqa: E501

    assert address in blockchain.accounts.get(SupportedBlockchain.HYPERLIQUID)


def test_retry_does_not_readd_removed_untracked_address(blockchain: ChainsAggregator) -> None:
    """A pending check of an address that was tracked, and that the user removed
    everywhere, must not bring it back"""
    with blockchain.database.user_write() as write_cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[(address := make_evm_address())],
            append_or_remove='append',
        )

    blockchain._activity_retries.record_failures(
        [(address, SupportedBlockchain.HYPERLIQUID)], submitted=True,
    )
    with blockchain.database.user_write() as write_cursor:
        blockchain.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[address],
        )

    assert blockchain._activity_retries.has_pending() is False
    with blockchain.database.conn.read_ctx() as cursor:  # and it is gone from the DB too
        assert cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name=?',
            (DBCacheStatic.EVM_ACCOUNTS_DETECT_RETRIES.value,),
        ).fetchone()[0] == 0


def test_pending_activity_retries_survive_restart(blockchain: ChainsAggregator) -> None:
    """The pending checks and their due time are read back from the DB, and an unreadable
    value is dropped instead of breaking the login."""
    address = make_evm_address()
    blockchain._activity_retries.record_failures(
        [(address, SupportedBlockchain.HYPERLIQUID)], submitted=True,
    )
    due_ts = blockchain._activity_retries._due_ts

    restarted = ActivityRetryTracker(blockchain.database)
    assert restarted._pending == {(address, SupportedBlockchain.HYPERLIQUID): True}
    assert restarted._due_ts == due_ts
    assert restarted.is_due() is False

    with blockchain.database.user_write() as write_cursor:
        blockchain.database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.EVM_ACCOUNTS_DETECT_RETRIES,
            value='{"due_ts": 1, "checks": [{"address": "0x1", "chain": "NOPE"}]}',
        )
    assert ActivityRetryTracker(blockchain.database).has_pending() is False


def _blocked_core_activity(started: Event, release: Event, result: bool | RemoteError, **kwargs: Any) -> bool:  # noqa: E501
    started.set()
    assert release.wait(10)
    if isinstance(result, RemoteError):
        raise result
    return result


@pytest.mark.parametrize('result', [True, RecoverableRemoteError('still unavailable')])
def test_removal_during_activity_retry_is_respected(
        blockchain: ChainsAggregator,
        result: bool | RemoteError,
) -> None:
    """Removal invalidates both a late positive response and a late recoverable failure."""
    address = make_evm_address()
    with blockchain.database.user_write() as cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[address],
            append_or_remove='append',
        )
    blockchain._activity_retries.record_failures(
        [(address, SupportedBlockchain.HYPERLIQUID)], submitted=True,
    )
    started, release = Event(), Event()
    with (
        patch.object(blockchain.hyperliquid.node_inquirer, 'has_activity', return_value=HasChainActivity.NONE),  # noqa: E501
        patch.object(HyperliquidAPI, 'has_core_activity', side_effect=partial(
            _blocked_core_activity, started, release, result,
        )),
    ):
        task = spawn(blockchain.retry_failed_activity_checks)
        try:
            assert started.wait(10)
            # The queue must remain durable even while the retry is on the network.
            restarted = ActivityRetryTracker(blockchain.database)
            with blockchain.database.user_write() as cursor:
                blockchain.remove_single_blockchain_accounts(
                    write_cursor=cursor,
                    blockchain=SupportedBlockchain.ETHEREUM,
                    accounts=[address],
                )
        finally:
            release.set()
            task.join(10)
        assert task.dead
        assert result_of(task) == []

    assert address not in blockchain.accounts.get(SupportedBlockchain.HYPERLIQUID)
    assert blockchain._activity_retries.has_pending() is False
    assert ActivityRetryTracker(blockchain.database).has_pending() is False
    assert restarted.has_pending() is True


@pytest.mark.parametrize('full_detection', [False, True])
def test_cancelled_activity_retry_remains_durable(
        blockchain: ChainsAggregator,
        full_detection: bool,
) -> None:
    address = make_evm_address()
    if full_detection:
        with blockchain.database.user_write() as cursor:
            blockchain.modify_blockchain_accounts(
                write_cursor=cursor,
                blockchain=SupportedBlockchain.ETHEREUM,
                accounts=[address],
                append_or_remove='append',
            )
    blockchain._activity_retries.record_failures(
        [(address, SupportedBlockchain.HYPERLIQUID)], submitted=True,
    )
    operation = (
        partial(blockchain.detect_evm_accounts, chains=[SupportedBlockchain.HYPERLIQUID])
        if full_detection else blockchain.retry_failed_activity_checks
    )
    with (
        patch.object(
            blockchain, 'check_chains_and_add_accounts', side_effect=TaskCancelledError(),
        ),
        pytest.raises(TaskCancelledError),
    ):
        operation()

    assert ActivityRetryTracker(blockchain.database)._pending == {
        (address, SupportedBlockchain.HYPERLIQUID): True,
    }


def test_activity_retry_scheduler_after_restart(task_manager: TaskManager) -> None:
    """A recent full scan must not prevent a restored, due targeted retry from running."""
    blockchain = task_manager.chains_aggregator
    address = make_evm_address()
    with blockchain.database.user_write() as cursor:
        blockchain.database.set_static_cache(
            write_cursor=cursor, name=DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS, value=ts_now(),
        )
    with patch('rotkehlchen.chain.activity_retries.ts_now', return_value=ts_now() - 2 * EVMLIKE_ACCOUNTS_DETECTION_RETRY):  # noqa: E501
        blockchain._activity_retries.record_failures(
            [(address, SupportedBlockchain.HYPERLIQUID)], submitted=True,
        )
    blockchain._activity_retries = ActivityRetryTracker(blockchain.database)
    assert task_manager._maybe_detect_evm_accounts() is None
    with (
        patch.object(blockchain.hyperliquid.node_inquirer, 'has_activity', return_value=HasChainActivity.NONE),  # noqa: E501
        patch.object(HyperliquidAPI, 'has_core_activity', return_value=True),
    ):
        tasks = task_manager._maybe_retry_failed_evm_detections()
        assert tasks is not None
        assert len(tasks) == 1
        assert result_of(tasks[0]) == [(SupportedBlockchain.HYPERLIQUID, address)]

    assert ActivityRetryTracker(blockchain.database).has_pending() is False


@contextmanager
def _only_hyperliquid_check_fails(blockchain: ChainsAggregator) -> Iterator[None]:
    """Every chain reports no activity except Hyperliquid, whose HyperEVM and Core
    checks fail recoverably."""
    def has_activity(self: Any, chain_id: ChainID, account: ChecksumEvmAddress) -> HasChainActivity:  # noqa: E501
        if chain_id == ChainID.HYPERLIQUID:
            raise RecoverableRemoteError('rate limited')
        return HasChainActivity.NONE

    with (
        patch('rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.has_activity', has_activity),
        patch('rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.is_contract', return_value=False),  # noqa: E501
        patch.object(HyperliquidAPI, 'has_core_activity', side_effect=RecoverableRemoteError('rate limited')),  # noqa: E501
        patch.object(blockchain.zksync_lite, '_query_api', return_value={'list': []}),
        patch.object(blockchain.avalanche, 'w3', MagicMock(**{'eth.get_transaction_count.return_value': 0})),  # noqa: E501
        patch.object(blockchain.avalanche, 'get_avax_balance', return_value=ZERO),
    ):
        yield


def _retry_with_core_active(blockchain: ChainsAggregator) -> list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]]:  # noqa: E501
    blockchain._activity_retries._due_ts = Timestamp(ts_now() - 1)
    with (
        patch('rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.has_activity', return_value=HasChainActivity.NONE),  # noqa: E501
        patch.object(HyperliquidAPI, 'has_core_activity', return_value=True),
    ):
        return blockchain.retry_failed_activity_checks()


def _add_tags(blockchain: ChainsAggregator, *names: str) -> None:
    with blockchain.database.user_write() as write_cursor:
        for name in names:
            blockchain.database.add_tag(
                write_cursor=write_cursor,
                name=name,
                description=None,
                background_color=HexColorCode('ffffff'),
                foreground_color=HexColorCode('000000'),
            )


def _saved_metadata(blockchain: ChainsAggregator, address: ChecksumEvmAddress) -> tuple[list[str], set[str]]:  # noqa: E501
    with blockchain.database.conn.read_ctx() as cursor:
        return (
            [row[0] for row in cursor.execute(
                'SELECT name FROM address_book WHERE address=? AND blockchain=?',
                (address, SupportedBlockchain.HYPERLIQUID.value),
            )],
            {row[0] for row in cursor.execute(
                'SELECT tag_name FROM tag_mappings WHERE object_reference=?', (address,),
            )},
        )


def test_delayed_retry_keeps_the_submitted_label_and_tags(blockchain: ChainsAggregator) -> None:
    """The user's label and tags must not be lost if the retry is what starts tracking the
    address. A tag deleted in the meantime is skipped instead of failing the whole write."""
    address = make_evm_address()
    _add_tags(blockchain, 'trading', 'gone')
    with _only_hyperliquid_check_fails(blockchain):
        blockchain.add_accounts_to_all_evm(
            [address],
            account_data={address: SingleBlockchainAccountData(
                address=address, label='Core only', tags=['Trading', 'gone'],
            )},
        )

    assert address not in blockchain.accounts.get(SupportedBlockchain.HYPERLIQUID)
    with blockchain.database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM tags WHERE name=?', ('gone',))

    assert _retry_with_core_active(blockchain) == [(SupportedBlockchain.HYPERLIQUID, address)]
    assert _saved_metadata(blockchain, address) == (['Core only'], {'trading'})
    assert blockchain._activity_retries.get_submission(address) is None  # nothing left to retry


def test_delayed_retry_does_not_reapply_the_submission_to_a_tracked_address(
        blockchain: ChainsAggregator,
) -> None:
    """Tags are per address. If the address was already added elsewhere with its submission,
    the retry must not bring back a tag the user removed since."""
    address = make_evm_address()
    _add_tags(blockchain, 'keep', 'removed')
    with _only_hyperliquid_check_fails(blockchain):
        blockchain.add_accounts_to_all_evm(
            [address],
            account_data={address: SingleBlockchainAccountData(
                address=address, label='Mine', tags=['keep', 'removed'],
            )},
        )

    with blockchain.database.user_write() as write_cursor:  # tracked elsewhere and tagged
        blockchain.modify_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[address],
            append_or_remove='append',
        )
        blockchain.database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM, address=address, label='Mine', tags=['keep', 'removed'],  # noqa: E501
            )],
        )
        write_cursor.execute("DELETE FROM tag_mappings WHERE tag_name='removed'")  # user edit

    assert _retry_with_core_active(blockchain) == [(SupportedBlockchain.HYPERLIQUID, address)]
    assert _saved_metadata(blockchain, address) == ([], {'keep'})


def test_submission_is_durable_when_adding_is_interrupted(blockchain: ChainsAggregator) -> None:
    """The failure is stored as explicitly submitted, with the label, as soon as it happens,
    so a logout, shutdown or restart before the end of the operation can't drop the retry."""
    address, other = make_evm_address(), make_evm_address()
    original = blockchain.check_chains_and_add_accounts

    def interrupted(account: ChecksumEvmAddress, **kwargs: Any) -> Any:
        if account == other:
            raise TaskCancelledError
        return original(account=account, **kwargs)

    with (
        _only_hyperliquid_check_fails(blockchain),
        patch.object(blockchain, 'check_chains_and_add_accounts', interrupted),
        pytest.raises(TaskCancelledError),
    ):
        blockchain.add_accounts_to_all_evm(
            [address, other],
            account_data={address: SingleBlockchainAccountData(address=address, label='Core only')},  # noqa: E501
        )

    restarted = ActivityRetryTracker(blockchain.database)
    assert restarted._pending == {(address, SupportedBlockchain.HYPERLIQUID): True}
    assert restarted.get_submission(address) == SingleBlockchainAccountData(address=address, label='Core only')  # noqa: E501

    blockchain._activity_retries = restarted
    assert _retry_with_core_active(blockchain) == [(SupportedBlockchain.HYPERLIQUID, address)]
    assert _saved_metadata(blockchain, address) == (['Core only'], set())


def test_pending_state_without_submissions_is_still_loaded(blockchain: ChainsAggregator) -> None:
    """The state persisted before submissions were stored must not be dropped"""
    address = make_evm_address()
    with blockchain.database.user_write() as write_cursor:
        blockchain.database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.EVM_ACCOUNTS_DETECT_RETRIES,
            value=f'{{"due_ts": 1, "checks": [{{"address": "{address}", "chain": "{SupportedBlockchain.HYPERLIQUID.value}", "submitted": true}}]}}',  # noqa: E501
        )

    restarted = ActivityRetryTracker(blockchain.database)
    assert restarted._pending == {(address, SupportedBlockchain.HYPERLIQUID): True}
    assert restarted.get_submission(address) is None


def test_detected_account_save_skips_removed_accounts(blockchain: ChainsAggregator) -> None:
    """An account removed between tracking and saving must stay absent from the DB and
    from the detected-account result sent to the frontend."""
    address = make_evm_address()
    with blockchain.database.user_write() as cursor:
        blockchain.modify_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.HYPERLIQUID,
            accounts=[address],
            append_or_remove='append',
        )
        blockchain.remove_single_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.HYPERLIQUID,
            accounts=[address],
        )

    added: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = [
        (SupportedBlockchain.HYPERLIQUID, address),
    ]
    blockchain._save_detected_accounts(added)
    assert added == []
    with blockchain.database.conn.read_ctx() as cursor:
        assert address not in blockchain.database.get_single_blockchain_addresses(
            cursor, SupportedBlockchain.HYPERLIQUID,
        )
