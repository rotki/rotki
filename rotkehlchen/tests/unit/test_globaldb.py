import itertools
import sqlite3
from pathlib import Path
from shutil import copyfile

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BAT, A_CRV, A_DAI, A_PICKLE
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.resolver import ChainID, ethaddress_to_identifier
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION, GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.globaldb import INITIAL_TOKENS
from rotkehlchen.types import EvmTokenKind, Location, Price, Timestamp, TradeType

selfkey_address = string_to_evm_address('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7')
selfkey_id = ethaddress_to_identifier(selfkey_address)
selfkey_asset_data = AssetData(
    identifier=selfkey_id,
    name='Selfkey',
    symbol='KEY',
    asset_type=AssetType.ETHEREUM_TOKEN,
    started=Timestamp(1508803200),
    forked=None,
    swapped_for=None,
    evm_address=selfkey_address,
    chain=ChainID.ETHEREUM,
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
    evm_address=None,
    chain=None,
    token_kind=None,
    decimals=None,
    cryptocompare=None,
    coingecko='binanceidr',
    protocol=None,
)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_get_ethereum_token_identifier(globaldb):
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_evm_token_identifier(
            cursor=cursor,
            address='0xnotexistingaddress',
            chain=ChainID.ETHEREUM,
        ) is None
        token_0_id = globaldb.get_evm_token_identifier(
            cursor=cursor,
            address=INITIAL_TOKENS[0].evm_address,
            chain=ChainID.ETHEREUM,
        )
    assert token_0_id == INITIAL_TOKENS[0].identifier


def test_open_new_globaldb_with_old_rotki(tmpdir_factory, sql_vm_instructions_cb):
    """Test for https://github.com/rotki/rotki/issues/2781"""
    # clean the previous resolver memory cache, as it
    # may have cached results from a discarded database
    AssetResolver().clean_memory_cache()
    version = 9999999999
    root_dir = Path(__file__).resolve().parent.parent.parent
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
    address_to_delete = make_ethereum_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    token_to_delete_id = token_to_delete.identifier
    globaldb.add_asset(
        asset_id=token_to_delete_id,
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_to_delete,
    )
    asset_to_delete = Asset(token_to_delete_id)
    with globaldb.conn.write_ctx() as cursor:
        assert globaldb.delete_evm_token(
            cursor,
            address=address_to_delete,
            chain=ChainID.ETHEREUM,
        ) == token_to_delete_id

    # now try to add a new token with swapped_for pointing to a non existing token in the DB
    with pytest.raises(InputError):
        globaldb.add_asset(
            asset_id='NEWID',
            asset_type=AssetType.ETHEREUM_TOKEN,
            data=EvmToken.initialize(
                address=make_ethereum_address(),
                chain=ChainID.ETHEREUM,
                token_kind=EvmTokenKind.ERC20,
                swapped_for=asset_to_delete,
            ),
        )

    # now edit a new token with swapped_for pointing to a non existing token in the DB
    bat_custom = globaldb.get_evm_token(address=A_BAT.evm_address, chain=ChainID.ETHEREUM)
    bat_custom = EvmToken.initialize(
        address=A_BAT.evm_address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=A_BAT.decimals,
        name=A_BAT.name,
        symbol=A_BAT.symbol,
        started=A_BAT.started,
        swapped_for=asset_to_delete,
        coingecko=A_BAT.coingecko,
        cryptocompare=A_BAT.cryptocompare,
        protocol=None,
        underlying_tokens=None,
    )
    with pytest.raises(InputError):
        globaldb.edit_evm_token(bat_custom)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_check_asset_exists(globaldb):
    globaldb.add_asset(
        asset_id='1',
        asset_type=AssetType.OWN_CHAIN,
        data={
            'name': 'Lolcoin',
            'symbol': 'LOLZ',
            'started': 0,
        },
    )
    globaldb.add_asset(
        asset_id='2',
        asset_type=AssetType.FIAT,
        data={
            'name': 'Lolcoin',
            'symbol': 'LOLZ',
            'started': 0,
        },
    )
    globaldb.add_asset(
        asset_id='3',
        asset_type=AssetType.OMNI_TOKEN,
        data={
            'name': 'Lolcoin',
            'symbol': 'LOLZ',
            'started': 0,
        },
    )

    assert not globaldb.check_asset_exists(AssetType.TRON_TOKEN, name='foo', symbol='FOO')
    assert not globaldb.check_asset_exists(AssetType.TRON_TOKEN, name='Lolcoin', symbol='LOLZ')
    assert globaldb.check_asset_exists(AssetType.FIAT, name='Lolcoin', symbol='LOLZ') == ['2']
    assert globaldb.check_asset_exists(AssetType.OMNI_TOKEN, name='Lolcoin', symbol='LOLZ') == ['3']  # noqa: E501

    # now add another asset already existing, but with different ID. See both returned
    globaldb.add_asset(
        asset_id='4',
        asset_type=AssetType.FIAT,
        data={
            'name': 'Euro',
            'symbol': 'EUR',
            'started': 0,
        },
    )
    assert globaldb.check_asset_exists(AssetType.FIAT, name='Euro', symbol='EUR') == ['EUR', '4']  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_get_asset_with_symbol(globaldb):
    # both categories of assets
    asset_data = globaldb.get_assets_with_symbol('KEY')
    bihukey_address = string_to_evm_address('0x4Cd988AfBad37289BAAf53C13e98E2BD46aAEa8c')
    aave_address = string_to_evm_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9')
    renbtc_address = string_to_evm_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D')
    assert asset_data == [
        selfkey_asset_data,
        AssetData(
            identifier=ethaddress_to_identifier(bihukey_address),
            name='Bihu KEY',
            symbol='KEY',
            asset_type=AssetType.ETHEREUM_TOKEN,
            started=1507822985,
            forked=None,
            swapped_for=None,
            evm_address=bihukey_address,
            chain=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            decimals=18,
            cryptocompare='BIHU',
            coingecko='key',
            protocol=None,
        ), AssetData(
            identifier='KEY-3',
            name='KeyCoin',
            symbol='KEY',
            asset_type=AssetType.OWN_CHAIN,
            started=1405382400,
            forked=None,
            swapped_for=None,
            evm_address=None,
            chain=None,
            token_kind=None,
            decimals=None,
            cryptocompare='KEYC',
            coingecko='',
            protocol=None,
        )]
    # only non-ethereum token
    assert globaldb.get_assets_with_symbol('BIDR') == [bidr_asset_data]
    # only ethereum token
    assert globaldb.get_assets_with_symbol('AAVE') == [AssetData(
        identifier=ethaddress_to_identifier(aave_address),
        name='Aave Token',
        symbol='AAVE',
        asset_type=AssetType.ETHEREUM_TOKEN,
        started=1600970788,
        forked=None,
        swapped_for=None,
        evm_address=aave_address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        cryptocompare=None,
        coingecko='aave',
        protocol=None,
    )]
    # finally non existing asset
    assert globaldb.get_assets_with_symbol('DASDSADSDSDSAD') == []

    # also check that symbol comparison is case insensitive for many arg combinations
    expected_renbtc = [AssetData(
        identifier=ethaddress_to_identifier(renbtc_address),
        name='renBTC',
        symbol='renBTC',
        asset_type=AssetType.ETHEREUM_TOKEN,
        started=1585090944,
        forked=None,
        swapped_for=None,
        evm_address=renbtc_address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=8,
        cryptocompare=None,
        coingecko='renbtc',
        protocol=None,
    )]
    for x in itertools.product(('ReNbTc', 'renbtc', 'RENBTC', 'rEnBTc'), (None, AssetType.ETHEREUM_TOKEN)):  # noqa: E501
        assert globaldb.get_assets_with_symbol(*x) == expected_renbtc


