import datetime
from collections.abc import Callable, Iterable
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

from freezegun import freeze_time

from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO
from rotkehlchen.chain.evm.decoding.morpho.utils import (
    query_morpho_reward_distributors,
    query_morpho_vaults,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_last_queried_ts_by_key,
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import CacheType, ChainID

if TYPE_CHECKING:
    from unittest.mock import _patch

    from rotkehlchen.db.dbhandler import DBHandler


def check_new_query_updates_timestamp(
        query_patch: '_patch',
        query_func: Callable,
        key_parts: Iterable[str | CacheType],
        is_general_cache: bool = False,
) -> None:
    """Trigger the query again and check that the timestamp was updated."""
    get_cache_ts_func = globaldb_get_general_cache_last_queried_ts_by_key if is_general_cache else globaldb_get_unique_cache_last_queried_ts_by_key  # noqa: E501
    with GlobalDBHandler().conn.read_ctx() as cursor:
        last_queried_ts = get_cache_ts_func(
            cursor=cursor,
            key_parts=key_parts,  # type: ignore  # can be general or unique depending on is_general_cache
        )
        assert last_queried_ts is not None

    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), query_patch:
        query_func()

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = get_cache_ts_func(
            cursor=cursor,
            key_parts=key_parts,  # type: ignore  # can be general or unique depending on is_general_cache
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


def test_morpho_vaults_api(database: 'DBHandler') -> None:
    """Test that vaults are queried correctly"""
    with (query_patch := patch(
        target='rotkehlchen.chain.evm.decoding.morpho.utils.requests.post',
        return_value=MockResponse(HTTPStatus.OK, '{"data":{"vaults":{"items":[{"address":"0xc43f5F199a055F38de4629dd14d18e69dAe9f29D","symbol":"AnzenUSDC","name":"Anzen Boosted USDC","asset":{"address":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","symbol":"USDC","name":"USD Coin","decimals":6},"chain":{"id":8453}},{"address":"0xc28ca6bFA6C1dfEF94989DC0D0A862eff8d71065","symbol":"glocWETHezETH","name":"Glocusent WETH ezETH","asset":{"address":"0x4200000000000000000000000000000000000006","symbol":"WETH","name":"Wrapped Ether","decimals":18},"chain":{"id":8453}}]}}}'),  # noqa: E501,
    )):
        query_morpho_vaults(database=database, chain_id=ChainID.BASE)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_VAULTS, str(ChainID.BASE)),
        ) == '2'

    # check that a new vault was added
    assert (token := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xc43f5F199a055F38de4629dd14d18e69dAe9f29D'),
        chain_id=ChainID.BASE,
    )) is not None
    assert token.name == 'Anzen Boosted USDC'
    assert token.symbol == 'AnzenUSDC'
    assert token.protocol == CPT_MORPHO
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

    check_new_query_updates_timestamp(
        query_patch=query_patch,
        query_func=lambda: query_morpho_vaults(database=database, chain_id=ChainID.BASE),
        key_parts=(CacheType.MORPHO_VAULTS, str(ChainID.BASE)),
    )


def test_morpho_rewards_api() -> None:
    """Test that reward distributor addresses are queried correctly."""
    eth_response = '{"data":[{"id":"0x2923a47dfacb9296e95586241349f77cbd7b48b992597011901080320cfe5957","market_id":"0x423cb007534ac88febb8ce39f544ab303e8b757f8415ed891fc76550f8f4c965","chain_id":1,"total_rewards":"2999999999999999999","total_rewards_distributed":"2999999999999999999","supply_rate_per_year":"37758620689655172413","borrow_rate_per_year":"0","collateral_rate_per_year":"0","asset":{"id":"0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0-1","address":"0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0","chain_id":1},"distributor":{"id":"0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb-1","address":"0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb","chain_id":1},"start":"1714525200","end":"1717030800","created_at":"1713968975","creator":"0x0C2553e4B9dFA9f83b1A6D3EAB96c4bAaB42d430","type":"market-reward"}]}'  # noqa: E501
    base_response = '{"data":[{"id":"0xd12a33f87f11fcc3f10b0f29b4a50999c8f7368649fdbd3f82ef1863f5aee096","vault":"0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1","chain_id":8453,"total_rewards":"4164999999999999999999998","total_rewards_distributed":"4164999999999999999999998","rate_per_year":"25337083333333333333333327","amount":"4164999999999999999999998","asset":{"id":"0xA88594D404727625A9437C3f886C7643872296AE-8453","address":"0xA88594D404727625A9437C3f886C7643872296AE","chain_id":8453},"distributor":{"id":"0x9e3380f8B29E8f85cA19EFFA80Fb41149417D943-8453","address":"0x9e3380f8B29E8f85cA19EFFA80Fb41149417D943","chain_id":8453},"start":"1718719200","end":"1723903200","created_at":"1718719200","creator":"0x74Cbb1E8B68dDD13B28684ECA202a351afD45EAa","type":"vault-reward"},{"id":"0x580cba08689cabd9a0decc50ed9ea3c1dc56e85287d9eeea8e04517be7caea30","market_id":"0xdba352d93a64b17c71104cbddc6aef85cd432322a1446b5b65163cbbc615cd0c","chain_id":8453,"total_rewards":"14279999999","total_rewards_distributed":"14279999999","supply_rate_per_year":"208141098169","borrow_rate_per_year":"0","collateral_rate_per_year":"0","asset":{"id":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913-8453","address":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","chain_id":8453},"distributor":{"id":"0x5400dBb270c956E8985184335A1C62AcA6Ce1333-8453","address":"0x5400dBb270c956E8985184335A1C62AcA6Ce1333","chain_id":8453},"start":"1718978400","end":"1721142000","created_at":"1718978400","creator":"0x874A0A0fc772a32b40e3749ACc3B72f3b0c9b82a","type":"market-reward"}]}'  # noqa: E501

    # First check that deserialization errors are handled gracefully.
    with patch(
        target='rotkehlchen.chain.evm.decoding.morpho.utils.requests.get',
        return_value=MockResponse(HTTPStatus.OK, eth_response.replace('"address":"', '"address":"XXXXXXX')),  # noqa: E501
    ):
        query_morpho_reward_distributors(chain_id=ChainID.ETHEREUM)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        for chain_id in (ChainID.BASE, ChainID.ETHEREUM):
            assert globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(chain_id)),
            ) == []

    # Check that distributors are correctly added using the good response.
    for chain_id, mock_response in (
            (ChainID.ETHEREUM, eth_response),
            (ChainID.BASE, base_response),
    ):
        with patch(
            target='rotkehlchen.chain.evm.decoding.morpho.utils.requests.get',
            return_value=MockResponse(HTTPStatus.OK, mock_response),
        ):
            query_morpho_reward_distributors(chain_id=chain_id)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(ChainID.BASE)),
        ) == [
            '0x5400dBb270c956E8985184335A1C62AcA6Ce1333',
            '0x9e3380f8B29E8f85cA19EFFA80Fb41149417D943',
        ]

        assert globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(ChainID.ETHEREUM)),
        ) == ['0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb']

    check_new_query_updates_timestamp(
        query_patch=patch(
            target='rotkehlchen.chain.evm.decoding.morpho.utils.requests.get',
            return_value=MockResponse(HTTPStatus.OK, eth_response),
        ),
        query_func=lambda: query_morpho_reward_distributors(chain_id=ChainID.ETHEREUM),
        key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(ChainID.ETHEREUM)),
        is_general_cache=True,
    )
