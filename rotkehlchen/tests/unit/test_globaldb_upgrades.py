import pytest

from rotkehlchen.assets.typing import AssetType
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ethaddress_to_identifier,
    strethaddress_to_identifier,
)


@pytest.mark.parametrize('globaldb_version', [1])
def test_upgrade_v1_v2(globaldb):
    # at this point upgrade should have happened
    assert globaldb.get_setting_value('version', None) == 2

    for identifier, entry in globaldb.get_all_asset_data(mapping=True, serialized=False).items():
        if entry.asset_type == AssetType.ETHEREUM_TOKEN:
            assert identifier == ethaddress_to_identifier(entry.ethereum_address)

        swapped_for = entry.swapped_for

        # check the swapped_for key also changed for one we know
        if entry.name == 'Aurora DAO':
            assert entry.swapped_for == strethaddress_to_identifier('0xB705268213D593B8FD88d3FDEFF93AFF5CbDcfAE')  # noqa: E501

        if swapped_for and swapped_for not in ('AM', 'PHB', 'FIRO', 'DIVI', 'SCRT', 'HAI', 'MED', 'NOAHP', 'VET', 'XDC'):  # noqa: E501
            assert entry.swapped_for.startswith(ETHEREUM_DIRECTIVE)

    # Check some swapped for that we know should have changed. DIVX -> DIVI
    asset_data = globaldb.get_asset_data(strethaddress_to_identifier('0x13f11C9905A08ca76e3e853bE63D4f0944326C72'), form_with_incomplete_data=True)  # noqa: E501
    assert asset_data.swapped_for == 'DIVI'
    # GNT -> GLM
    asset_data = globaldb.get_asset_data(strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d'), form_with_incomplete_data=True)  # noqa: E501
    assert asset_data.swapped_for == strethaddress_to_identifier('0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429')  # noqa: E501

    # Make sure the number of assets remained the same
    cursor = globaldb._conn.cursor()
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
        ('_ceth_0x35bD01FC9d6D5D81CA9E055Db88Dc49aa2c699A8',
         '_ceth_0xBBc2AE13b23d715c30720F079fcd9B4a74093505',
         '_ceth_0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B',
         '_ceth_0x647C4CD779043b3f00a4ccdec550F35Dd18792b3',
         ),
    )
    assert query.fetchone()[0] == 4
    query = cursor.execute(
        'SELECT COUNT(*) from ethereum_tokens where address IN (?, ?, ?, ?);',
        ('0x35bD01FC9d6D5D81CA9E055Db88Dc49aa2c699A8',
         '0xBBc2AE13b23d715c30720F079fcd9B4a74093505',
         '0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B',
         '0x647C4CD779043b3f00a4ccdec550F35Dd18792b3',
         ),
    )
    assert query.fetchone()[0] == 4