@pytest.mark.parametrize('enum_class, table_name', [
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
        evm_address=None,
        chain=None,
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
        evm_address=None,
        chain=None,
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
    - Start a transaction, check that the change doesn't take effect, commit
    and see that then it works.

    The reason for this test's existence is to verify our assumptions on sqlite
    and PRAGMAs and to check that they hold for the versions we use. If this test
    fails we know that something has changed and we will need to adjust our strategy.
    """
    cursor = globaldb.conn.cursor()
    cursor.execute('PRAGMA foreign_keys = OFF;')
    cursor.execute('PRAGMA foreign_keys')
    # Now restrictions should be disabled
    assert cursor.fetchone()[0] == 0

    cursor.execute(
        """
        INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES(
        "0xD178b20c6007572bD1FD01D205cC20D32B4A6017", 18, NULL
        );
        """,
    )
    cursor.execute(
        """
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6017", "C", "Aidus", "AID"   ,
        123, NULL,   NULL, "AIDU", "0xD178b20c6007572bD1FD01D205cC20D32B4A6017");
        """,
    )
    # activate them again should fail since we haven't finished
    cursor.execute('PRAGMA foreign_keys = ON;')
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 0
    # To change them again we have to commit the pending transaction
    cursor.execute('COMMIT;')
    # activate them again
    cursor.execute('PRAGMA foreign_keys = ON;')
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 1

    # deactivate them
    cursor.execute('PRAGMA foreign_keys = OFF;')
    globaldb.conn.commit()
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 0
    cursor.execute('PRAGMA foreign_keys = ON;')
    cursor.execute('PRAGMA foreign_keys')
    # Now restrictions should be enabled
    assert cursor.fetchone()[0] == 1

    # Start a transaction and they should fail to change to off
    # since the transaction hasn't finished
    cursor.execute('begin')
    cursor.execute('PRAGMA foreign_keys = OFF;')
    cursor.execute('PRAGMA foreign_keys')
    assert cursor.fetchone()[0] == 1
    # Finish the transaction
    cursor.execute('commit')
    cursor.execute('PRAGMA foreign_keys = OFF;')
    cursor.execute('PRAGMA foreign_keys')
    # Now the pragma should be off
    assert cursor.fetchone()[0] == 0


def test_global_db_restore(globaldb, database):
    """
    Check that the user can recreate assets information from the packaged
    database with rotki (hard reset). The test adds a new asset, restores
    the database and checks that the added token is not in there and that
    the amount of assets is the expected
    """
    # Add a custom eth token
    address_to_delete = make_ethereum_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    globaldb.add_asset(
        asset_id='DELMEID1',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_to_delete,
    )
    # Add a token with underlying token
    with_underlying_address = make_ethereum_address()
    with_underlying = EvmToken.initialize(
        address=with_underlying_address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name="Not a scam",
        symbol="NSCM",
        started=0,
        underlying_tokens=[UnderlyingToken(
            address=address_to_delete,
            weight=1,
        )],
    )
    globaldb.add_asset(
        asset_id='xDELMEID1',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=with_underlying,
    )
    # Add asset that is not a token
    globaldb.add_asset(
        asset_id='1',
        asset_type=AssetType.OWN_CHAIN,
        data={
            'name': 'Lolcoin',
            'symbol': 'LOLZ',
            'started': 0,
        },
    )

    # Add asset that is not a token
    globaldb.add_asset(
        asset_id='2',
        asset_type=AssetType.OWN_CHAIN,
        data={
            'name': 'Lolcoin2',
            'symbol': 'LOLZ2',
            'started': 0,
        },
    )

    with database.user_write() as cursor:
        database.add_asset_identifiers(cursor, '1')
        database.add_asset_identifiers(cursor, '2')

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
        notes="",
    )

    with database.user_write() as cursor:
        database.add_trades(cursor, [trade])
        status, _ = GlobalDBHandler().hard_reset_assets_list(database)
        assert status is False
        # Now do it without the trade
        database.delete_trade(cursor, trade.identifier)
    status, msg = GlobalDBHandler().hard_reset_assets_list(database, True)
    assert status, msg
    cursor = globaldb.conn.cursor()
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Ethereum token should have been deleted'
    query = f'SELECT COUNT(*) FROM assets where details_reference == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Ethereum token should have been deleted from assets'
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,), 'Token with underlying token should have been deleted from assets'
    query = f'SELECT COUNT(*) FROM assets where details_reference == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (0,)
    query = f'SELECT COUNT(*) FROM underlying_tokens_list where address == "{address_to_delete}";'
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
    root_dir = Path(__file__).resolve().parent.parent.parent
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


def test_global_db_reset(globaldb):
    """
    Check that the user can recreate assets information from the packaged
    database with rotki (soft reset). The test adds a new asset, restores
    the database and checks that the added tokens are still in the database.
    In addition a token is edited and we check that was correctly restored.
    """
    # Add a custom eth token
    address_to_delete = make_ethereum_address()
    token_to_delete = EvmToken.initialize(
        address=address_to_delete,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    globaldb.add_asset(
        asset_id='DELMEID1',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_to_delete,
    )
    # Add a token with underlying token
    with_underlying_address = make_ethereum_address()
    with_underlying = EvmToken.initialize(
        address=with_underlying_address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name="Not a scam",
        symbol="NSCM",
        started=0,
        underlying_tokens=[UnderlyingToken(
            address=address_to_delete,
            chain=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            weight=1,
        )],
    )
    globaldb.add_asset(
        asset_id='xDELMEID1',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=with_underlying,
    )
    # Add asset that is not a token
    globaldb.add_asset(
        asset_id='1',
        asset_type=AssetType.OWN_CHAIN,
        data={
            'name': 'Lolcoin',
            'symbol': 'LOLZ',
            'started': 0,
        },
    )
    # Edit one token
    one_inch_update = EvmToken.initialize(
        address='0x111111111117dC0aa78b770fA6A738034120C302',
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        name='1inch boi',
    )
    GlobalDBHandler().edit_evm_token(one_inch_update)

    status, _ = GlobalDBHandler().soft_reset_assets_list()
    assert status
    cursor = globaldb.conn.cursor()
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Custom ethereum tokens should not been deleted'
    query = f'SELECT COUNT(*) FROM assets where details_reference == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = f'SELECT COUNT(*) FROM evm_tokens where address == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Ethereum token with underlying token should not be deleted'
    query = f'SELECT COUNT(*) FROM assets where details_reference == "{with_underlying_address}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = f'SELECT COUNT(*) FROM underlying_tokens_list where address == "{address_to_delete}";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,)
    query = 'SELECT COUNT(*) FROM assets where identifier == "1";'
    r = cursor.execute(query)
    assert r.fetchone() == (1,), 'Non ethereum token added should be in the db'
    # Check that the 1inch token was correctly fixed
    assert EvmToken('0x111111111117dC0aa78b770fA6A738034120C302').name != '1inch boi'

    # Check that the number of assets is the expected
    root_dir = Path(__file__).resolve().parent.parent.parent
    builtin_database = root_dir / 'data' / 'global.db'
    conn = sqlite3.connect(builtin_database)
    cursor_clean_db = conn.cursor()
    tokens_expected = cursor_clean_db.execute('SELECT COUNT(*) FROM assets;')
    tokens_local = cursor.execute('SELECT COUNT(*) FROM assets;')
    assert tokens_expected.fetchone()[0] + 3 == tokens_local.fetchone()[0]
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
