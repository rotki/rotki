import os
import string
from pathlib import Path
from unittest import mock

import pytest

from rotkehlchen.data_handler import DataHandler
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.user_messages import MessagesAggregator


def _user_creation_and_login(
        username: str, password: str,
        data_dir: Path, msg_aggregator:
        MessagesAggregator, sql_vm_instructions_cb: int,
):
    handler = DataHandler(
        data_directory=data_dir,
        msg_aggregator=msg_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    filepath = handler.unlock(
        username=username,
        password=password,
        create_new=True,
        resume_from_backup=False,
    )
    assert filepath is not None
    # Also login as non-new user with same password
    handler.logout()
    filepath = handler.unlock(
        username=username,
        password=password,
        create_new=False,
        resume_from_backup=False,
    )
    assert filepath is not None


def test_user_long_password(
        data_dir: Path,
        function_scope_messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
):
    """Test that very long password work. https://github.com/rotki/rotki/issues/805"""
    username = 'foo'
    password = 'dadsadsadsdsasadsadsadsadsadsadsadhkhdkjasd#$%$%*)(\\aasdasdsadjsakdhjaskdhkjsadhkjsadhsdadsadjksajdlskajdskldjslkdjklasjdlsadjsadj4324@#@qweioqweiCZCK#$a'  # noqa: E501
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_user_password_with_double_quote(
        data_dir: Path,
        function_scope_messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
):
    """Test that a password containing " is accepted.

    Probably what caused https://github.com/rotki/rotki/issues/805 to be reported"""
    username = 'foo'
    password = 'pass"word'
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_user_password_with_all_ascii(
        data_dir: Path,
        function_scope_messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
):
    """Test that a password containing all ASCII characters is accepted"""
    username = 'foo'
    password = string.printable
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_users_query_permission_error(
        data_dir: Path,
        function_scope_messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
):
    not_allowed_dir = os.path.join(data_dir, 'notallowed')
    allowed_user_dir = os.path.join(data_dir, 'allowed_user')
    os.mkdir(not_allowed_dir)
    os.chmod(not_allowed_dir, 0o200)
    os.mkdir(allowed_user_dir)
    Path(os.path.join(allowed_user_dir, 'rotkehlchen.db')).touch()
    handler = DataHandler(
        data_directory=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    assert handler.get_users() == {'allowed_user': 'loggedout'}
    # Change permissions back to that pytest cleanup can clean it
    os.chmod(not_allowed_dir, 0o777)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@mock.patch.object(Path, 'mkdir', side_effect=PermissionError)
def test_new_user_permission_error(
        data_dir: Path,
        function_scope_messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
):
    not_allowed_dir = Path(os.path.join(data_dir, 'notallowed'))

    handler = DataHandler(
        data_directory=not_allowed_dir,
        msg_aggregator=function_scope_messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    with pytest.raises(SystemPermissionError):
        handler.unlock(
            username='someuser',
            password='123',
            create_new=True,
            resume_from_backup=False,
        )
