import os
import random
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pytest
import requests

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION, DBSettings
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_async_response,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.premium import (
    VALID_PREMIUM_KEY,
    VALID_PREMIUM_SECRET,
    create_patched_premium,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def check_proper_unlock_result(
        response_data: dict[str, Any],
        settings_to_check: Optional[dict[str, Any]] = None,
) -> None:

    assert isinstance(response_data['exchanges'], list)
    assert response_data['settings']['version'] == ROTKEHLCHEN_DB_VERSION
    for setting in DBSettings._fields:
        assert setting in response_data['settings']

    if settings_to_check is not None:
        for setting, value in settings_to_check.items():
            assert response_data['settings'][setting] == value


def check_user_status(api_server) -> dict[str, str]:
    # Check users status
    response = requests.get(
        api_url_for(api_server, 'usersresource'),
    )
    result = assert_proper_response_with_result(response)
    return result


def test_loggedin_user_querying(rotkehlchen_api_server, username, data_dir):
    """Start with a logged in user and make sure we can query all users"""
    Path(data_dir / 'another_user').mkdir()
    Path(data_dir / 'another_user' / 'rotkehlchen.db').touch()
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedin'
    assert result['another_user'] == 'loggedout'
    assert len(result) == 2


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_not_loggedin_user_querying(rotkehlchen_api_server, username, data_dir):
    """Start without logged in user and make sure we can query all users"""
    Path(data_dir / 'another_user').mkdir()
    Path(data_dir / 'another_user' / 'rotkehlchen.db').touch()
    Path(data_dir / username).mkdir(exist_ok=True)
    Path(data_dir / username / 'rotkehlchen.db').touch()

    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedout'
    assert result['another_user'] == 'loggedout'
    assert len(result) == 2


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation(rotkehlchen_api_server, data_dir):
    """Test that PUT at user endpoint can create a new user"""
    # Create a user without any premium credentials
    async_query = random.choice([False, True])
    username = 'hania'
    data = {'name': username, 'password': '1234', 'async_query': async_query}
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)

    if async_query is True:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    check_proper_unlock_result(result, {'submit_usage_analytics': True})

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 1

    # Check that the directory was created
    assert Path(data_dir / username / 'rotkehlchen.db').exists()


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_no_analytics(rotkehlchen_api_server, data_dir):
    """Test that providing specific settings at user creation works"""
    # Create a user without any premium credentials
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
        'initial_settings': {'submit_usage_analytics': False},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    result = assert_proper_response_with_result(response)
    check_proper_unlock_result(result, {'submit_usage_analytics': False})

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 1

    # Check that the directory was created
    assert Path(data_dir / username / 'rotkehlchen.db').exists()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_permission_error(rotkehlchen_api_server, data_dir):
    """Test that creating a user when data directory permissions are wrong is handled"""
    os.chmod(data_dir, 0o200)
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to create directory for user: [Errno 13] Permission denied',
        status_code=HTTPStatus.CONFLICT,
    )
    os.chmod(data_dir, 0o777)


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_premium_credentials(rotkehlchen_api_server, data_dir):
    """Test that PUT at user endpoint can create a new user"""
    # Create a user with premium credentials
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': VALID_PREMIUM_KEY,
        'premium_api_secret': VALID_PREMIUM_SECRET,
    }
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    patched_premium_at_start, _, patched_get = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        patch_get=True,
        metadata_last_modify_ts=0,
        metadata_data_hash=b'',
        metadata_data_size=0,
    )

    with patched_premium_at_start:
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    result = assert_proper_response_with_result(response)
    check_proper_unlock_result(result)

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 1

    # Check that the directory was created
    assert Path(data_dir / username / 'rotkehlchen.db').exists()

    # Check that the user has premium
    assert rotki.premium is not None
    assert rotki.premium.credentials.serialize_key() == VALID_PREMIUM_KEY
    assert rotki.premium.credentials.serialize_secret() == VALID_PREMIUM_SECRET
    with patched_get:
        assert rotki.premium.is_active()


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_invalid_premium_credentials(rotkehlchen_api_server, data_dir):
    """
    Test that invalid and unauthenticated premium credentials are handled at new user creation
    """
    # Create a user with invalid credentials
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': 'foo',
        'premium_api_secret': 'boo',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Provided API/Key secret format is invalid',
    )

    # Check that the directory was NOT created
    assert not Path(data_dir / username).exists(), 'The directory should not have been created'

    # Create a new user with valid but not authenticable credentials
    username = 'Anja'
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': VALID_PREMIUM_KEY,
        'premium_api_secret': VALID_PREMIUM_SECRET,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)

    expected_msg = (
        'Could not verify keys for the new account. rotki API key was rejected by server'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # Check that the directory was NOT created
    assert not Path(data_dir / username).exists(), 'The directory should not have been created'
    # But check that a backup of the directory was made just in case
    backups = list(Path(data_dir).glob('auto_backup_*'))
    assert len(backups) == 1
    assert 'auto_backup_Anja_' in str(backups[0]), 'An automatic backup should have been made'

    # But then try to create a normal-non premium user and see it works
    username = 'hania2'
    data = {
        'name': username,
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    result = assert_proper_response_with_result(response)
    check_proper_unlock_result(result)

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 2

    # Check that the directory was created
    assert Path(data_dir / username / 'rotkehlchen.db').exists()


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_errors(rotkehlchen_api_server: 'APIServer', data_dir: Path) -> None:
    """Test errors and edge cases for user creation"""
    # Missing username
    username = 'hania'
    data: dict[str, Any] = {
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )
    # Missing password
    username = 'hania'
    data = {
        'name': username,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )

    # Invalid type for name
    data = {
        'name': 5435345.31,
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )

    # Invalid type for password
    data = {
        'name': username,
        'password': 4535,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )

    # Provide only premium_api_key
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': 'asdsada',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Must provide both or neither of api key/secret',
    )
    # Provide only premium_api_secret
    data = {
        'name': username,
        'password': '1234',
        'premium_api_secret': 'asdsada',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Must provide both or neither of api key/secret',
    )
    # Invalid type for premium api key
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': True,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )
    # Invalid type for premium api secret
    data = {
        'name': username,
        'password': '1234',
        'premium_api_secret': 45.2,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )

    # Check that the directory was NOT created
    assert not Path(data_dir / username / 'rotkehlchen.db').exists()

    # Let's pretend there is another user, and try to create them again
    Path(data_dir / 'another_user').mkdir()
    Path(data_dir / 'another_user' / 'rotkehlchen.db').touch()
    data = {
        'name': 'another_user',
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='User another_user already exists',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that if there is an already logged in user it raises an error
    rotkehlchen_api_server.rest_api.rotkehlchen.user_is_logged_in = True
    rotkehlchen_api_server.rest_api.rotkehlchen.data.username = 'hania'
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Can not create a new user because user hania is already logged in. Log out of that user first',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )


def test_user_creation_with_already_loggedin_user(rotkehlchen_api_server, username):
    """Test that creating a user while another one is logged in fails"""
    # Missing username
    data = {
        'name': username,
        'password': '1234',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    msg = (
        f'Can not create a new user because user {username} is already logged in. '
        f'Log out of that user first'
    )
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.CONFLICT,
    )


def test_user_password_change(rotkehlchen_api_server, username, db_password):
    """
    Test that changing a logged-in user's users password works successfully and that
    common errors are handled. Also make sure logging in again with the new password works.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    new_password = 'asdf'
    # wrong username
    data_wrong_user = {
        'name': 'billybob',
        'current_password': 'asdf',
        'new_password': 'asdf',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'userpasswordchangeresource',
            name=username,
        ), json=data_wrong_user)
    msg = f'Provided user "{data_wrong_user["name"]}" is not the logged in user'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong password
    data_wrong_pass = {
        'name': username,
        'current_password': 'asdf',
        'new_password': 'asdf',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'userpasswordchangeresource',
            name=username,
        ), json=data_wrong_pass)
    msg = 'Provided current password is not correct'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.UNAUTHORIZED,
    )

    # now do change password
    data_success = {
        'name': username,
        'current_password': db_password,
        'new_password': new_password,
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'userpasswordchangeresource',
            name=username,
        ), json=data_success)
    assert_simple_ok_response(response)
    assert rotki.data.db.password == new_password

    # Logout
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False

    # And login with the new password to make sure it works
    data = {'password': new_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    check_proper_unlock_result(result)
    assert rotki.user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 1
    assert users_data[username] == 'loggedin'


def test_user_logout(rotkehlchen_api_server, username, db_password):
    """Test that user logout works succesfully and that common errors are handled"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Logout of a non-existing/different user
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name='nobody'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Provided user nobody is not the logged in user',
        status_code=HTTPStatus.CONFLICT,
    )
    assert rotki.user_is_logged_in is True

    # Logout of the active user
    assert rotki.data.db.password == db_password
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False
    assert rotki.data.db.password == ''

    # Now try to log out of the same user again
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='No user is currently logged in',
        status_code=HTTPStatus.CONFLICT,
    )
    assert rotki.user_is_logged_in is False


