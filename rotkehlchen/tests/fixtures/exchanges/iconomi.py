import pytest

from rotkehlchen.tests.utils.exchanges import create_test_iconomi


@pytest.fixture(scope='function')
def function_scope_iconomi(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_iconomi(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
