import pytest

from rotkehlchen.tests.utils.exchanges import (
    create_test_coinbase,
    create_test_coinbaseprime,
)


@pytest.fixture
def function_scope_coinbase(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    return create_test_coinbase(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture
def function_scope_coinbaseprime(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    return create_test_coinbaseprime(
        database=database,
        passphrase='Rotki123!',
        msg_aggregator=function_scope_messages_aggregator,
    )