def test_user_login(rotkehlchen_api_server, username, db_password, data_dir):
    """Test that user login works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Let's pretend there is another user, and try to create them again
    Path(data_dir / 'another_user').mkdir()
    Path(data_dir / 'another_user' / 'rotkehlchen.db').touch()

    # Check users status
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'

    # Logout of the active user
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedout'
    assert users_data['another_user'] == 'loggedout'

    # Now let's try to login
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    # And make sure it works
    task_id = assert_ok_async_response(response)
    result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    check_proper_unlock_result(result)
    assert rotki.user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'

    # Logout again
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedout'
    assert users_data['another_user'] == 'loggedout'

    # Now try to login with a wrong password
    data = {'password': 'wrong_password', 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)
    # And make sure it fails
    assert_error_async_response(
        response_data=response_data,
        contained_in_msg='Wrong password or invalid/corrupt database for user',
        status_code=HTTPStatus.UNAUTHORIZED,
    )
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedout'
    assert users_data['another_user'] == 'loggedout'

    # Now let's manually add valid but not authenticable premium credentials in the DB
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id)
    credentials = PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET)
    rotki.data.db.set_rotkehlchen_premium(credentials)
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False
    # And try to login while having these unauthenticable premium credentials in the DB
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    # And make sure it works despite having unauthenticable premium credentials in the DB
    task_id = assert_ok_async_response(response)
    result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    check_proper_unlock_result(result)
    assert rotki.user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'


def test_user_set_premium_credentials(rotkehlchen_api_server, username):
    """Test that setting the premium credentials endpoint works.

    We mock the server accepting the premium credentials
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _, patched_premium_at_set, patched_get = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        patch_get=True,
        metadata_last_modify_ts=0,
        metadata_data_hash=b'',
        metadata_data_size=0,
    )

    # Set premium credentials for current user
    data = {'premium_api_key': VALID_PREMIUM_KEY, 'premium_api_secret': VALID_PREMIUM_SECRET}
    with patched_premium_at_set:
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
    assert_simple_ok_response(response)
    assert rotki.premium is not None
    assert rotki.premium.credentials.serialize_key() == VALID_PREMIUM_KEY
    assert rotki.premium.credentials.serialize_secret() == VALID_PREMIUM_SECRET
    with patched_get:
        assert rotki.premium.is_active()


