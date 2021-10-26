from pathlib import Path

import pytest
import requests

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result


@pytest.mark.parametrize('start_with_logged_in_user', [True, False])
def test_query_db_info(rotkehlchen_api_server, data_dir, username, start_with_logged_in_user):
    if start_with_logged_in_user:
        backup1 = Path(data_dir / username / '1624053928_rotkehlchen_db_v26.backup')
        backup1_contents = 'bla bla'
        backup1.write_text(backup1_contents)
        backup2 = Path(data_dir / username / '1626382287_rotkehlchen_db_v27.backup')
        backup2_contents = 'i am a bigger amount of text'
        backup2.write_text(backup2_contents)
        Path(data_dir / username / '1633042045_rotkehlchen_db_v28.backup').touch()

    response = requests.get(api_url_for(rotkehlchen_api_server, 'databaseinforesource'))
    result = assert_proper_response_with_result(response)
    assert len(result) == 2
    assert result['globaldb'] == {'globaldb_assets_version': 10, 'globaldb_schema_version': 2}

    if start_with_logged_in_user:
        userdb = result['userdb']
        assert userdb['info']['filepath'] == f'{data_dir}/{username}/rotkehlchen.db'
        assert userdb['info']['size'] >= 300000  # just from comparison at tests
        assert userdb['info']['version'] == ROTKEHLCHEN_DB_VERSION
        assert len(userdb['backups']) == 3
        assert userdb['backups'][0] == {
            'size': len(backup2_contents), 'time': '1626382287', 'version': '27',
        }
        assert userdb['backups'][1] == {
            'size': 0, 'time': '1633042045', 'version': '28',
        }
        assert userdb['backups'][2] == {
            'size': len(backup1_contents), 'time': '1624053928', 'version': '26',
        }
