import dataclasses
import random
import shutil
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock
from unittest.mock import patch

import gevent
import pytest
import requests
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import USERDB_NAME, USERSDIR_NAME
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION, DBSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.tests.fixtures.rotkehlchen import patch_no_op_unlock
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_async_response,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.premium import (
    VALID_PREMIUM_KEY,
    VALID_PREMIUM_SECRET,
    create_patched_premium,
)
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def check_proper_unlock_result(
        response_data: dict[str, Any],
        settings_to_check: dict[str, Any] | None = None,
) -> None:

    assert isinstance(response_data['exchanges'], list)
    assert response_data['settings']['version'] == ROTKEHLCHEN_DB_VERSION
    for setting in dataclasses.fields(DBSettings):
        assert setting.name in response_data['settings']
    assert DBCacheStatic.LAST_DATA_UPLOAD_TS.value in response_data['settings']
    assert DBCacheStatic.LAST_BALANCE_SAVE.value in response_data['settings']

    if settings_to_check is not None:
        for setting_to_check, value in settings_to_check.items():
            assert response_data['settings'][setting_to_check] == value


def check_user_status(api_server: 'APIServer') -> dict[str, str]:
    # Check users status
    response = requests.get(
        api_url_for(api_server, 'usersresource'),
    )
    return assert_proper_sync_response_with_result(response)


