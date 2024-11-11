import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import requests
from freezegun import freeze_time

from rotkehlchen.chain.evm.decoding.morpho.utils import MORPHO_BLUE_API, query_morpho_vaults
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import MORPHO_VAULT_PROTOCOL, CacheType, ChainID

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def test_morpho_api(database: 'DBHandler') -> None:
    """Test that vaults are queried correctly"""
    original_request = requests.get

    def mock_morpho_api(url, json, headers, timeout):
        """Return only two morpho vaults for the API response"""
        if url == MORPHO_BLUE_API:
            return MockResponse(HTTPStatus.OK, '{"data":{"vaults":{"items":[{"address":"0xc43f5F199a055F38de4629dd14d18e69dAe9f29D","symbol":"AnzenUSDC","name":"Anzen Boosted USDC","asset":{"address":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","symbol":"USDC","name":"USD Coin","decimals":6},"chain":{"id":8453}},{"address":"0xc28ca6bFA6C1dfEF94989DC0D0A862eff8d71065","symbol":"glocWETHezETH","name":"Glocusent WETH ezETH","asset":{"address":"0x4200000000000000000000000000000000000006","symbol":"WETH","name":"Wrapped Ether","decimals":18},"chain":{"id":8453}}]}}}')  # noqa: E501

        nonlocal original_request
        return original_request(url=url, json=json, headers=headers, timeout=timeout)

    with patch.object(requests, 'post', wraps=mock_morpho_api):
        query_morpho_vaults(database=database)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_VAULTS,),
        ) == '2'

        last_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_VAULTS,),
        )
        assert last_queried_ts is not None

    # check that a new vault was added
    assert (token := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xc43f5F199a055F38de4629dd14d18e69dAe9f29D'),
        chain_id=ChainID.BASE,
    )) is not None
    assert token.name == 'Anzen Boosted USDC'
    assert token.symbol == 'AnzenUSDC'
    assert token.protocol == MORPHO_VAULT_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'post', wraps=mock_morpho_api):
        query_morpho_vaults(database=database)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts
