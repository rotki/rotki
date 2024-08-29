from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.constants import GRAPH_QUERY_CRED
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.fixture(name='add_subgraph_api_key')
def fixture_add_subgraph_api_key(database: 'DBHandler') -> None:
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.THEGRAPH,
                api_key=ApiKey(GRAPH_QUERY_CRED),
            )],
        )
