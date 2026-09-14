import pytest

from rotkehlchen.banks.qonto import Qonto
from rotkehlchen.types import ApiKey, ApiSecret


@pytest.fixture(name='qonto')
def fixture_qonto(database, function_scope_messages_aggregator):
    return Qonto(
        name='qonto1',
        api_key=ApiKey('test-login'),
        secret=ApiSecret(b'test-secret'),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
