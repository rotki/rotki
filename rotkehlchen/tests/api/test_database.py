import filecmp
import tempfile
from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.constants.misc import USERDB_NAME, USERSDIR_NAME
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('start_with_logged_in_user', [True, False])
def test_query_db_info(
        rotkehlchen_api_server: APIServer,
        data_dir: Path,
        username: str,
        start_with_logged_in_user: bool,
) -> None:
    """Test that retrieving user and global database details works fine"""
    users_dir = data_dir / USERSDIR_NAME
    if start_with_logged_in_user:
        backup1 = users_dir / username / '1624053928_rotkehlchen_db_v26.backup'
        backup1_contents = 'bla bla'
        backup1.write_text(backup1_contents)
        backup2 = users_dir / username / '1626382287_rotkehlchen_db_v27.backup'
        backup2_contents = 'i am a bigger amount of text'
        backup2.write_text(backup2_contents)
        (users_dir / username / '1633042045_rotkehlchen_db_v28.backup').touch()

    if start_with_logged_in_user:
        db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
        db.conn.wal_checkpoint()  # flush the wal file

    response = requests.get(api_url_for(rotkehlchen_api_server, 'databaseinforesource'))
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 2
    assert result['globaldb'] == {'globaldb_assets_version': 36, 'globaldb_schema_version': 13}

    if start_with_logged_in_user:
        userdb = result['userdb']
        assert userdb['info']['filepath'] == str(users_dir / username / USERDB_NAME)
        assert userdb['info']['size'] >= 300000  # just from comparison at tests
        assert userdb['info']['version'] == ROTKEHLCHEN_DB_VERSION
        assert len(userdb['backups']) == 3
        assert {'size': len(backup2_contents), 'time': 1626382287, 'version': 27} in userdb['backups']  # noqa: E501
        assert {'size': 0, 'time': 1633042045, 'version': 28} in userdb['backups']
        assert {'size': len(backup1_contents), 'time': 1624053928, 'version': 26} in userdb['backups']  # noqa: E501


def test_create_download_delete_backup(
        rotkehlchen_api_server: APIServer,
        data_dir: Path,
        username: str,
) -> None:
    """Test that creating, downloading and deleting a backup works fine"""
    start_ts = ts_now()
    response = requests.put(api_url_for(rotkehlchen_api_server, 'databasebackupsresource'))
    filepath = Path(assert_proper_sync_response_with_result(response))
    assert filepath.exists()
    assert filepath.parent == data_dir / USERSDIR_NAME / username

    response = requests.get(api_url_for(rotkehlchen_api_server, 'databaseinforesource'))
    result = assert_proper_sync_response_with_result(response)
    backups = result['userdb']['backups']
    assert len(backups) == 1
    assert backups[0]['time'] >= start_ts
    assert backups[0]['version'] == ROTKEHLCHEN_DB_VERSION

    # now also try to download that backup and make sure it's the same file
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'databasebackupsresource'),
        json={'file': str(filepath)},
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempdbpath = Path(tmpdirname, 'temp.db')
        tempdbpath.write_bytes(response.content)
        assert filecmp.cmp(filepath, tempdbpath)

    # create an extra database to check that lists work correctly
    second_filepath = filepath.parent / 'back.db'
    second_filepath.touch()

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'files': [str(filepath), str(second_filepath)]},
    )
    assert_simple_ok_response(response)
    assert not filepath.exists()
    assert not second_filepath.exists()
    response = requests.get(api_url_for(rotkehlchen_api_server, 'databaseinforesource'))
    result = assert_proper_sync_response_with_result(response)
    backups = result['userdb']['backups']
    assert len(backups) == 0


def test_delete_download_backup_errors(
        rotkehlchen_api_server: APIServer,
        data_dir: Path,
        username: str,
) -> None:
    """Test that errors are handled properly in backup deletion and download"""
    user_data_dir = Path(data_dir, username)
    # Make sure deleting file outside  of user data dir fails
    undeletable_file = Path(data_dir / 'notdeletablefile')
    undeletable_file.touch()
    assert undeletable_file.exists()
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'files': [str(undeletable_file)]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not in the user directory',
        status_code=HTTPStatus.CONFLICT,
    )
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'file': str(undeletable_file)},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not in the user directory',
        status_code=HTTPStatus.CONFLICT,
    )
    undeletable_file.unlink()  # finally delete normally

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'files': [str(Path(user_data_dir, 'idontexist'))]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='does not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'file': str(Path(user_data_dir, 'idontexist'))},
    )
    assert_error_response(
        response=response,
        contained_in_msg='does not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # test delete two files and only one exists
    undeletable_file.touch()
    response = requests.put(api_url_for(rotkehlchen_api_server, 'databasebackupsresource'))
    filepath = Path(assert_proper_sync_response_with_result(response))
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'databasebackupsresource'),
        json={'files': [str(undeletable_file), str(filepath)]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not in the user directory',
        status_code=HTTPStatus.CONFLICT,
    )
    assert undeletable_file.exists()
    assert filepath.exists()
