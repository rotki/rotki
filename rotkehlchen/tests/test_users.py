import string

from rotkehlchen.data_handler import DataHandler


def _user_creation_and_login(username, password, data_dir, msg_aggregator):
    handler = DataHandler(
        data_directory=data_dir,
        msg_aggregator=msg_aggregator,
    )
    filepath = handler.unlock(username=username, password=password, create_new=True)
    assert filepath is not None
    # Also login as non-new user with same password
    handler.logout()
    filepath = handler.unlock(username=username, password=password, create_new=False)
    assert filepath is not None


def test_user_long_password(data_dir, function_scope_messages_aggregator):
    """Test that very long password work. https://github.com/rotki/rotki/issues/805"""
    username = 'foo'
    password = 'dadsadsadsdsasadsadsadsadsadsadsadhkhdkjasd#$%$%*)(\\aasdasdsadjsakdhjaskdhkjsadhkjsadhsdadsadjksajdlskajdskldjslkdjklasjdlsadjsadj4324@#@qweioqweiCZCK#$a'  # noqa: E501
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )


def test_user_password_with_double_quote(data_dir, function_scope_messages_aggregator):
    """Test that a password containing " is accepted.

    Probably what caused https://github.com/rotki/rotki/issues/805 to be reported"""
    username = 'foo'
    password = 'pass"word'
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )


def test_user_password_with_all_ascii(data_dir, function_scope_messages_aggregator):
    """Test that a password containing all ASCII characters is accepted"""
    username = 'foo'
    password = string.printable
    _user_creation_and_login(
        username=username,
        password=password,
        data_dir=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
