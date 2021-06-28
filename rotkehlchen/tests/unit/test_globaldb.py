import itertools
from pathlib import Path
from shutil import copyfile

import pytest

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.typing import AssetData, AssetType
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.assets import A_BAT
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors import InputError
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.globaldb import INITIAL_TOKENS
from rotkehlchen.typing import Timestamp

selfkey_address = string_to_ethereum_address('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7')
selfkey_id = ethaddress_to_identifier(selfkey_address)
selfkey_asset_data = AssetData(
    identifier=selfkey_id,
    name='Selfkey',
    symbol='KEY',
    asset_type=AssetType.ETHEREUM_TOKEN,
    started=Timestamp(1508803200),
    forked=None,
    swapped_for=None,
    ethereum_address=selfkey_address,
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
    ethereum_address=None,
    decimals=None,
    cryptocompare=None,
    coingecko='binanceidr',
    protocol=None,
)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_get_ethereum_token_identifier(globaldb):
    assert globaldb.get_ethereum_token_identifier('0xnotexistingaddress') is None
    token_0_id = globaldb.get_ethereum_token_identifier(INITIAL_TOKENS[0].ethereum_address)
    assert token_0_id == ethaddress_to_identifier(INITIAL_TOKENS[0].ethereum_address)


def test_open_new_globaldb_with_old_rotki(tmpdir_factory):
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
        create_globaldb(new_data_dir)

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
    # need to obtain a valid EthereumToken object
    address_to_delete = make_ethereum_address()
    token_to_delete = EthereumToken.initialize(
        address=address_to_delete,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    token_to_delete_id = 'DELMEID1'
    globaldb.add_asset(
        asset_id=token_to_delete_id,
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_to_delete,
    )
    asset_to_delete = Asset(token_to_delete_id)
    assert globaldb.delete_ethereum_token(address_to_delete) == token_to_delete_id

    # now try to add a new token with swapped_for pointing to a non existing token in the DB
    with pytest.raises(InputError):
        globaldb.add_asset(
            asset_id='NEWID',
            asset_type=AssetType.ETHEREUM_TOKEN,
            data=EthereumToken.initialize(
                address=make_ethereum_address(),
                swapped_for=asset_to_delete,
            ),
        )

    # now edit a new token with swapped_for pointing to a non existing token in the DB
    bat_custom = globaldb.get_ethereum_token(A_BAT.ethereum_address)
    bat_custom = EthereumToken.initialize(
        address=A_BAT.ethereum_address,
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
        globaldb.edit_ethereum_token(bat_custom)


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
    bihukey_address = string_to_ethereum_address('0x4Cd988AfBad37289BAAf53C13e98E2BD46aAEa8c')
    aave_address = string_to_ethereum_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9')
    renbtc_address = string_to_ethereum_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D')
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
            ethereum_address=bihukey_address,
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
            ethereum_address=None,
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
        ethereum_address=aave_address,
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
        ethereum_address=renbtc_address,
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
    cursor = globaldb._conn.cursor()
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
        ethereum_address=None,
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
        ethereum_address=None,
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
    cursor = globaldb._conn.cursor()
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
    globaldb._conn.commit()
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
