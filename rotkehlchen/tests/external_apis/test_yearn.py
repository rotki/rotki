import datetime
from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.chain.ethereum.modules.yearn.utils import YEARN_OLD_API, query_yearn_vaults
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.globaldb.cache import (
    globaldb_get_cache_last_queried_ts_by_key,
    globaldb_get_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import YEARN_VAULTS_V2_PROTOCOL, CacheType, ChainID, Timestamp


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api(database, ethereum_inquirer):
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url, timeout):
        """Return only two yearn vaults for the API response"""
        if YEARN_OLD_API in url:
            return MockResponse(HTTPStatus.OK, """[{"inception":14891068,"address":"0x341bb10D8f5947f3066502DC8125d9b8949FD3D6","symbol":"yvCurve-STG-USDC","name":"yvCurve-STG-USDC 0.4.3","display_name":"STGUSDC-f","icon":"https://rawcdn.githack.com/yearn/yearn-assets/4db1bb6b68ad0c7a75a1b3bf01025d2c22cfbaa7/icons/multichain-tokens/1/0x341bb10D8f5947f3066502DC8125d9b8949FD3D6/logo-128.png","token":{"name":"Curve.fi Factory Crypto Pool: STG/USDC","symbol":"STGUSDC-f","address":"0xdf55670e27bE5cDE7228dD0A6849181891c9ebA1","decimals":18,"display_name":"STGUSDC-f","icon":"https://rawcdn.githack.com/yearn/yearn-assets/4db1bb6b68ad0c7a75a1b3bf01025d2c22cfbaa7/icons/multichain-tokens/1/0xdf55670e27bE5cDE7228dD0A6849181891c9ebA1/logo-128.png"},"tvl":{"total_assets":1066762132988328431382564,"price":1.613069263536325,"tvl":1720761.2082279222},"apy":{"type":"convex","gross_apr":0.14584764353034685,"net_apy":0.09226416095055612,"fees":{"performance":0.2,"withdrawal":null,"management":0.02,"keep_crv":null,"cvx_keep_crv":0.1},"points":null,"blocks":null,"composite":null,"error_reason":null,"staking_rewards_apr":0},"strategies":[{"address":"0x916011bD2d333fBA14dBB8bf0BdF01e3384FD2e6","name":"StrategyConvexSTGUSDC"}],"endorsed":true,"version":"0.4.3","decimals":18,"type":"v2","emergency_shutdown":false,"updated":1687812577,"migration":{"available":false,"address":"0x341bb10D8f5947f3066502DC8125d9b8949FD3D6"}},{"inception":14980240,"address":"0x3B27F92C0e212C671EA351827EDF93DB27cc0c65","symbol":"yvUSDT","name":"yvUSDT 0.4.3","display_name":"USDT","icon":"https://rawcdn.githack.com/yearn/yearn-assets/4db1bb6b68ad0c7a75a1b3bf01025d2c22cfbaa7/icons/multichain-tokens/1/0x3B27F92C0e212C671EA351827EDF93DB27cc0c65/logo-128.png","token":{"name":"Tether USD","symbol":"USDT","address":"0xdAC17F958D2ee523a2206206994597C13D831ec7","decimals":6,"display_name":"USDT","icon":"https://rawcdn.githack.com/yearn/yearn-assets/4db1bb6b68ad0c7a75a1b3bf01025d2c22cfbaa7/icons/multichain-tokens/1/0xdAC17F958D2ee523a2206206994597C13D831ec7/logo-128.png"},"tvl":{"total_assets":14938928651062,"price":1.0000823,"tvl":14940158.124889985},"apy":{"type":"v2:averaged","gross_apr":0.023362870862237983,"net_apy":0.018862632100866916,"fees":{"performance":0.2,"withdrawal":null,"management":0.0,"keep_crv":null,"cvx_keep_crv":null},"points":{"week_ago":0.013129557974331796,"month_ago":0.018862632100866916,"inception":0.022614793789739185},"blocks":{"now":17565983,"week_ago":17516180,"month_ago":17345663,"inception":15243268},"composite":null,"error_reason":null,"staking_rewards_apr":0},"strategies":[{"address":"0x016919386387898E4Fa87c7c4D3324F75f178F12","name":"0x01691938"},{"address":"0x087794F304aEB337388a40e7c382A0fEa78c47fC","name":"Strategy_ProviderOfUSDTToNoHedgeUniV3StablesJoint(USDC-USDT)"},{"address":"0xBc04eFD0D18685BA97cFAdE4e2D3171701B4099c","name":"StrategyLenderYieldOptimiser"},{"address":"0xE7A8Cbc43a0506d3A328393C1C30548835256d7D","name":"Stargate-v2-USDT"},{"address":"0xde6F5b2452F94337a428c86b5D2F143383b4D573","name":"Strategy_ProviderOfUSDTToNoHedgeBalancerTripod(bb-a-USD)"},{"address":"0x8829f62FCe1DFBfA3EB60eBE95133D5F43b9BD04","name":"EmptyStrat"},{"address":"0xd8F414beB0aEb5784c5e5eBe32ca9fC182682Ff8","name":"StrategyLenderYieldOptimiser"}],"endorsed":true,"version":"0.4.3","decimals":6,"type":"v2","emergency_shutdown":false,"updated":1687812580,"migration":{"available":false,"address":"0x3B27F92C0e212C671EA351827EDF93DB27cc0c65"}}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_cache_values(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, ethereum_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_after = globaldb_get_cache_values(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

        last_queried_ts = globaldb_get_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
        assert last_queried_ts is not None

    assert state_after != state_before
    # 140 is the number of vaults at the moment of writing this test
    assert state_before is None
    assert int(state_after) == 2

    # check that a new vault was added
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x341bb10D8f5947f3066502DC8125d9b8949FD3D6'),
        chain_id=ChainID.ETHEREUM,
    )

    assert token is not None
    assert token.name == 'yvCurve-STG-USDC 0.4.3'
    assert token.symbol == 'yvCurve-STG-USDC'
    assert token.protocol == YEARN_VAULTS_V2_PROTOCOL
    assert token.started == Timestamp(1654174125)

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, ethereum_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=[CacheType.YEARN_VAULTS],
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts
