import itertools
import sqlite3
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from rotkehlchen.assets.asset import (
    Asset,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    FiatAsset,
    UnderlyingToken,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.assets.utils import (
    check_if_spam_token,
    get_or_create_evm_token,
    symbol_to_asset_or_token,
)
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BAT, A_CRV, A_DAI, A_ETH, A_LUSD, A_PICKLE, A_USD
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ONE
from rotkehlchen.constants.resolver import ethaddress_to_identifier, evm_address_to_identifier
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.filtering import CustomAssetsFilterQuery
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.globaldb.cache import (
    globaldb_delete_general_cache,
    globaldb_get_general_cache_last_queried_ts,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION, GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.globaldb import create_initial_globaldb_test_tokens
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    EvmTokenKind,
    GeneralCacheType,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


selfkey_address = string_to_evm_address('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7')
selfkey_id = ethaddress_to_identifier(selfkey_address)
selfkey_asset = EvmToken.initialize(
    name='Selfkey',
    symbol='KEY',
    started=Timestamp(1508803200),
    forked=None,
    swapped_for=None,
    address=selfkey_address,
    chain_id=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    decimals=18,
    cryptocompare=None,
    coingecko='selfkey',
    protocol=None,
)
selfkey_asset_data = AssetData(
    identifier=selfkey_id,
    name='Selfkey',
    symbol='KEY',
    asset_type=AssetType.EVM_TOKEN,
    started=Timestamp(1508803200),
    forked=None,
    swapped_for=None,
    address=selfkey_address,
    chain_id=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    decimals=18,
    cryptocompare=None,
    coingecko='selfkey',
    protocol=None,
)
bidr_asset_data = AssetData(
    identifier='BIDR',
    name='Binance IDR Stable Coin',
    symbol='BIDR',
    asset_type=AssetType.BINANCE_TOKEN,
    started=Timestamp(1593475200),
    forked=None,
    swapped_for=None,
    address=None,
    chain_id=None,
    token_kind=None,
    decimals=None,
    cryptocompare=None,
    coingecko='binanceidr',
    protocol=None,
)
bidr_asset = CryptoAsset.initialize(
    identifier='BIDR',
    name='Binance IDR Stable Coin',
    symbol='BIDR',
    asset_type=AssetType.BINANCE_TOKEN,
    started=Timestamp(1593475200),
    forked=None,
    swapped_for=None,
    cryptocompare=None,
    coingecko='binanceidr',
)


A_yDAI = Asset('eip155:1/erc20:0x19D3364A399d251E894aC732651be8B0E4e85001')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
def test_get_ethereum_token_identifier(globaldb):
    user_tokens = create_initial_globaldb_test_tokens()
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_evm_token_identifier(
            cursor=cursor,
            address='0xnotexistingaddress',
            chain_id=ChainID.ETHEREUM,
        ) is None
        token_0_id = globaldb.get_evm_token_identifier(
            cursor=cursor,
            address=user_tokens[0].evm_address,
            chain_id=ChainID.ETHEREUM,
        )
    assert token_0_id == user_tokens[0].identifier


def test_open_new_globaldb_with_old_rotki(tmpdir_factory, sql_vm_instructions_cb):
    """Test for https://github.com/rotki/rotki/issues/2781"""
    # clean the previous resolver memory cache, as it
    # may have cached results from a discarded database
    AssetResolver().clean_memory_cache()
    version = 9999999999
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    source_db_path = root_dir / 'tests' / 'data' / f'v{version}_global.db'
    new_data_dir = Path(tmpdir_factory.mktemp('test_data_dir'))
    new_global_dir = new_data_dir / 'global_data'
    new_global_dir.mkdir(parents=True, exist_ok=True)
    copyfile(source_db_path, new_global_dir / 'global.db')
    with pytest.raises(ValueError) as excinfo:
        create_globaldb(new_data_dir, sql_vm_instructions_cb)

    msg = (
        f'Tried to open a rotki version intended to work with GlobalDB v{GLOBAL_DB_VERSION} '
        f'but the GlobalDB found in the system is v{version}. Bailing ...'
    )
    assert msg in str(excinfo.value)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_add_edit_token_with_wrong_swapped_for(globaldb):
    """Test that giving a non-existing swapped_for token in the DB raises InputError

    This can only be unit tested since via the API, marshmallow checks for Asset existence already
    """
    # To unit test it we need to even hack it a bit. Make a new token, add it in the DB
    # then delete it and then try to add a new one referencing the old one. Since we
    # need to obtain a valid EvmToken object
    address_to_delete = make_evm_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    token_to_delete_id = token_to_delete.identifier
    globaldb.add_asset(token_to_delete)
    asset_to_delete = Asset(token_to_delete_id)
    assert globaldb.delete_evm_token(
        address=address_to_delete,
        chain_id=ChainID.ETHEREUM,
    ) == token_to_delete_id

    # now try to add a new token with swapped_for pointing to a non existing token in the DB
    with pytest.raises(InputError):
        globaldb.add_asset(EvmToken.initialize(
            address=make_evm_address(),
            chain_id=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            swapped_for=asset_to_delete,
        ))

    # now edit a new token with swapped_for pointing to a non existing token in the DB
    resolved_bat = A_BAT.resolve_to_evm_token()
    bat_custom = globaldb.get_evm_token(address=resolved_bat.evm_address, chain_id=ChainID.ETHEREUM)  # noqa: E501
    bat_custom = EvmToken.initialize(
        address=resolved_bat.evm_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=resolved_bat.decimals,
        name=resolved_bat.name,
        symbol=resolved_bat.symbol,
        started=resolved_bat.started,
        swapped_for=asset_to_delete,
        coingecko=resolved_bat.coingecko,
        cryptocompare=resolved_bat.cryptocompare,
        protocol=None,
        underlying_tokens=None,
    )
    with pytest.raises(InputError):
        globaldb.edit_evm_token(bat_custom)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_check_asset_exists(globaldb):
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='1',
        asset_type=AssetType.OWN_CHAIN,
        name='Lolcoin',
        symbol='LOLZ',
        started=0,
    ))
    globaldb.add_asset(FiatAsset.initialize(
        identifier='2',
        name='Lolcoin',
        symbol='LOLZ',
    ))
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='3',
        asset_type=AssetType.OMNI_TOKEN,
        name='Lolcoin',
        symbol='LOLZ',
        started=0,
    ))
    assert not globaldb.check_asset_exists(CryptoAsset.initialize(identifier='foo', asset_type=AssetType.TRON_TOKEN, name='foo', symbol='FOO'))  # noqa: E501
    assert not globaldb.check_asset_exists(CryptoAsset.initialize(identifier='foo', asset_type=AssetType.TRON_TOKEN, name='Lolcoin', symbol='LOLZ'))  # noqa: E501
    assert globaldb.check_asset_exists(FiatAsset.initialize(identifier='lolcoin', name='Lolcoin', symbol='LOLZ')) == ['2']  # noqa: E501
    assert globaldb.check_asset_exists(CryptoAsset.initialize(identifier='lolz', asset_type=AssetType.OMNI_TOKEN, name='Lolcoin', symbol='LOLZ')) == ['3']  # noqa: E501

    # now add another asset already existing, but with different ID. See both returned
    globaldb.add_asset(FiatAsset.initialize(
        identifier='4',
        name='Euro',
        symbol='EUR',
    ))
    assert globaldb.check_asset_exists(FiatAsset.initialize(identifier='mieur', name='Euro', symbol='EUR')) == ['EUR', '4']  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_get_asset_with_symbol(globaldb):
    # both categories of assets
    asset_data = globaldb.get_assets_with_symbol('KEY')
    bihukey_address = string_to_evm_address('0x4Cd988AfBad37289BAAf53C13e98E2BD46aAEa8c')
    aave_address = string_to_evm_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9')
    renbtc_address = string_to_evm_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D')
    assert asset_data == [
        selfkey_asset,
        EvmToken.initialize(
            name='Bihu KEY',
            symbol='KEY',
            started=1507822985,
            forked=None,
            swapped_for=None,
            address=bihukey_address,
            chain_id=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            decimals=18,
            cryptocompare='BIHU',
            coingecko='key',
            protocol=None,
        ), CryptoAsset.initialize(
            identifier='KEY-3',
            name='KeyCoin',
            symbol='KEY',
            asset_type=AssetType.OWN_CHAIN,
            started=1405382400,
            forked=None,
            swapped_for=None,
            cryptocompare='KEYC',
            coingecko='',
        )]
    # only non-ethereum token
    assert globaldb.get_assets_with_symbol('BIDR') == [bidr_asset]
    # only ethereum token
    expected_assets = [EvmToken.initialize(
        name='Aave Token',
        symbol='AAVE',
        started=1600970788,
        forked=None,
        swapped_for=None,
        address=aave_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        cryptocompare=None,
        coingecko='aave',
        protocol=None,
    ), EvmToken.initialize(
        name='Aave (PoS)',
        symbol='AAVE',
        started=None,
        forked=None,
        swapped_for=None,
        address='0xD6DF932A45C0f255f85145f286eA0b292B21C90B',
        chain_id=ChainID.POLYGON_POS,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        cryptocompare='',
        coingecko='aave',
        protocol=None,
    ), EvmToken.initialize(
        name='Binance-Peg Aave Token',
        symbol='AAVE',
        started=Timestamp(1611903498),
        forked=None,
        swapped_for=None,
        address='0xfb6115445Bff7b52FeB98650C87f44907E58f802',
        chain_id=ChainID.BINANCE,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        cryptocompare='',
        coingecko='aave',
        protocol=None,
    )]
    assert globaldb.get_assets_with_symbol('AAVE') == expected_assets
    # finally non existing asset
    assert globaldb.get_assets_with_symbol('DASDSADSDSDSAD') == []

    # also check that symbol comparison is case insensitive for many arg combinations
    expected_renbtc = [EvmToken.initialize(
        name='renBTC',
        symbol='renBTC',
        started=1585090944,
        forked=None,
        swapped_for=None,
        address=renbtc_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=8,
        cryptocompare=None,
        coingecko='renbtc',
        protocol=None,
    ), EvmToken.initialize(
        name='renBTC',
        symbol='renBTC',
        started=None,
        forked=None,
        swapped_for=None,
        address='0xDBf31dF14B66535aF65AaC99C32e9eA844e14501',
        chain_id=ChainID.POLYGON_POS,
        token_kind=EvmTokenKind.ERC20,
        decimals=8,
        cryptocompare='',
        coingecko='renbtc',
        protocol=None,
    ), EvmToken.initialize(
        name='renBTC',
        symbol='renBTC',
        started=1605069649,
        forked=None,
        swapped_for=None,
        address='0xfCe146bF3146100cfe5dB4129cf6C82b0eF4Ad8c',
        chain_id=ChainID.BINANCE,
        token_kind=EvmTokenKind.ERC20,
        decimals=8,
        cryptocompare='',
        coingecko='renbtc',
        protocol=None,
    )]
    for x in itertools.product(('ReNbTc', 'renbtc', 'RENBTC', 'rEnBTc'), (None, AssetType.EVM_TOKEN)):  # noqa: E501
        assert globaldb.get_assets_with_symbol(*x) == expected_renbtc