def test_loggedin_user_querying(
        rotkehlchen_api_server: 'APIServer',
        username: str,
        data_dir: Path,
) -> None:
    """Start with a logged in user and make sure we can query all users"""
    users_dir = data_dir / USERSDIR_NAME
    user_dir = users_dir / 'another_user'
    user_dir.mkdir(exist_ok=True)
    (user_dir / USERDB_NAME).touch()
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result[username] == 'loggedin'
    assert result['another_user'] == 'loggedout'
    assert len(result) == 2


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_not_loggedin_user_querying(
        rotkehlchen_api_server: 'APIServer',
        start_with_logged_in_user: bool,
        username: str,
        data_dir: Path,
) -> None:
    """Start without logged in user and make sure we can query all users"""
    users_dir = data_dir / USERSDIR_NAME
    another_user_dir = users_dir / 'another_user'
    another_user_dir.mkdir()
    (another_user_dir / USERDB_NAME).touch()
    user_dir = users_dir / username
    user_dir.mkdir(exist_ok=True)
    (user_dir / USERDB_NAME).touch()

    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result[username] == 'loggedout'
    assert result['another_user'] == 'loggedout'
    assert len(result) == 2


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation(
        rotkehlchen_api_server: 'APIServer',
        start_with_logged_in_user: bool,
        data_dir: Path,
) -> None:
    """Test that PUT at user endpoint can create a new user"""
    # Create a user without any premium credentials
    async_query = random.choice([False, True])
    usernames = ('hania', 'john.doe')
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    for idx, username in enumerate(usernames):
        data = {'name': username, 'password': '1234', 'async_query': async_query}
        with ExitStack() as stack:
            patch_no_op_unlock(rotki, stack)
            response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)  # noqa: E501

            if async_query is True:
                task_id = assert_ok_async_response(response)
                outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
                result = outcome['result']
            else:
                result = assert_proper_sync_response_with_result(response)

        check_proper_unlock_result(result, {'submit_usage_analytics': True})

        # Query users and make sure the new user is logged in
        response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
        result = assert_proper_sync_response_with_result(response)
        assert result[username] == 'loggedin'
        assert len(result) == idx + 1

        # Check that the directory was created
        assert (data_dir / USERSDIR_NAME / username / USERDB_NAME).exists()

        # Logout
        data = {'action': 'logout'}
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        assert_simple_ok_response(response)
        assert rotki.user_is_logged_in is False


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_no_analytics(
        rotkehlchen_api_server: 'APIServer',
        start_with_logged_in_user: bool,
        data_dir: Path,
) -> None:
    """Test that providing specific settings at user creation works"""
    # Create a user without any premium credentials
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
        'initial_settings': {'submit_usage_analytics': False},
    }
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack, should_mock_settings=False)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
        result = assert_proper_sync_response_with_result(response)
        check_proper_unlock_result(result, {'submit_usage_analytics': False})

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 1

    # Check that the directory was created
    assert (data_dir / USERSDIR_NAME / username / USERDB_NAME).exists()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@mock.patch.object(
    Path, 'mkdir',
    side_effect=PermissionError(
        'Failed to create directory for user: [Errno 13] Permission denied',
    ),
)
def test_user_creation_permission_error(
        mock_path_mkdir: mock.MagicMock,
        rotkehlchen_api_server: 'APIServer',
        use_clean_caching_directory: bool,
        start_with_logged_in_user: bool,
) -> None:
    """Test that creating a user when data directory permissions are wrong is handled"""
    username = 'hania'
    data = {
        'name': username,
        'password': '1234',
    }
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
        assert_error_response(
            response=response,
            contained_in_msg='Failed to create directory for user: [Errno 13] Permission denied',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_premium_credentials(
        rotkehlchen_api_server: 'APIServer',
        start_with_logged_in_user: bool,
        data_dir: Path,
) -> None:
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
    patched_premium_at_start, _, patched_get, _ = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        username=username,
        patch_get=True,
        database=None,  # type: ignore  # the user is not logged in
        metadata_last_modify_ts=Timestamp(0),
        metadata_data_hash='',
        metadata_data_size=0,
    )

    with patched_premium_at_start, ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    check_proper_unlock_result(result)

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 1

    # Check that the directory was created
    assert (data_dir / USERSDIR_NAME / username / USERDB_NAME).exists()

    # Check that the user has premium
    assert rotki.premium is not None
    assert rotki.premium.credentials.serialize_key() == VALID_PREMIUM_KEY
    assert rotki.premium.credentials.serialize_secret() == VALID_PREMIUM_SECRET
    with patched_get:
        assert rotki.premium.is_active()


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_with_invalid_premium_credentials(
        rotkehlchen_api_server: 'APIServer',
        data_dir: Path,
) -> None:
    """
    Test that invalid and unauthenticated premium credentials are handled at new user creation
    """
    # Create a user with invalid credentials
    username = 'hania'
    users_dir = data_dir / USERSDIR_NAME
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': 'foo',
        'premium_api_secret': 'boo',
    }
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
        assert_error_response(
            response=response,
            contained_in_msg='Provided API/Key secret format is invalid',
        )

    # Check that the directory was NOT created
    assert not Path(users_dir / username).exists(), 'The directory should not have been created'

    # Create a new user with valid but not authenticable credentials
    username = 'Anja'
    data = {
        'name': username,
        'password': '1234',
        'premium_api_key': VALID_PREMIUM_KEY,
        'premium_api_secret': VALID_PREMIUM_SECRET,
    }
    with (
        ExitStack() as stack,
        patch('rotkehlchen.premium.premium.Premium.authenticate_device', side_effect=RemoteError('Invalid API-KEY')),  # noqa: E501
    ):
        patch_no_op_unlock(rotki, stack)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)

    expected_msg = (
        'Could not verify keys for the new account. Invalid API-KEY'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # Check that the directory was NOT created
    assert not Path(users_dir / username).exists(), 'The directory should not have been created'
    # But check that a backup of the directory was made just in case
    backups = list(Path(users_dir).glob('auto_backup_*'))
    assert len(backups) == 1
    assert 'auto_backup_Anja_' in str(backups[0]), 'An automatic backup should have been made'

    # But then try to create a normal-non premium user and see it works
    username = 'hania2'
    data = {
        'name': username,
        'password': '1234',
    }
    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.put(api_url_for(rotkehlchen_api_server, 'usersresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    check_proper_unlock_result(result)

    # Query users and make sure the new user is logged in
    response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result[username] == 'loggedin'
    assert len(result) == 2

    # Check that the directory was created
    assert (users_dir / username / USERDB_NAME).exists()


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_user_creation_errors(
        rotkehlchen_api_server: 'APIServer',
        start_with_logged_in_user: bool,
        data_dir: Path,
) -> None:
    """Test errors and edge cases for user creation"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    users_dir = data_dir / USERSDIR_NAME
    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)

        # Missing username
        username = 'hania'
        data: dict[str, str | float | int | bool] = {'password': '1234'}
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

        # name containing slashes (gets interpreted as a path)
        assert_error_response(
            response=requests.put(
                url=api_url_for(rotkehlchen_api_server, 'usersresource'),
                json={'name': 'john/doe', 'password': '1234'},
            ),
            contained_in_msg=(
                'Data dir for user john/doe is not in the users directory. '
                'Usernames may not contain path separators.',
            ),
            status_code=HTTPStatus.CONFLICT,
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
        assert not (users_dir / username / USERDB_NAME).exists()

        # Let's pretend there is another user, and try to create them again
        another_user_dir = users_dir / 'another_user'
        another_user_dir.mkdir()
        (another_user_dir / USERDB_NAME).touch()
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


def test_user_creation_with_already_loggedin_user(
        rotkehlchen_api_server: 'APIServer',
        username: str,
) -> None:
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


def test_user_password_change(
        rotkehlchen_api_server: 'APIServer',
        username: str,
        db_password: str,
) -> None:
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
    data: dict[str, str | bool] = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    assert rotki.user_is_logged_in is False

    # And login with the new password to make sure it works
    data = {'password': new_password, 'sync_approval': 'unknown', 'async_query': True}

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        check_proper_unlock_result(result)
    user_is_logged_in: bool = rotki.user_is_logged_in
    assert user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 1
    assert users_data[username] == 'loggedin'


def test_user_logout(
        rotkehlchen_api_server: 'APIServer',
        username: str,
        db_password: str,
) -> None:
    """Test that user logout works successfully and that common errors are handled"""
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

    # Run some async task
    with mock.patch.object(
        target=rotkehlchen_api_server.rest_api.rotkehlchen,
        attribute='query_balances',
        side_effect=lambda *args, **kwargs: gevent.sleep(10),
    ):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'allbalancesresource', name=username),
            json={'async_query': True},
        )
        task_id = assert_ok_async_response(response)

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'specific_async_tasks_resource', task_id=task_id),
    )
    assert response.json()['result']['status'] == 'pending'

    # Logout of the active user
    assert rotki.data.db.password == db_password
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    user_is_logged_in: bool = rotki.user_is_logged_in
    assert user_is_logged_in is False
    assert rotki.data.db.password == ''

    # Check that task isn't pending anymore
    assert requests.get(
        api_url_for(rotkehlchen_api_server, 'specific_async_tasks_resource', task_id=task_id),
    ).json()['result']['status'] == 'not-found'
    assert Inquirer._uniswapv2 is None
    assert Inquirer._uniswapv3 is None
    with pytest.raises(AssertionError):
        PriceHistorian()  # raises error because we don't have any instance and we aren't providing the init arguments here.  # noqa: E501

    # Now try to log out of the same user again
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='No user is currently logged in',
        status_code=HTTPStatus.UNAUTHORIZED,
    )
    assert rotki.user_is_logged_in is False


def test_user_login(
        rotkehlchen_api_server: 'APIServer',
        username: str,
        db_password: str,
        data_dir: Path,
) -> None:
    """Test that user login works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    users_dir = data_dir / USERSDIR_NAME
    # Let's pretend there is another user, and try to create them again
    another_user_dir = users_dir / 'another_user'
    another_user_dir.mkdir()
    (another_user_dir / USERDB_NAME).touch()

    # Check users status
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'

    # Logout of the active user
    data: dict[str, str | bool] = {'action': 'logout'}
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

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        # And make sure it works
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        check_proper_unlock_result(result)

    user_is_logged_in: bool = rotki.user_is_logged_in
    assert user_is_logged_in is True
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

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        # And make sure it works despite having unauthenticable premium credentials in the DB
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        check_proper_unlock_result(result)

    assert user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'

    # Pretend that a user db upgrade is ongoing, so that we can test the resume_from_backup
    # functionality on user login while an upgrade is ongoing.
    ongoing_upgrade_from_version = 33  # pretend we are upgrading from v33

    # Add a backup
    backup_path = users_dir / username / f'{ts_now()}_rotkehlchen_db_v{ongoing_upgrade_from_version}.backup'  # noqa: E501
    shutil.copy(users_dir / username / USERDB_NAME, backup_path)
    backup_connection = DBConnection(
        path=str(backup_path),
        connection_type=DBConnectionType.USER,
        sql_vm_instructions_cb=0,
    )
    with backup_connection.write_ctx() as write_cursor:
        write_cursor.executescript(f"PRAGMA key='{db_password}'")  # unlock
        write_cursor.execute("INSERT INTO settings VALUES('is_backup', 'Yes')")
    backup_connection.close()

    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(  # Pretend that an upgrade was started
            write_cursor=write_cursor,
            name='ongoing_upgrade_from_version',
            value=ongoing_upgrade_from_version,
        )

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

    # Now let's try to login (without a consent to resume from backup)
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True, 'resume_from_backup': False}  # noqa: E501
    with (
        ExitStack() as stack,
        patch('rotkehlchen.premium.premium.Premium.authenticate_device'),
    ):
        patch_no_op_unlock(rotki, stack)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        task_id = assert_ok_async_response(response)
        response_data = wait_for_async_task(rotkehlchen_api_server, task_id)

    assert_error_async_response(
        response_data=response_data,
        contained_in_msg='Either resume from a backup or solve the issue manually',
        status_code=HTTPStatus.MULTIPLE_CHOICES,
        result_exists=True,
    )

    # Now let's try to login (with a consent to resume from backup)
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True, 'resume_from_backup': True}  # noqa: E501
    with (
        ExitStack() as stack,
        patch('rotkehlchen.premium.premium.Premium.authenticate_device'),
    ):
        patch_no_op_unlock(rotki, stack)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        # And make sure it works
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        check_proper_unlock_result(result)

    assert user_is_logged_in is True
    users_data = check_user_status(rotkehlchen_api_server)
    assert len(users_data) == 2
    assert users_data[username] == 'loggedin'
    assert users_data['another_user'] == 'loggedout'

    # check that the backup db is used
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT * FROM settings WHERE name=?', ('is_backup',))
        results: list[tuple[str, ...]] = cursor.fetchall()
        assert len(results) == 1, f'Expected one result, got {len(results)}'
        assert results[0][1] == 'Yes'

    # Remove the ongoing upgrade setting
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(
            write_cursor=write_cursor,
            name='ongoing_upgrade_from_version',
            value='',
        )


def test_user_set_premium_credentials(
        rotkehlchen_api_server: 'APIServer',
        username: str,
) -> None:
    """Test that setting the premium credentials endpoint works.

    We mock the server accepting the premium credentials
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _, patched_premium_at_set, patched_get, _ = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        username=username,
        patch_get=True,
        database=rotki.data.db,
        metadata_last_modify_ts=Timestamp(0),
        metadata_data_hash='',
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


def test_user_del_premium_credentials(
        rotkehlchen_api_server: 'APIServer',
        username: str,
) -> None:
    """Test that removing the premium credentials endpoint works.

    We first set up mock the server accepting the premium credentials
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _, patched_premium_at_set, patched_get, _ = create_patched_premium(
        PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET),
        username=username,
        patch_get=True,
        database=rotki.data.db,
        metadata_last_modify_ts=Timestamp(0),
        metadata_data_hash='',
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
        assert rotki.premium is not None
        assert rotki.premium.is_active()

    # Delete premium credentials for current user
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'userpremiumkeyresource',
                                           name=username))
    assert_simple_ok_response(response)
    premium: Premium | None = rotki.premium  # typing hinting because mypy assumes it is never None when reading the Rotkehlchen class  #  noqa: E501
    assert premium is None
    assert rotki.premium_sync_manager.premium is None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@mock.patch.object(Path, 'exists', side_effect=PermissionError)
