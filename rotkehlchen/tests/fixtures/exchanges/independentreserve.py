import pytest

from rotkehlchen.tests.utils.exchanges import create_test_independentreserve


@pytest.fixture(scope='function')
def function_scope_independentreserve(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_independentreserve(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
