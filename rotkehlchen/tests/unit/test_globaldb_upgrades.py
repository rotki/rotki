import pytest

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE, ChainID
from rotkehlchen.globaldb.upgrades.v1_v2 import upgrade_ethereum_asset_ids
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind


def _old_ethaddress_to_identifier(address: ChecksumEvmAddress) -> str:
    return ETHEREUM_DIRECTIVE + address


def _old_strethaddress_to_identifier(address: str) -> str:
    return ETHEREUM_DIRECTIVE + address


@pytest.mark.parametrize('globaldb_version', [1])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reaload_custom_assets', [False])
@pytest.mark.parametrize('db_upgrades', [{1: upgrade_ethereum_asset_ids}])
def test_upgrade_v1_v2(globaldb):
    # at this point upgrade should have happened
    assert globaldb.get_setting_value('version', None) == 2
    query_assets_info_v2 = """SELECT A.identifier, A.type, B.address, A.name, A.swapped_for from
    assets as A LEFT OUTER JOIN ethereum_tokens as B ON B.address = A.details_reference
    WHERE A.type='C' UNION ALL
    SELECT A.identifier, A.type, null, A.name, A.swapped_for from assets as A LEFT OUTER JOIN
    common_asset_details as B ON B.asset_id = A.identifier WHERE A.type!='C';
    """
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(query_assets_info_v2)
        for identifier, asset_type, address, name, swapped_for in cursor:
            if AssetType.deserialize_from_db(asset_type) == AssetType.EVM_TOKEN:
                assert identifier == _old_ethaddress_to_identifier(address)

            # check the swapped_for key also changed for one we know
            if name == 'Aurora DAO':
                assert swapped_for == _old_strethaddress_to_identifier('0xB705268213D593B8FD88d3FDEFF93AFF5CbDcfAE')  # noqa: E501

            if swapped_for and swapped_for not in ('AM', 'PHB', 'FIRO', 'DIVI', 'SCRT', 'HAI', 'MED', 'NOAHP', 'VET', 'XDC'):  # noqa: E501
                assert swapped_for.startswith(ETHEREUM_DIRECTIVE)

        # Check some swapped for that we know should have changed. DIVX -> DIVI
        cursor.execute('SELECT swapped_for from ASSETS where identifier=?', (_old_strethaddress_to_identifier('0x13f11C9905A08ca76e3e853bE63D4f0944326C72'),))  # noqa: E501
        assert cursor.fetchone()[0] == 'DIVI'
        # GNT -> GLM
        cursor.execute('SELECT swapped_for from ASSETS where identifier=?', (_old_strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d'),))  # noqa: E501
        assert cursor.fetchone()[0] == _old_strethaddress_to_identifier('0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429')  # noqa: E501

        # Make sure the number of assets remained the same
        cursor = globaldb.conn.cursor()
        assert cursor.execute('SELECT COUNT(*) from assets').fetchone()[0] == 1886
        assert cursor.execute('SELECT COUNT(*) from user_owned_assets').fetchone()[0] == 105
        # Make sure that populated underlying assets are still there
        query = cursor.execute('SELECT * from underlying_tokens_list;')
        assert query.fetchall() == [
            ('0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B', '0.5', '0xBBc2AE13b23d715c30720F079fcd9B4a74093505'),  # noqa: E501
            ('0x647C4CD779043b3f00a4ccdec550F35Dd18792b3', '0.5', '0xBBc2AE13b23d715c30720F079fcd9B4a74093505'),  # noqa: E501
        ]
        # Make sure that the previous custom assets are still in the DB
        query = cursor.execute(
            'SELECT COUNT(*) from assets where identifier IN (?, ?, ?, ?);',
            (
                '_ceth_0x35bD01FC9d6D5D81CA9E055Db88Dc49aa2c699A8',
                '_ceth_0xBBc2AE13b23d715c30720F079fcd9B4a74093505',
                '_ceth_0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B',
                '_ceth_0x647C4CD779043b3f00a4ccdec550F35Dd18792b3',
            ),
        )
        assert query.fetchone()[0] == 4
        query = cursor.execute(
            'SELECT COUNT(*) from ethereum_tokens where address IN (?, ?, ?, ?);',
            (
                '0x35bD01FC9d6D5D81CA9E055Db88Dc49aa2c699A8',
                '0xBBc2AE13b23d715c30720F079fcd9B4a74093505',
                '0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B',
                '0x647C4CD779043b3f00a4ccdec550F35Dd18792b3',
            ),
        )
        assert query.fetchone()[0] == 4


@pytest.mark.parametrize('globaldb_version', [2])
@pytest.mark.parametrize('target_globaldb_version', [3])
def test_upgrade_v2_v3(globaldb):
    # at this point upgrade should have happened
    assert globaldb.get_setting_value('version', None) == 3
    with globaldb.conn.read_ctx() as cursor:
        # test that we have the same number of assets before and after the migration
        # 367 are the new assets from other chains that are evm and currently they are
        # marked with the OTHER asset type or that are missing the different chains versions.
        # 38 are the assets with type OTHER that will be replaced
        assert cursor.execute('SELECT COUNT(*) from assets').fetchone()[0] == 3095 + 367 - 38

        # Check that the properties of LUSD (ethereum token) have been correctly translated
        weth_token_data = cursor.execute('SELECT identifier, token_kind, chain, address, decimals, protocol FROM evm_tokens WHERE address = "0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert weth_token_data[0] == 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert EvmTokenKind.deserialize_from_db(weth_token_data[1]) == EvmTokenKind.ERC20
        assert ChainID.deserialize_from_db(weth_token_data[2]) == ChainID.ETHEREUM
        assert weth_token_data[3] == '0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert weth_token_data[4] == 18
        assert weth_token_data[5] is None
        weth_asset_data = cursor.execute('SELECT name, symbol, coingecko, cryptocompare, forked FROM common_asset_details WHERE identifier = "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'LUSD Stablecoin'
        assert weth_asset_data[1] == 'LUSD'
        assert weth_asset_data[2] == 'liquity-usd'
        assert weth_asset_data[3] == 'LUSD'
        assert weth_asset_data[4] is None
        weth_asset_data = cursor.execute('SELECT type, started, swapped_for FROM assets WHERE identifier = "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert AssetType.deserialize_from_db(weth_asset_data[0]) == AssetType.EVM_TOKEN
        assert weth_asset_data[1] == 1617611299
        assert weth_asset_data[2] is None

        # Check that a normal asset also gets correctly mapped
        weth_asset_data = cursor.execute('SELECT name, symbol, coingecko, cryptocompare, forked FROM common_asset_details WHERE identifier = "BCH"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'Bitcoin Cash'
        assert weth_asset_data[1] == 'BCH'
        assert weth_asset_data[2] == 'bitcoin-cash'
        assert weth_asset_data[3] is None
        assert weth_asset_data[4] == 'BTC'
        weth_asset_data = cursor.execute('SELECT type, started, swapped_for FROM assets WHERE identifier = "BCH"').fetchone()  # noqa: E501
        assert AssetType.deserialize_from_db(weth_asset_data[0]) == AssetType.OWN_CHAIN
        assert weth_asset_data[1] == 1501593374
        assert weth_asset_data[2] is None

        ids_in_db = {row[0] for row in cursor.execute('SELECT * FROM user_owned_assets')}
        assert ids_in_db == {
            'eip155:1/erc20:0x4E15361FD6b4BB609Fa63C81A2be19d873717870',
            'eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5',
            'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0',
            'BTC',
            'ETH',
            'USD',
            'EUR',
            'BCH',
        }