def test_user_login_user_dir_permission_error(
        mock_path_exists: bool,
        start_with_logged_in_user: bool,
        rotkehlchen_api_server: 'APIServer',
        data_dir: Path,  # pylint: disable=unused-argument
) -> None:
    """Test that user login with userdir path permission errors is handled properly"""
    users_dir = data_dir / USERSDIR_NAME
    username = 'a_user'
    user_dir = users_dir / username
    user_dir.mkdir()
    db_path = user_dir / USERDB_NAME
    db_path.touch()
    data = {'password': '123', 'sync_approval': 'unknown', 'async_query': True}
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
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
@mock.patch.object(
    DBConnection, '__init__', side_effect=sqlcipher.OperationalError,  # pylint: disable=no-member
)
def test_user_login_db_permission_error(
        mock_db_conn: DBConnection,
        start_with_logged_in_user: bool,
        rotkehlchen_api_server: 'APIServer',
        data_dir: Path,  # pylint: disable=unused-argument
) -> None:
    """Test that user login with db path permission errors is handled properly"""
    username = 'a_user'
    user_dir = data_dir / USERSDIR_NAME / username
    user_dir.mkdir()
    db_path = user_dir / USERDB_NAME
    db_path.touch()
    data = {'password': '123', 'sync_approval': 'unknown', 'async_query': True}
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
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


def test_user_set_premium_credentials_errors(
        rotkehlchen_api_server: 'APIServer',
        username: str,
) -> None:
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
    with patch('rotkehlchen.premium.premium.Premium.authenticate_device', side_effect=RemoteError('Invalid API-KEY')):  # noqa: E501
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Invalid API-KEY',
        status_code=HTTPStatus.FORBIDDEN,
    )


def test_users_by_name_endpoint_errors(
        rotkehlchen_api_server: 'APIServer',
        username: str,
        db_password: str,
) -> None:
    """Test that user by name endpoint errors are handled (for login/logout and edit)"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Now let's try to login while the user is already logged in
    data: dict[str, str | bool | float] = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}  # noqa: E501
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
    user_is_logged_in: bool = rotki.user_is_logged_in
    assert user_is_logged_in is False

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
    assert user_is_logged_in is False

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
    assert user_is_logged_in is False

    # Login first to test that schema validation works.
    data = {'password': db_password, 'sync_approval': 'unknown', 'async_query': True}

    with ExitStack() as stack:
        patch_no_op_unlock(rotki, stack)
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
