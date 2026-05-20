import pytest

from rotkehlchen.tests.utils.exchanges import create_test_gate


@pytest.fixture(name='gate_exchange')
def function_scope_gate(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_gate(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