@pytest.mark.parametrize(('enum_class', 'table_name'), [
    (AssetType, 'asset_types'),
    (HistoricalPriceOracle, 'price_history_source_types'),
])
def test_enum_values_are_present_in_global_db(globaldb, enum_class, table_name):
    """
    Check that all enum classes have the same number of possible values
    in the class definition as in the database
    """
    cursor = globaldb.conn.cursor()
    query = f'SELECT COUNT(*) FROM {table_name} WHERE seq=?'

    for enum_class_entry in enum_class:
        r = cursor.execute(query, (enum_class_entry.value,))
        assert r.fetchone() == (1,), f'Did not find {table_name} entry for value {enum_class_entry.value}'  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_get_all_asset_data_specific_ids(globaldb):
    btc_asset_data = AssetData(
        identifier='BTC',
        name='Bitcoin',
        symbol='BTC',
        asset_type=AssetType.OWN_CHAIN,
        started=Timestamp(1231006505),
        forked=None,
        swapped_for=None,
        address=None,
        chain_id=None,
        token_kind=None,
        decimals=None,
        cryptocompare=None,
        coingecko='bitcoin',
        protocol=None,
    )
    eth_asset_data = AssetData(
        identifier='ETH',
        name='Ethereum',
        symbol='ETH',
        asset_type=AssetType.OWN_CHAIN,
        started=Timestamp(1438214400),
        forked=None,
        swapped_for=None,
        address=None,
        chain_id=None,
        token_kind=None,
        decimals=None,
        cryptocompare=None,
        coingecko='ethereum',
        protocol=None,
    )

    asset_data = globaldb.get_all_asset_data(
        mapping=False,
        specific_ids=['BTC', 'ETH', selfkey_id, 'BIDR'],
    )
    assert asset_data == [
        selfkey_asset_data,
        bidr_asset_data,
        btc_asset_data,
        eth_asset_data,
    ]

    asset_data = globaldb.get_all_asset_data(
        mapping=True,
        serialized=True,
        specific_ids=['BTC', 'ETH', selfkey_id, 'BIDR'],
    )
    assert asset_data == {
        selfkey_id: selfkey_asset_data.serialize(),
        'BIDR': bidr_asset_data.serialize(),
        'BTC': btc_asset_data.serialize(),
        'ETH': eth_asset_data.serialize(),
    }
    asset_data = globaldb.get_all_asset_data(
        mapping=True,
        serialized=False,
        specific_ids=['BTC', 'ETH', selfkey_id, 'BIDR'],
    )
    assert asset_data == {
        selfkey_id: selfkey_asset_data,
        'BIDR': bidr_asset_data,
        'BTC': btc_asset_data,
        'ETH': eth_asset_data,
    }

    # unknown ids
    assert globaldb.get_all_asset_data(
        mapping=False,
        specific_ids=['INVALIDIDSS!@!1', 'DSAD#@$DSAD@EAS'],
    ) == []
    assert globaldb.get_all_asset_data(
        mapping=True,
        specific_ids=['INVALIDIDSS!@!1', 'DSAD#@$DSAD@EAS'],
    ) == {}

    # empty list
    assert globaldb.get_all_asset_data(
        mapping=False,
        specific_ids=[],
    ) == []
    assert globaldb.get_all_asset_data(
        mapping=True,
        specific_ids=[],
    ) == {}


