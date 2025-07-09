import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_STAKING,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import (
    YDAEMON_API,
    query_yearn_vaults,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import CacheType, ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":4}')
        if f'{YDAEMON_API}/list' in url and '&skip=0' in url:
            return MockResponse(HTTPStatus.OK, """[{"address":"0xBfBC4acAE2ceC91A5bC80eCA1C9290F92959f7c3","type":"Automated Yearn Vault","kind":"Legacy","symbol":"yvCurve-eUSDUSDC-f","display_symbol":"yvCurve-eUSDUSDC-f","formated_symbol":"yveUSDUSDC","name":"Curve eUSDUSDC Factory yVault","display_name":"Curve eUSDUSDC Factory yVault","formated_name":"eUSD/USDC yVault","icon":"https://assets.smold.app/api/token/1/0xBfBC4acAE2ceC91A5bC80eCA1C9290F92959f7c3/logo-128.png","version":"0.4.6","category":"Curve","decimals":18,"chainID":1,"endorsed":true,"boosted":false,"emergency_shutdown":false,"token":{"address":"0x08BfA22bB3e024CDfEB3eca53c0cb93bF59c4147","underlyingTokensAddresses":["0xA0d69E286B938e21CBf7E51D71F6A4c8918f482F","0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],"name":"eUSD/USDC","symbol":"eUSDUSDC","type":"Curve LP","display_name":"eUSD/USDC","display_symbol":"eUSDUSDC","description":"","icon":"https://assets.smold.app/api/token/1/0x08BfA22bB3e024CDfEB3eca53c0cb93bF59c4147/logo-128.png","decimals":18},"tvl":{"totalAssets":"0","tvl":0,"price":1.0009945186053801},"apr":{"type":"v2:new_averaged","netAPR":0,"fees":{"performance":0.1,"management":0},"points":{"weekAgo":0,"monthAgo":0,"inception":0},"extra":{"stakingRewardsAPR":null,"gammaRewardAPR":null},"forwardAPR":{"type":"crv","netAPR":0.1907285324500736,"composite":{"boost":2.5,"poolAPY":0.0063,"boostedAPR":0.2056205916111929,"baseAPR":0.08224823664447715,"cvxAPR":0,"rewardsAPR":0,"keepCRV":0,"keepVELO":0}}},"details":{"isRetired":false,"isHidden":false,"isAggregator":false,"isBoosted":false,"isAutomated":true,"isHighlighted":false,"isPool":false,"stability":"Unknown","category":"auto"},"strategies":[{"address":"0xB3650Ee177E186732c0a3B54bCaec201C76b2Df2","name":"StrategyCurveBoostedFactory-eUSDUSDC","details":{"totalDebt":"0","totalLoss":"0","totalGain":"0","performanceFee":0,"lastReport":1719934499,"debtRatio":10000}}],"migration":{"available":false,"address":"0xBfBC4acAE2ceC91A5bC80eCA1C9290F92959f7c3","contract":"0x0000000000000000000000000000000000000000"},"info":{"sourceURL":"https://curve.fi/#/ethereum/pools/factory-stable-ng-167/deposit","riskLevel":0,"isRetired":false,"isBoosted":false,"isHighlighted":false},"featuringScore":0,"pricePerShare":"1000000000000000000"},{"address":"0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9","type":"Automated Yearn Vault","kind":"Legacy","symbol":"yvCurve-mevETHfrxE-f","display_symbol":"yvCurve-mevETHfrxE-f","formated_symbol":"yvmevETHfrxE-f","name":"Curve mevETHfrxE-f Factory yVault","display_name":"Curve mevETHfrxE-f Factory yVault","formated_name":"Curve.fi Factory Crypto Pool: mevETH/frxETH yVault","icon":"https://assets.smold.app/api/token/1/0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9/logo-128.png","version":"0.4.6","category":"Curve","decimals":18,"chainID":1,"endorsed":true,"boosted":false,"emergency_shutdown":false,"token":{"address":"0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5","underlyingTokensAddresses":["0x5E8422345238F34275888049021821E8E08CAa1f","0x24Ae2dA0f361AA4BE46b48EB19C91e02c5e4f27E"],"name":"Curve.fi Factory Crypto Pool: mevETH/frxETH","symbol":"mevETHfrxE-f","type":"Curve LP","display_name":"Curve.fi Factory Crypto Pool: mevETH/frxETH","display_symbol":"mevETHfrxE-f","description":"","icon":"https://assets.smold.app/api/token/1/0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5/logo-128.png","decimals":18},"tvl":{"totalAssets":"265451271550654976","tvl":1722.9639725278246,"price":6490.69775579899},"apr":{"type":"v2:averaged","netAPR":4.111557907942738,"fees":{"performance":0.1,"management":0},"points":{"weekAgo":0,"monthAgo":4.111557907942738,"inception":2.001605308982676},"extra":{"stakingRewardsAPR":null,"gammaRewardAPR":null},"forwardAPR":{"type":"crv","netAPR":0.10578796145444178,"composite":{"boost":2.5,"poolAPY":0.0003,"boostedAPR":0.1172421793938242,"baseAPR":0.04689687175752968,"cvxAPR":0,"rewardsAPR":0,"keepCRV":0,"keepVELO":0}}},"details":{"isRetired":false,"isHidden":false,"isAggregator":false,"isBoosted":false,"isAutomated":true,"isHighlighted":false,"isPool":false,"stability":"Unknown","category":"auto"},"strategies":[{"address":"0xe02e2ec14246fdb88DA96d483CA3a5494D204585","name":"StrategyCurveBoostedFactory-mevETHfrxE-f","details":{"totalDebt":"265451271550654976","totalLoss":"0","totalGain":"0","performanceFee":0,"lastReport":1719592631,"debtRatio":10000}}],"migration":{"available":false,"address":"0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9","contract":"0x0000000000000000000000000000000000000000"},"info":{"sourceURL":"https://curve.fi/#/ethereum/pools/factory-crypto-318/deposit","riskLevel":-1,"isRetired":false,"isBoosted":false,"isHighlighted":false},"featuringScore":0,"pricePerShare":"3001605308982676080"},{"address":"0x341bb10D8f5947f3066502DC8125d9b8949FD3D6","type":"Yearn Vault","kind":"","symbol":"yvCurve-STG-USDC","display_symbol":"yvCurve-STG-USDC","formated_symbol":"yvSTGUSDC-f","name":"Curve STG-USDC Pool yVault","display_name":"Curve STG-USDC Pool yVault","formated_name":"Curve.fi Factory Crypto Pool: STG/USDC yVault","icon":"https://assets.smold.app/api/token/1/0x341bb10D8f5947f3066502DC8125d9b8949FD3D6/logo-128.png","version":"0.4.3","category":"Volatile","decimals":18,"chainID":1,"endorsed":true,"boosted":false,"emergency_shutdown":false,"token":{"address":"0xdf55670e27bE5cDE7228dD0A6849181891c9ebA1","underlyingTokensAddresses":["0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6","0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],"name":"Curve.fi Factory Crypto Pool: STG/USDC","symbol":"STGUSDC-f","type":"Curve","display_name":"Curve STG-USDC Pool","display_symbol":"crvSTG-USDC","description":"This token represents a Curve liquidity pool. Holders earn fees from users trading in the pool, and can also deposit the LP to Curve's gauges to earn CRV emissions. This Curve v2 crypto pool contains USDC and STG, Stargate Finance's governance token.","icon":"https://assets.smold.app/api/token/1/0xdf55670e27bE5cDE7228dD0A6849181891c9ebA1/logo-128.png","decimals":18},"tvl":{"totalAssets":"1075225914388863179506039","tvl":1400943.0898786543,"price":1.3029290599593875},"apr":{"type":"","netAPR":null,"fees":{"performance":null,"management":null},"points":{"weekAgo":null,"monthAgo":null,"inception":null},"extra":{"stakingRewardsAPR":null,"gammaRewardAPR":null},"forwardAPR":{"type":"","netAPR":null,"composite":{"boost":null,"poolAPY":null,"boostedAPR":null,"baseAPR":null,"cvxAPR":null,"rewardsAPR":null}}},"details":{"isRetired":true,"isHidden":false,"isAggregator":false,"isBoosted":false,"isAutomated":false,"isHighlighted":false,"isPool":true,"poolProvider":"Curve","stability":"Volatile","category":"auto"},"strategies":[],"migration":{"available":false,"address":"0x0000000000000000000000000000000000000000","contract":"0x341bb10D8f5947f3066502DC8125d9b8949FD3D6"},"info":{"sourceURL":"https://curve.fi/#/ethereum/pools/factory-crypto-37/deposit","riskLevel":-1,"isRetired":false,"isBoosted":false,"isHighlighted":false},"featuringScore":0,"pricePerShare":"1055309524466787207"},{"address":"0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13","type":"Yearn Vault","kind":"Multi Strategy","symbol":"yvmkUSD-A","display_symbol":"yvmkUSD-A","formated_symbol":"yvmkUSD","name":"mkUSD yVault-A","display_name":"mkUSD-A","formated_name":"mkUSD-A yVault","description":"Multi strategy mkUSD vault. \u003cbr/\u003e\u003cbr/\u003eMulti strategy vaults are (wait for it) vaults that contain multiple strategies. Multi strategy vaults give the vault creator flexibility to balance risk and opportunity across multiple different strategies.","icon":"https://assets.smold.app/api/token/1/0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13/logo-128.png","version":"3.0.1","category":"Stablecoin","decimals":18,"chainID":1,"endorsed":false,"boosted":false,"emergency_shutdown":false,"token":{"address":"0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28","underlyingTokensAddresses":["0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28"],"name":"Prisma mkUSD","symbol":"mkUSD","type":"Yearn Vault","display_name":"Prisma mkUSD","display_symbol":"mkUSD","description":"","icon":"https://assets.smold.app/api/token/1/0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28/logo-128.png","decimals":18},"tvl":{"totalAssets":"197532689799033418080793","tvl":193630.82657743312,"price":0.980247},"apr":{"type":"v3:averaged","netAPR":0,"fees":{"performance":0,"management":0},"points":{"weekAgo":0,"monthAgo":0,"inception":0},"extra":{"stakingRewardsAPR":null,"gammaRewardAPR":null},"forwardAPR":{"type":"v3:onchainOracle","netAPR":0,"composite":{"boost":null,"poolAPY":null,"boostedAPR":null,"baseAPR":null,"cvxAPR":null,"rewardsAPR":null,"v3OracleCurrentAPR":0,"v3OracleStratRatioAPR":0}}},"details":{"isRetired":false,"isHidden":false,"isAggregator":false,"isBoosted":false,"isAutomated":false,"isHighlighted":false,"isPool":false,"stability":"Unknown","category":"auto"},"strategies":[],"migration":{"available":false,"address":"0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13","contract":"0x0000000000000000000000000000000000000000"},"info":{"riskLevel":-1,"isRetired":false,"isBoosted":false,"isHighlighted":false},"featuringScore":0,"pricePerShare":"1000000000000000000"}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, ethereum_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_after = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

        last_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
        assert last_queried_ts is not None

    assert state_after != state_before
    # 140 is the number of vaults at the moment of writing this test
    assert state_before is None
    assert int(state_after) == 4

    # check that a new vault was added
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x341bb10D8f5947f3066502DC8125d9b8949FD3D6'),
        chain_id=ChainID.ETHEREUM,
    )

    assert token is not None
    assert token.name == 'Curve STG-USDC Pool yVault'
    assert token.symbol == 'yvCurve-STG-USDC'
    assert token.protocol == CPT_YEARN_V2

    # token in ydemon but not in the old api
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'Curve mevETHfrxE-f Factory yVault'
    assert token.symbol == 'yvCurve-mevETHfrxE-f'
    assert token.protocol == CPT_YEARN_V2
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5'

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'mkUSD yVault-A'
    assert token.symbol == 'yvmkUSD-A'
    assert token.protocol == CPT_YEARN_V3
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, ethereum_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_process_staked_vaults(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        globaldb: 'GlobalDBHandler',
        inquirer_defi: 'Inquirer',
):
    data = """[{
        "address": "0x790a60024bC3aea28385b60480f15a0771f26D09",
        "name": "Curve YFI-ETH Pool yVault",
        "symbol": "yvCurve-YFIETH",
        "decimals": 18,
        "version": "0.4.3",
        "icon": "https://assets.smold.app/api/token/1/0x790a60024bC3aea28385b60480f15a0771f26D09/logo-128.png",
        "type": "Yearn Vault",
        "token": {
        "address": "0x29059568bB40344487d62f7450E78b8E6C74e0e5",
        "name": "Curve.fi Factory Crypto Pool: YFI/ETH",
        "symbol": "YFIETH-f",
        "decimals": 18,
        "icon": "https://assets.smold.app/api/token/1/0x29059568bB40344487d62f7450E78b8E6C74e0e5/logo-128.png"
        },
        "staking": "0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3"
    }]"""
    original_request = requests.get
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('DELETE FROM unique_cache WHERE key=?', ('YEARN_VAULTS',))

    def mock_yearn_api(url, timeout):
        """Return only two yearn vaults for the API response"""
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":1}')
        if f'{YDAEMON_API}/list' in url:
            return MockResponse(HTTPStatus.OK, data)
        nonlocal original_request
        return original_request(url, timeout)

    evm_manager = inquirer_defi.get_evm_manager(chain_id=ChainID.ETHEREUM)
    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, ethereum_inquirer=ethereum_inquirer)

    token = EvmToken('eip155:1/erc20:0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3')
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09')  # noqa: E501
    assert token.protocol == CPT_YEARN_STAKING
    with patch.object(evm_manager, 'assure_curve_cache_is_queried_and_decoder_updated'):
        assert inquirer_defi.find_usd_price(token).is_close(FVal('8776.098257'), max_diff='1e6')
