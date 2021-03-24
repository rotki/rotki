import pytest

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE


@pytest.mark.parametrize('globaldb_version', [1])
def test_upgrade_v1_v2(globaldb):
    # at this point upgrade should have happened
    assert globaldb.get_setting_value('version', None) == 2

    for identifier, entry in globaldb.get_all_asset_data(mapping=True).items():
        if entry['asset_type'] == 'ethereum token':
            assert identifier == ETHEREUM_DIRECTIVE + entry['ethereum_address']

        swapped_for = entry['swapped_for']

        # check the swapped_for key also changed for one we know
        if entry['name'] == 'Aurora DAO':
            assert entry['swapped_for'] == ETHEREUM_DIRECTIVE + '0xB705268213D593B8FD88d3FDEFF93AFF5CbDcfAE'  # noqa: E501

        if swapped_for and swapped_for not in ('AM', 'PHB', 'FIRO', 'DIVI', 'SCRT', 'HAI', 'MED', 'NOAHP', 'VET', 'XDC'):  # noqa: E501
            assert entry['swapped_for'].startswith(ETHEREUM_DIRECTIVE)

    cursor = globaldb._conn.cursor()
    assert cursor.execute('SELECT COUNT(*) from assets').fetchone() == 1886
    assert cursor.execute('SELECT COUNT(*) from user_owned_assets').fetchone() == 105
    query = cursor.execute('SELECT * from underlying_tokens_list;')
    assert query.fetchall() == [
        ('0x42Fa37aC7c115bf17ca5DDfcb94b73b91B10B61B', '0.5', '0xBBc2AE13b23d715c30720F079fcd9B4a74093505'),  # noqa: E501
        ('0x647C4CD779043b3f00a4ccdec550F35Dd18792b3', '0.5', '0xBBc2AE13b23d715c30720F079fcd9B4a74093505'),  # noqa: E501
    ]
