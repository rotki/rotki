import itertools

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.typing import AssetData, AssetType
from rotkehlchen.chain.ethereum.typing import CustomEthereumToken, string_to_ethereum_address
from rotkehlchen.constants.assets import A_BAT
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors import InputError
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.globaldb import INITIAL_TOKENS
from pathlib import Path
from rotkehlchen.assets.resolver import AssetResolver
from shutil import copyfile
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION
from rotkehlchen.tests.fixtures.globaldb import create_globaldb


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_get_ethereum_token_identifier(globaldb):
    assert globaldb.get_ethereum_token_identifier('0xnotexistingaddress') is None
    token_0_id = globaldb.get_ethereum_token_identifier(INITIAL_TOKENS[0].address)
    assert token_0_id == ethaddress_to_identifier(INITIAL_TOKENS[0].address)


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
    # need to obtain a valid CustomEthereumToken object
    address_to_delete = make_ethereum_address()
    token_to_delete = CustomEthereumToken(
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
            data=CustomEthereumToken(
                address=make_ethereum_address(),
                swapped_for=asset_to_delete,
            ),
        )

    # now edit a new token with swapped_for pointing to a non existing token in the DB
    bat_custom = A_BAT.to_custom_ethereum_token()
    bat_custom = CustomEthereumToken(
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
    selfkey_address = string_to_ethereum_address('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7')
    bihukey_address = string_to_ethereum_address('0x4Cd988AfBad37289BAAf53C13e98E2BD46aAEa8c')
    aave_address = string_to_ethereum_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9')
    renbtc_address = string_to_ethereum_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D')
    assert asset_data == [AssetData(
        identifier=ethaddress_to_identifier(selfkey_address),
        name='Selfkey',
        symbol='KEY',
        asset_type=AssetType.ETHEREUM_TOKEN,
        started=1508803200,
        forked=None,
        swapped_for=None,
        ethereum_address=selfkey_address,
        decimals=18,
        cryptocompare=None,
        coingecko='selfkey',
        protocol=None,
    ), AssetData(
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
    assert globaldb.get_assets_with_symbol('BIDR') == [AssetData(
        identifier='BIDR',
        name='Binance IDR Stable Coin',
        symbol='BIDR',
        asset_type=AssetType.BINANCE_TOKEN,
        started=1593475200,
        forked=None,
        swapped_for=None,
        ethereum_address=None,
        decimals=None,
        cryptocompare=None,
        coingecko='binanceidr',
        protocol=None,
    )]
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