def test_globaldb_pragma_foreign_keys(globaldb):
    """
    This tests verifies the behaviour of sqlite at the moment of
    activating and deactivating PRAGMA foreign_keys. As per what
    we could test and the documentation says for the change to
    take effect it needs that no transaction is pending.

    In this test we do:
    - Deactivate the check, insert assets and activate it again
    - Deactivate them and activate them again without pending transactions

    The reason for this test's existence is to verify our assumptions on sqlite
    and PRAGMAs and to check that they hold for the versions we use. If this test
    fails we know that something has changed and we will need to adjust our strategy.
    """
    cursor = globaldb.conn.cursor()
    cursor.switch_foreign_keys('OFF')
    cursor.execute('PRAGMA foreign_keys')
    # Now restrictions should be disabled
    assert cursor.fetchone()[0] == 0

    cursor.execute(
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES(
        "eip155:100/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6017", "A", "A",
        "0xD178b20c6007572bD1FD01D205cC20D32B4A6017", 18, NULL)
        """,
    )
    cursor.execute(
        """
        INSERT INTO assets(identifier, name, type) VALUES(
        "eip155:100/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6017", "Aidus", "C")
        """,
    )
    cursor.execute(
        """
        INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare,
        forked, started, swapped_for)
        VALUES("eip155:100/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6017",
        NULL, "AIDU", "", NULL, 123, NULL);
        """,
    )
    # activate them again
    cursor.switch_foreign_keys('ON')
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 1

    # deactivate them
    cursor.switch_foreign_keys('OFF')
    globaldb.conn.commit()
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 0
    cursor.switch_foreign_keys('ON')
    cursor.execute('PRAGMA foreign_keys')
    # Now restrictions should be enabled
    assert cursor.fetchone()[0] == 1


def test_global_db_restore(globaldb, database):
    """
    Check that the user can recreate assets information from the packaged
    database with rotki (hard reset). The test adds a new asset, restores
    the database and checks that the added token is not in there and that
    the amount of assets is the expected
    """
    # Add a custom eth token
    address_to_delete = make_evm_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    globaldb.add_asset(token_to_delete)
    # Add a token with underlying token
    with_underlying_address = make_evm_address()
    with_underlying = EvmToken.initialize(
        address=with_underlying_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Not a scam',
        symbol='NSCM',
        started=0,
        underlying_tokens=[UnderlyingToken(
            address=address_to_delete,
            token_kind=EvmTokenKind.ERC20,
            weight=1,
        )],
    )
    globaldb.add_asset(with_underlying)
    # Add asset that is not a token
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='1',
        asset_type=AssetType.OWN_CHAIN,
        name='Lolcoin',
        symbol='LOLZ',
        started=0,
    ))
    # Add asset that is not a token
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='2',
        asset_type=AssetType.OWN_CHAIN,
        name='Lolcoin2',
        symbol='LOLZ2',
        started=0,
    ))
    with database.user_write() as write_cursor:
        database.add_asset_identifiers(write_cursor, '1')
        database.add_asset_identifiers(write_cursor, '2')

    # Try to reset DB it if we have a trade that uses a custom asset
    buy_asset = symbol_to_asset_or_token('LOLZ2')
    buy_amount = deserialize_asset_amount(1)
    sold_asset = symbol_to_asset_or_token('LOLZ')
    sold_amount = deserialize_asset_amount(2)
    rate = Price(buy_amount / sold_amount)
    trade = Trade(
        timestamp=Timestamp(12312312),
        location=Location.BLOCKFI,
        base_asset=buy_asset,
        quote_asset=sold_asset,
        trade_type=TradeType.BUY,
        amount=buy_amount,
        rate=rate,
        fee=None,
        fee_currency=None,
        link='',
        notes='',
    )

    with database.user_write() as write_cursor:
        database.add_trades(write_cursor, [trade])
    status, _ = GlobalDBHandler().hard_reset_assets_list(database)
    assert status is False
    with database.user_write() as write_cursor:
        # Now do it without the trade
        database.delete_trades(write_cursor, [trade.identifier])
    status, msg = GlobalDBHandler().hard_reset_assets_list(database, True)
    assert status, msg
    cursor = globaldb.conn.cursor()
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Ethereum token should have been deleted'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Ethereum token should have been deleted from assets'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Token with underlying token should have been deleted from assets'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,)
    query = f'SELECT COUNT(*) FROM underlying_tokens_list where identifier == "{ethaddress_to_identifier(address_to_delete)}";'  # noqa: E501
    r = cursor.execute(query)
    assert r.fetchone() == (0,)
    query = 'SELECT COUNT(*) FROM assets where identifier == "1";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Non ethereum token should be deleted'
    # Check that the user database is correctly updated
    query = 'SELECT identifier from assets'
    r = cursor.execute(query)
    user_db_cursor = database.conn.cursor()
    user_db_cursor.execute(query)
    assert r.fetchall() == user_db_cursor.fetchall()

    # Check that the number of assets is the expected
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    builtin_database = root_dir / 'data' / 'global.db'
    conn = sqlite3.connect(builtin_database)
    cursor_clean_db = conn.cursor()
    tokens_expected = cursor_clean_db.execute('SELECT COUNT(*) FROM assets;')
    tokens_local = cursor.execute('SELECT COUNT(*) FROM assets;')
    assert tokens_expected.fetchone() == tokens_local.fetchone()
    cursor.execute('SELECT asset_id FROM user_owned_assets')
    msg = 'asset id in trade should not be in the owned table'
    assert "'2'" not in [entry[0] for entry in cursor.fetchall()], msg
    conn.close()


def test_global_db_reset(globaldb, database):
    """
    Check that the user can recreate assets information from the packaged
    database with rotki (soft reset). The test adds a new asset, restores
    the database and checks that the added tokens are still in the database.
    In addition a token is edited and we check that was correctly restored.
    """
    # Add a custom eth token
    address_to_delete = make_evm_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    globaldb.add_asset(token_to_delete)
    # Add a token with underlying token
    with_underlying_address = make_evm_address()
    with_underlying = EvmToken.initialize(
        address=with_underlying_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Not a scam',
        symbol='NSCM',
        started=0,
        underlying_tokens=[UnderlyingToken(
            address=address_to_delete,
            token_kind=EvmTokenKind.ERC20,
            weight=1,
        )],
    )
    globaldb.add_asset(with_underlying)
    # Add asset that is not a token
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='1',
        asset_type=AssetType.OWN_CHAIN,
        name='Lolcoin',
        symbol='LOLZ',
        started=0,
    ))
    # Edit one token
    one_inch_update = EvmToken.initialize(
        address='0x111111111117dC0aa78b770fA6A738034120C302',
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        name='1inch boi',
        symbol='1INCH',
        decimals=18,
    )
    GlobalDBHandler().edit_evm_token(one_inch_update)

    # Add some data to the tables that reference assets to make sure that it is not
    # touched by the reset
    historical_price = HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_DAI,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=1337,
        price=ONE,
    )
    GlobalDBHandler().add_single_historical_price(historical_price)
    GlobalDBHandler().add_user_owned_assets([A_ETH, A_DAI, A_CRV])
    db_custom_assets = DBCustomAssets(database)
    custom_asset = CustomAsset.initialize(
        identifier=str(uuid4()),
        name='My favorite lamborgini',
        custom_asset_type='Sport car',
        notes='It is so fast and so furious!',
    )
    db_custom_assets.add_custom_asset(custom_asset)
    with GlobalDBHandler().conn.write_ctx() as cursor:
        # TODO: when we fill data about collections into our packaged db, also add a check
        # that collections are properly reset.

        # Create a new collection
        cursor.execute(
            'INSERT INTO asset_collections (name, symbol) VALUES (?, ?)',
            ('New collection', 'NEWCOLLECTION'),
        )
        new_collection_id = cursor.lastrowid
        cursor.executemany(
            'INSERT INTO multiasset_mappings(collection_id, asset) VALUES (?, ?)',
            (
                (new_collection_id, A_CRV.identifier),  # put some assets into the new collection
                (new_collection_id, A_LUSD.identifier),
            ),
        )

        # Read original information from underlying tokens before the reset
        # get yDAI's underlying tokens
        ydai_underlying_tokens = cursor.execute(
            'SELECT * FROM underlying_tokens_list WHERE parent_token_entry=?',
            (A_yDAI.identifier,),
        ).fetchall()
        assert len(ydai_underlying_tokens) > 0
        # And put someting extra in there which should be deleted by the reset
        cursor.execute(
            'INSERT INTO underlying_tokens_list(identifier, weight, parent_token_entry) VALUES (?, ?, ?)',  # noqa: E501
            (A_CRV.identifier, '1.0', A_yDAI.identifier),
        )

    status, _ = GlobalDBHandler().soft_reset_assets_list()
    assert status
    cursor = globaldb.conn.cursor()
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Custom ethereum tokens should not been deleted'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Ethereum token with underlying token should not be deleted'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = f'SELECT COUNT(*) FROM underlying_tokens_list where identifier == "{ethaddress_to_identifier(address_to_delete)}";'  # noqa: E501
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = 'SELECT COUNT(*) FROM assets where identifier == "1";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Non ethereum token added should be in the db'
    # Check that the 1inch token was correctly fixed
    assert EvmToken('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302').name != '1inch boi'  # noqa: E501

    # Check that the number of assets is the expected
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    builtin_database = root_dir / 'data' / 'global.db'
    conn = sqlite3.connect(builtin_database)
    cursor_clean_db = conn.cursor()
    tokens_expected = cursor_clean_db.execute('SELECT COUNT(*) FROM assets;')
    tokens_local = cursor.execute('SELECT COUNT(*) FROM assets;')
    assert tokens_expected.fetchone()[0] + 4 == tokens_local.fetchone()[0]

    # Check that data that was not supposed to be reset was not touched
    historical_price_after_reset = GlobalDBHandler().get_historical_price(
        from_asset=historical_price.from_asset,
        to_asset=historical_price.to_asset,
        timestamp=historical_price.timestamp,
        max_seconds_distance=0,
    )
    assert historical_price_after_reset == historical_price
    expected_owned_assets = [(A_ETH.identifier,), (A_DAI.identifier,), (A_CRV.identifier,)]
    assert cursor.execute('SELECT * FROM user_owned_assets').fetchall() == expected_owned_assets
    entries, _, entries_total = db_custom_assets.get_custom_assets_and_limit_info(
        CustomAssetsFilterQuery.make(),
    )
    assert entries == [custom_asset]
    assert entries_total == 1

    # Check that manually added collection was not touched
    new_collection_after_reset = cursor.execute(
        'SELECT name, symbol FROM asset_collections WHERE id=?',
        (new_collection_id,),
    ).fetchall()
    assert new_collection_after_reset == [('New collection', 'NEWCOLLECTION')]
    new_collection_assets = cursor.execute(
        'SELECT asset FROM multiasset_mappings WHERE collection_id=?',
        (new_collection_id,),
    ).fetchall()
    assert new_collection_assets == [(A_CRV.identifier,), (A_LUSD.identifier,)]

    # Check that extra underlying token was deleted
    ydai_underlying_tokens_after_upgrade = cursor.execute(
        'SELECT * FROM underlying_tokens_list WHERE parent_token_entry=?',
        (A_yDAI.identifier,),
    ).fetchall()
    assert ydai_underlying_tokens_after_upgrade == ydai_underlying_tokens
    conn.close()


def test_add_user_owned_asset_nft(globaldb):
    """
    Test that adding an NFT user owned asset does not make it into the global DB.
    Otherwise a foreign key error will occur.
    """
    cursor = globaldb.conn.cursor()
    result = cursor.execute('SELECT asset_id FROM user_owned_assets').fetchall()
    initial_assets = {x[0] for x in result}

    globaldb.add_user_owned_assets([A_DAI])
    globaldb.add_user_owned_assets([
        A_PICKLE,
        Asset('_nft_0xfoo_24'),
        A_CRV,
        Asset('_nft_0xboo_2441'),
    ])

    result = cursor.execute('SELECT asset_id FROM user_owned_assets').fetchall()
    new_assets = {x[0] for x in result}
    assert new_assets - initial_assets == {A_DAI.identifier, A_PICKLE.identifier, A_CRV.identifier}
    assert all(not x.startswith(NFT_DIRECTIVE) for x in new_assets)


def test_asset_deletion(globaldb):
    """This test checks that deletion of both evm token and normal asset works as expected"""
    def check_tables(asset_id: str, expected_count: int, also_eth: bool):
        """Util function to check that data in the tables is correct. Checks that provided
        `asset_id` either exists or doesn't exist in all tables by comparing number of found
        entries with `expected_count` which should be either 1 or 0 respectively. If `also_eth`
        is True also checks evm-related tables (`evm_tokens` and `underlying_tokens_list`)."""
        queries = [
            'SELECT * FROM assets WHERE identifier=?',
            'SELECT * FROM common_asset_details WHERE identifier=?',
        ]
        if also_eth is True:
            queries += [
                'SELECT * FROM evm_tokens WHERE identifier=?',
                'SELECT * FROM underlying_tokens_list WHERE parent_token_entry=?',
            ]
        results = []
        with globaldb.conn.read_ctx() as cursor:
            for query in queries:
                res = cursor.execute(query, (asset_id,)).fetchall()
                results.append(len(res))

        assert all(x == expected_count for x in results)

    # Creating custom evm token to also check that underlying tokens are cleared
    token_data = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='a',
        name='b',
        decimals=0,
        underlying_tokens=[UnderlyingToken(
            address=make_evm_address(),
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
    )
    # Create token
    globaldb.add_asset(token_data)
    # Check that it was created
    check_tables(
        asset_id=token_data.identifier,
        expected_count=1,
        also_eth=True,
    )

    # Then delete this token
    GlobalDBHandler().delete_evm_token(
        address=token_data.evm_address,
        chain_id=ChainID.ETHEREUM,
    )
    # Check that it was deleted
    check_tables(
        asset_id=token_data.identifier,
        expected_count=0,
        also_eth=True,
    )

    asset_id = 'USD'
    # Check that asset exists
    check_tables(
        asset_id=asset_id,
        expected_count=1,
        also_eth=False,
    )
    # Delete asset
    GlobalDBHandler().delete_asset_by_identifier(identifier=asset_id)
    # Check that it was deleted properly
    check_tables(
        asset_id=asset_id,
        expected_count=0,
        also_eth=False,
    )


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_general_cache(globaldb):
    """
    Test that cache in the globaldb works properly. Tests insertion, deletion and reading.

    Used an older globalDB that is not pre-populated so that CURVE_POOLTOKENS and
    other flags are simpler to test.
    """

    ts_test_start = ts_now()
    with globaldb.conn.write_ctx() as write_cursor:
        # write some values
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
            values=['abc'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, '123'],
            values=['xyz', 'klm'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '123'],
            values=['abc', 'klm'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '456'],
            values=['def', 'klm'],
        )

    with GlobalDBHandler().conn.read_ctx() as cursor:
        # check that we can read saved values
        values_0 = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        )
        assert values_0 == ['abc']
        values_1 = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, '123'],
        )
        assert values_1 == ['klm', 'xyz']
        values_2 = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '123'],
        )
        assert values_2 == ['abc', 'klm']
        values_3 = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '456'],
        )
        assert values_3 == ['def', 'klm']
        values_4 = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, 'NO VALUE'],
        )
        assert len(values_4) == 0

        # check that timestamps were saved properly
        ts_test_end = ts_now()
        last_queried_ts_0 = globaldb_get_general_cache_last_queried_ts(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, '123'],
            value='xyz',
        )
        assert ts_test_end >= last_queried_ts_0 >= ts_test_start
        last_queried_ts_1 = globaldb_get_general_cache_last_queried_ts(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, '123'],
            value='NON-EXISTENT',
        )
        assert last_queried_ts_1 is None

    # check that deletion works properly
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '123'],
        )
        values_5 = globaldb_get_general_cache_values(
            cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '123'],
        )
        assert len(values_5) == 0
        values_6 = globaldb_get_general_cache_values(
            cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '456'],
        )
        assert len(values_6) == 2   # should have not been touched by the deletion above
        globaldb_delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '456'],
        )
        values_7 = globaldb_get_general_cache_values(
            cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, '456'],
        )
        assert len(values_7) == 0
        values_8 = globaldb_get_general_cache_values(
            cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, '123'],
        )
        assert values_8 == values_1


def test_edit_token_with_missing_information(database):
    """
    Test that editing a token that already exists with missing information doesn't
    raise any error and the information is updated
    """
    token_address = make_evm_address()
    peth = get_or_create_evm_token(
        userdb=database,
        symbol='IDONTEXIST',
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        evm_address=token_address,
    )
    assert peth.name == peth.identifier
    assert peth.decimals == 18

    # Querying adding missing key information should update the asset
    peth = get_or_create_evm_token(
        userdb=database,
        symbol='IDONTEXIST',
        name='IDONTEXIST NAME',
        decimals=18,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        evm_address=token_address,
    )
    assert peth.name == 'IDONTEXIST NAME'
    assert peth.decimals == 18


def test_packaged_db_check_for_constant_assets(globaldb):
    """Check that UnknownAsset & WrongAssetType is not raised for an asset in CONSTANT_ASSETS"""
    # delete one entry in `CONSTANT_ASSETS`
    with globaldb.conn.write_ctx() as cursor:
        cursor.execute('DELETE FROM assets WHERE identifier=?;', (A_LUSD.identifier,))
        assert cursor.rowcount == 1
    # now resolve the asset and check that no error is raised
    lusd = A_LUSD.resolve_to_evm_token()
    assert lusd.asset_type == AssetType.EVM_TOKEN
    assert lusd.identifier == A_LUSD.identifier

    # delete another asset and try checking its existence
    with globaldb.conn.write_ctx() as cursor:
        cursor.execute('DELETE FROM assets WHERE identifier=?;', (A_DAI.identifier, ))  # noqa: E501
        assert cursor.rowcount == 1
    # now check the asset type is correct and does not raise an error
    assert A_DAI.is_evm_token() is True

    # check that UnknownAsset is properly raised for an asset that does not
    # truly exist
    with pytest.raises(UnknownAsset):
        Asset('i-dont-exist').resolve()

    # check that if the type of asset is changed, resolving to the real type
    # does not raise a `WrongAssetType` exception
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('UPDATE assets SET type=? WHERE identifier=?;', (AssetType.FIAT.serialize_for_db(), A_DAI.identifier))  # noqa: E501
        cursor.execute('UPDATE assets SET type=? WHERE identifier=?;', (AssetType.EVM_TOKEN.serialize_for_db(), A_USD.identifier))  # noqa: E501
        assert cursor.rowcount == 1

    dai = A_DAI.resolve_to_evm_token()
    usd = A_USD.resolve_to_fiat_asset()
    assert dai.asset_type == AssetType.EVM_TOKEN
    assert dai.identifier == A_DAI.identifier
    assert usd.identifier == A_USD.identifier
    assert usd.asset_type == AssetType.FIAT

    # check that the information was correctly updated locally
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT type FROM assets WHERE identifier=?;', (A_DAI.identifier,))  # noqa: E501
        assert AssetType.deserialize_from_db(cursor.fetchone()[0]) == AssetType.EVM_TOKEN
        cursor.execute('SELECT type FROM assets WHERE identifier=?;', (A_USD.identifier,))  # noqa: E501
        assert AssetType.deserialize_from_db(cursor.fetchone()[0]) == AssetType.FIAT
        cursor.execute('SELECT type FROM assets WHERE identifier=?;', (A_LUSD.identifier,))  # noqa: E501
        assert AssetType.deserialize_from_db(cursor.fetchone()[0]) == AssetType.EVM_TOKEN


def test_get_assets_missing_information_by_symbol(globaldb):
    """
    Verify that querying assets by symbol doesn't raise error if any of the
    assets have missing information
    """
    token_address = string_to_evm_address('0x3031745E732dcE8fECccc94AcA13D5fa18F1012d')
    token = EvmToken.initialize(
        address=token_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name=None,
        symbol='BPTTT',
    )
    globaldb.add_asset(token)

    assets = globaldb.get_assets_with_symbol('BPTTT')
    assert assets[0].name == token.identifier
    token = EvmToken.initialize(
        address=token_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Test token',
        symbol='BPTTT',
    )
    globaldb.edit_evm_token(token)
    assets = globaldb.get_assets_with_symbol('BPTTT')
    assert len(assets) == 1
    assert assets[0].name == 'Test token'


def test_for_spam_tokens(database: 'DBHandler', ethereum_inquirer) -> None:
    """Test different cases of spam assets that we already know"""
    # $ aavereward.com
    assert check_if_spam_token(EvmToken(ethaddress_to_identifier(string_to_evm_address('0x39cf57b4dECb8aE3deC0dFcA1E2eA2C320416288'))).symbol) is True  # noqa: E501
    # Visit https://op-reward.xyz and claim rewards
    assert check_if_spam_token(EvmToken(evm_address_to_identifier(address='0x168fbA6072EE467931484a418EDeb5FcC1B9fb79', chain_id=ChainID.OPTIMISM, token_type=EvmTokenKind.ERC20)).symbol) is True  # noqa: E501
    # $ USDCGift.com <- Visit to claim bonus
    assert check_if_spam_token(EvmToken(ethaddress_to_identifier(string_to_evm_address('0x68Ca006dB91312Cd60a2238Ce775bE5F9f738bBa'))).symbol) is True  # noqa: E501
    # test adding now $RPL Claim at RPoolBonus.com
    token = get_or_create_evm_token(
        userdb=database,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        evm_address=string_to_evm_address('0x245151454C790EB870498e9E5B590145fAC1463F'),
        evm_inquirer=ethereum_inquirer,
    )
    assert token.protocol == SPAM_PROTOCOL
    with database.conn.read_ctx() as cursor:
        assert token.identifier in database.get_ignored_asset_ids(cursor)


def test_get_evm_tokens(globaldb):
    tokens = globaldb.get_evm_tokens(chain_id=ChainID.POLYGON_POS)
    assert tokens and not any(token.protocol == SPAM_PROTOCOL for token in tokens)
    assert all(token.chain_id == ChainID.POLYGON_POS for token in tokens)
    tokens = globaldb.get_evm_tokens(chain_id=ChainID.POLYGON_POS, ignore_spam=False)
    assert tokens and any(token.protocol == SPAM_PROTOCOL for token in tokens)

    tokens = globaldb.get_evm_tokens(chain_id=ChainID.ETHEREUM, protocol=CPT_COMPOUND)
    assert tokens and all(token.protocol == CPT_COMPOUND for token in tokens)
    tokens_without_exception = len(tokens)
    exception_address = tokens[0].evm_address
    tokens = globaldb.get_evm_tokens(chain_id=ChainID.ETHEREUM, protocol=CPT_COMPOUND, exceptions=(exception_address,))  # noqa: E501
    assert len(tokens) == tokens_without_exception - 1
    assert not any(token.evm_address == exception_address for token in tokens)