def test_user_del_premium_credentials(rotkehlchen_api_server, username):
    """Test that removing the premium credentials endpoint works.

    We first set up mock the server accepting the premium credentials
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _, patched_premium_at_set, patched_get = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        patch_get=True,
        metadata_last_modify_ts=0,
        metadata_data_hash=b'',
        metadata_data_size=0,
    )

    # Set premium credentials for current user
    data = {'premium_api_key': VALID_PREMIUM_KEY, 'premium_api_secret': VALID_PREMIUM_SECRET}
    with patched_premium_at_set:
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
    with patched_get:
        assert rotki.premium.is_active()

    # Delete premium credentials for current user
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'userpremiumkeyresource',
                                           name=username))
    assert_simple_ok_response(response)
    assert rotki.premium is None
    assert rotki.premium_sync_manager.premium is None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_login_user_dir_permission_error(rotkehlchen_api_server, data_dir):
    """Test that user login with userdir path permission errors is handled properly"""
    username = 'a_user'
    user_dir = Path(data_dir / username)
    user_dir.mkdir()
    db_path = Path(data_dir / username / 'rotkehlchen.db')
    db_path.touch()
    os.chmod(user_dir, 0o200)

    data = {'password': '123', 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)

    assert_error_async_response(
        response_data=response_data,
        contained_in_msg=f'User {username} exists but DB is missing',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_login_db_permission_error(rotkehlchen_api_server, data_dir):
    """Test that user login with db path permission errors is handled properly"""
    username = 'a_user'
    user_dir = Path(data_dir / username)
    user_dir.mkdir()
    db_path = Path(data_dir / username / 'rotkehlchen.db')
    db_path.touch()
    os.chmod(db_path, 0o200)
    data = {'password': '123', 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_error_async_response(
        response_data=response_data,
        contained_in_msg='Could not open database file',
        status_code=HTTPStatus.CONFLICT,
    )
    os.chmod(db_path, 0o777)


def test_user_set_premium_credentials_errors(rotkehlchen_api_server, username):
    """Test that setting the premium credentials endpoint reacts properly to bad input"""
    # Set premium credentials for non-logged in user
    data = {'premium_api_key': 'dadssad', 'premium_api_secret': 'jhjhkh'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name='another_user'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Provided user another_user is not the logged in user',
        status_code=HTTPStatus.CONFLICT,
    )

    # Set valid format but not authenticated premium credentials for logged in user
    data = {'premium_api_key': VALID_PREMIUM_KEY, 'premium_api_secret': VALID_PREMIUM_SECRET}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='rotki API key was rejected by server',
        status_code=HTTPStatus.UNAUTHORIZED,
    )


def test_users_by_name_endpoint_errors(rotkehlchen_api_server, username, db_password):
    """Test that user by name endpoint errors are handled (for login/logout and edit)"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Now let's try to login while the user is already logged in
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)

    expected_msg = (
        f'Can not login to user {username} because user {username} is '
        f'already logged in. Log out of that user first'
    )
    assert_error_async_response(
        response_data=response_data,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    assert rotki.user_is_logged_in is True

    # Logout of the active user
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False

    # Now let's try to login with an invalid password
    data = {'password': 'wrong-password', 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)

    assert_error_async_response(
        response_data=response_data,
        contained_in_msg='Wrong password or invalid/corrupt database for user',
        status_code=HTTPStatus.UNAUTHORIZED,
    )
    assert rotki.user_is_logged_in is False

    # Login action without a password
    data = {'sync_approval': 'unknown'}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is False

    # Login first to test that schema validation works.
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id)
    assert rotki.user_is_logged_in is True

    # No action and no premium credentials
    data = {}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Without an action premium api key and secret must be provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True

    # No action and only premium key
    data = {'premium_api_key': VALID_PREMIUM_KEY}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Without an action premium api key and secret must be provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True

    # No action and only premium secret
    data = {'premium_api_secret': VALID_PREMIUM_SECRET}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Without an action premium api key and secret must be provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True

    # Invalid action type
    data = {'action': 555.3, 'premium_api_key': '123', 'premium_api_secret': '1'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True

    # Invalid action string
    data = {'action': 'chopwood', 'premium_api_key': '123', 'premium_api_secret': '1'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Must be equal to logout',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True

    # Invalid password type
    data = {'password': True, 'sync_approval': 'unknown'}
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotki.user_is_logged_in is True
