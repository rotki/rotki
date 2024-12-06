import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.yearn.utils import YDAEMON_API, query_yearn_vaults
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    YEARN_STAKING_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    YEARN_VAULTS_V3_PROTOCOL,
    CacheType,
    ChainID,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_ethereum(database: 'DBHandler', ethereum_inquirer: 'EthereumInquirer') -> None:
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url: str, timeout: Any) -> MockResponse | requests.Response:
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
        query_yearn_vaults(db=database, evm_inquirer=ethereum_inquirer)

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
    assert state_after is not None
    assert int(state_after) == 4

    # check that a new vault was added
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x341bb10D8f5947f3066502DC8125d9b8949FD3D6'),
        chain_id=ChainID.ETHEREUM,
    )

    assert token is not None
    assert token.name == 'Curve STG-USDC Pool yVault'
    assert token.symbol == 'yvCurve-STG-USDC'
    assert token.protocol == YEARN_VAULTS_V2_PROTOCOL

    # token in ydemon but not in the old api
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token is not None
    assert token.name == 'Curve mevETHfrxE-f Factory yVault'
    assert token.symbol == 'yvCurve-mevETHfrxE-f'
    assert token.protocol == YEARN_VAULTS_V2_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5'

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token is not None
    assert token.name == 'mkUSD yVault-A'
    assert token.symbol == 'yvmkUSD-A'
    assert token.protocol == YEARN_VAULTS_V3_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_process_staked_vaults_ethereum(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        globaldb: 'GlobalDBHandler',
        inquirer_defi: 'Inquirer',
) -> None:
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
        query_yearn_vaults(db=database, evm_inquirer=ethereum_inquirer)

    token = EvmToken('eip155:1/erc20:0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3')
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09')  # noqa: E501
    assert token.protocol == YEARN_STAKING_PROTOCOL
    with patch.object(evm_manager, 'assure_curve_cache_is_queried_and_decoder_updated'):
        assert FVal(7413.3987907).is_close(inquirer_defi.find_usd_price(token))


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_optimism(database: 'DBHandler', optimism_inquirer: 'OptimismInquirer') -> None:
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url: str, timeout: Any) -> MockResponse | requests.Response:
        """Return only three yearn vaults for the API response"""
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":3}')
        if f'{YDAEMON_API}/list' in url and '&skip=0' in url:
            return MockResponse(HTTPStatus.OK, """[{"address": "0xf5A8aF3C13C0f6c139F58aac8A549100484E0aaD","type": "Automated Yearn Vault","kind": "Legacy","symbol": "yvVelo-UNLOCK-VELO-f","display_symbol": "yvVelo-UNLOCK-VELO-f","formated_symbol": "yvvAMMV2-UNLOCK/VELO","name": "Velodrome v2 UNLOCK-VELO Factory yVault","display_name": "Velodrome v2 UNLOCK-VELO Factory yVault","formated_name": "VolatileV2 AMM - UNLOCK/VELO yVault","icon": "https://assets.smold.app/api/token/10/0xf5A8aF3C13C0f6c139F58aac8A549100484E0aaD/logo-128.png","version": "0.4.6","category": "Velodrome","decimals": 18,"chainID": 10,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x6e6046E9b5E3D90eac2ABbA610bcA725834Ca5b3","underlyingTokensAddresses": [],"name": "VolatileV2 AMM - UNLOCK/VELO","symbol": "vAMMV2-UNLOCK/VELO","type": "Velodrome","display_name": "Velodrome Volatile UNLOCK-VELO","display_symbol": "vAMMV2-UNLOCK/VELO","description": "This token represents a Velodrome liquidity pool. Holders earn fees from users trading in the pool, and can also deposit the LP to Velodrome's gauges to earn emissions. This volatile pool contains UNLOCK and VELO.","icon": "https://assets.smold.app/api/token/10/0x6e6046E9b5E3D90eac2ABbA610bcA725834Ca5b3/logo-128.png","decimals": 18},"tvl": {"totalAssets": "12142009652638857040176","tvl": 315.9593751809684,"price": 0.026022},"apr": {"type": "v2:averaged","netAPR": 0,"fees": {"performance": 0.1,"management": 0},"points": {"weekAgo": 0,"monthAgo": 0,"inception": 0.7212614473105359},"pricePerShare": {"today": 1.7212614473105359,"weekAgo": 1.7212614473105359,"monthAgo": 1.7212614473105359},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "v2:velo_unpopular","netAPR": 0,"composite": {"boost": 0,"poolAPY": 0,"boostedAPR": 0,"baseAPR": 0,"cvxAPR": 0,"rewardsAPR": 0}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": true,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Velodrome"},"strategies": [{"address": "0x4A3f4DFf2cDe557BaBAe2A7E1f7bd84092840631","name": "Velodrome Reinvest","description": "Supplies {{token}} to [Velodrome Finance](https://app.velodrome.finance/liquidity) and stakes it in the gauge to collect any available tokens and earn VELO rewards. Rewards are harvested, sold for more {{token}}, and deposited back into the strategy.","details": {"totalDebt": "12142009652638857040176","totalLoss": "0","totalGain": "7645280763913705299842","performanceFee": 0,"lastReport": 1732058347,"debtRatio": 10000}}],"migration": {"available": false,"address": "0xf5A8aF3C13C0f6c139F58aac8A549100484E0aaD","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"riskLevel": 0,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [0,0,0,0,0,0,0,0,0,0,0]},"featuringScore": 0,"pricePerShare": "1721261447310535901"},{"address": "0x36E4c18B2B43CC989085B4a7306915b115058abF","type": "Automated Yearn Vault","kind": "Legacy","symbol": "yvVelo-DAI-USDC.e-f","display_symbol": "yvVelo-DAI-USDC.e-f","formated_symbol": "yvsAMMV2-USDC/DAI","name": "Velodrome v2 DAI-USDC.e Factory yVault","display_name": "Velodrome v2 DAI-USDC.e Factory yVault","formated_name": "StableV2 AMM - USDC/DAI yVault","icon": "https://assets.smold.app/api/token/10/0x36E4c18B2B43CC989085B4a7306915b115058abF/logo-128.png","version": "0.4.6","category": "Velodrome","decimals": 18,"chainID": 10,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x19715771E30c93915A5bbDa134d782b81A820076","underlyingTokensAddresses": [],"name": "StableV2 AMM - USDC/DAI","symbol": "sAMMV2-USDC/DAI","type": "Velodrome","display_name": "Velodrome Stable USDC.e-DAI","display_symbol": "sAMM-USDC.e/DAI","description": "This token represents a Velodrome liquidity pool. Holders earn fees from users trading in the pool, and can also deposit the LP to Velodrome's gauges to earn emissions. This stablepool contains USDC.e and DAI.","icon": "https://assets.smold.app/api/token/10/0x19715771E30c93915A5bbDa134d782b81A820076/logo-128.png","decimals": 18},"tvl": {"totalAssets": "9512420057978","tvl": 19.013467874805013,"price": 1998804.48497},"apr": {"type": "v2:averaged","netAPR": 0,"fees": {"performance": 0.1,"management": 0},"points": {"weekAgo": 0,"monthAgo": 0,"inception": 0.025324225952032542},"pricePerShare": {"today": 1.0253242259520325,"weekAgo": 1.0253242259520325,"monthAgo": 1.0253242259520325},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "v2:velo","netAPR": 0.031605951112537056,"composite": {"boost": 0,"poolAPY": 0,"boostedAPR": 0,"baseAPR": 0,"cvxAPR": 0,"rewardsAPR": 0}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": true,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Velodrome"},"strategies": [{"address": "0xEBa7737DD78212a37229f823c3f286bC57597C39","name": "Velodrome Reinvest","description": "Supplies {{token}} to [Velodrome Finance](https://app.velodrome.finance/liquidity) and stakes it in the gauge to collect any available tokens and earn VELO rewards. Rewards are harvested, sold for more {{token}}, and deposited back into the strategy.","details": {"totalDebt": "9512420057978","totalLoss": "0","totalGain": "285764625914","performanceFee": 0,"lastReport": 1710504133,"debtRatio": 10000}}],"migration": {"available": false,"address": "0x36E4c18B2B43CC989085B4a7306915b115058abF","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"riskLevel": 0,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [0,0,0,0,0,0,0,0,0,0,0]},"featuringScore": 0,"pricePerShare": "1025324225952032594"},{"address": "0x22687Ca792A8Cb5E169a77E0949e71Fe37147604","type": "Yearn Vault","kind": "Legacy","symbol": "yvVelo-USDC-DOLA","display_symbol": "yvVelo-USDC-DOLA","formated_symbol": "yvsAMM-USDC/DOLA","name": "Velodrome USDC-DOLA yVault","display_name": "Velodrome USDC-DOLA yVault","formated_name": "StableV1 AMM - USDC/DOLA yVault","icon": "https://assets.smold.app/api/token/10/0x22687Ca792A8Cb5E169a77E0949e71Fe37147604/logo-128.png","version": "0.4.5","category": "Velodrome","decimals": 18,"chainID": 10,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x6C5019D345Ec05004A7E7B0623A91a0D9B8D590d","underlyingTokensAddresses": [],"name": "StableV1 AMM - USDC/DOLA","symbol": "sAMM-USDC/DOLA","type": "Velodrome","display_name": "Velodrome Stable USDC.e-DOLA","display_symbol": "sAMM-USDC.e/DOLA","description": "This token represents a Velodrome liquidity pool. Holders earn fees from users trading in the pool, and can also deposit the LP to Velodrome's gauges to earn emissions. This stablepool contains USDC.e and DOLA.","icon": "https://assets.smold.app/api/token/10/0x6C5019D345Ec05004A7E7B0623A91a0D9B8D590d/logo-128.png","decimals": 18},"tvl": {"totalAssets": "1562459850268","tvl": 0,"price": 0},"apr": {"type": "v2:averaged","netAPR": 0,"fees": {"performance": 0.2,"management": 0},"points": {"weekAgo": 0,"monthAgo": 0,"inception": 0},"pricePerShare": {"today": 1,"weekAgo": 1,"monthAgo": 1},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "","netAPR": null,"composite": {"boost": null,"poolAPY": null,"boostedAPR": null,"baseAPR": null,"cvxAPR": null,"rewardsAPR": null}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Velodrome"},"strategies": [{"address": "0x4809143428Ed49D08978aDF209A4179d52ce5371","name": "Velodrome Reinvest","description": "Supplies {{token}} to [Velodrome Finance](https://app.velodrome.finance/liquidity) and stakes it in the gauge to collect any available tokens and earn VELO rewards. Rewards are harvested, sold for more {{token}}, and deposited back into the strategy.","details": {"totalDebt": "1562459850268","totalLoss": "0","totalGain": "0","performanceFee": 0,"lastReport": 1687347949,"debtRatio": 10000}}],"migration": {"available": false,"address": "0x22687Ca792A8Cb5E169a77E0949e71Fe37147604","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "0x692287540111A8a9B3323427e729073d9aaeEe83","available": true,"source": "OP Boost","rewards": [{"address": "0x7D2382b1f8Af621229d33464340541Db362B4907","name": "OP yVault","symbol": "yvOP","decimals": 18,"price": 2.5110492997200544,"isFinished": true,"finishedAt": 1688046333,"apr": 0,"perWeek": 0}]},"info": {"riskLevel": 0,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [0,0,0,0,0,0,0,0,0,0,0]},"featuringScore": 0,"pricePerShare": "1000000000000000000"}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=optimism_inquirer)

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
    assert state_before is None
    assert state_after is not None
    assert int(state_after) == 3

    # check that a new vault was added
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xf5A8aF3C13C0f6c139F58aac8A549100484E0aaD'),
        chain_id=ChainID.OPTIMISM,
    )
    assert token is not None
    assert token.name == 'Velodrome v2 UNLOCK-VELO Factory yVault'
    assert token.symbol == 'yvVelo-UNLOCK-VELO-f'
    assert token.protocol == YEARN_VAULTS_V2_PROTOCOL

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=optimism_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_base(database: 'DBHandler', base_inquirer: 'BaseInquirer') -> None:
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB.

    the ydaemon for base has 33 vaults, only v3 and without staking
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url: str, timeout: Any) -> MockResponse | requests.Response:
        """Return only two yearn vaults for the API response"""
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":2}')
        if f'{YDAEMON_API}/list' in url and '&skip=0' in url:
            return MockResponse(HTTPStatus.OK, """[{"address": "0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F","type": "Yearn Vault","kind": "Single Strategy","symbol": "ysDAI","display_symbol": "ysDAI","formated_symbol": "yvysDAI","name": "AaveV3 DAI Lender","display_name": "Aave V3 DAI Lender","formated_name": "Aave V3 DAI Lender yVault","description": "Supplies {{token}} to [Aave V3](https://app.aave.com/) to generate interest and earn any applicable rewards. Earned tokens are harvested, sold for more {{token}} which is deposited back into the strategy.","icon": "https://assets.smold.app/api/token/137/0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F/logo-128.png","version": "3.0.1","category": "Stablecoin","decimals": 18,"chainID": 137,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063","underlyingTokensAddresses": [],"name": "(PoS) Dai Stablecoin","symbol": "DAI","type": "","display_name": "(PoS) Dai Stablecoin","display_symbol": "DAI","description": "","icon": "https://assets.smold.app/api/token/137/0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063/logo-128.png","decimals": 18},"tvl": {"totalAssets": "773470631748246083818712","tvl": 773470.6317482461,"price": 1},"apr": {"type": "v3:averaged","netAPR": 0.07538930146288543,"fees": {"performance": 0.05,"management": 0},"points": {"weekAgo": 0.03255456949348464,"monthAgo": 0.07538930146288543,"inception": 0.07304584512866774},"pricePerShare": {"today": 1.0730458451286677,"weekAgo": 1.072376323904235,"monthAgo": 1.0664377903286812},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "v3:onchainOracle","netAPR": 0.10183615424257386,"composite": {"boost": null,"poolAPY": null,"boostedAPR": null,"baseAPR": null,"cvxAPR": null,"rewardsAPR": null,"v3OracleCurrentAPR": 0.10183615424257386,"v3OracleStratRatioAPR": 0}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Stablecoin"},"strategies": [],"migration": {"available": false,"address": "0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"riskLevel": 1,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [3,1,1,1,1,1,1,1,1,1,1]},"featuringScore": 0,"pricePerShare": "1073045845128667647"},{"address": "0x42908891cBC13301C910B4E71055431bf134AAa0","type": "Yearn Vault","kind": "Multi Strategy","symbol": "ysawMATIC-USDC","display_symbol": "ysawMATIC-USDC","formated_symbol": "yvawMATIC-USDC","name": "yearn-V3-Gamma-WMATIC-USDC.e","display_name": "Gamma WMATIC/USDC.e LP","formated_name": "Gamma WMATIC/USDC.e LP yVault","description": "[Click here](https://app.gamma.xyz/vault/qi/polygon/details/wmatic-usdc.e-narrow) to get your {{token}} Gamma LP tokens. <br/><br/>Stakes {{token}} on [Gamma.xyz](https://app.gamma.xyz/vault/qi/polygon/details/wmatic-usdc.e-narrow). Earned reward tokens are harvested, sold for more {{token}} which is deposited back into the strategy.","icon": "https://assets.smold.app/api/token/137/0x42908891cBC13301C910B4E71055431bf134AAa0/logo-128.png","version": "3.0.1","category": "Gamma","decimals": 18,"chainID": 137,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x04d521E2c414E6d898c6F2599FdD863Edf49e247","underlyingTokensAddresses": [],"name": "awMATIC-USDC","symbol": "awMATIC-USDC","type": "","display_name": "awMATIC-USDC","display_symbol": "awMATIC-USDC","description": "","icon": "https://assets.smold.app/api/token/137/0x04d521E2c414E6d898c6F2599FdD863Edf49e247/logo-128.png","decimals": 18},"tvl": {"totalAssets": "2137410617","tvl": 277.8359836700345,"price": 129987182369.28947},"apr": {"type": "v3:averaged","netAPR": 0.7818766054342569,"fees": {"performance": 0,"management": 0},"points": {"weekAgo": 0,"monthAgo": 0.7818766054342569,"inception": 0.4027279330330169},"pricePerShare": {"today": 1.402727933033017,"weekAgo": 1.402727933033017,"monthAgo": 1.318026501251825},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": 0.7736404011577269},"forwardAPR": {"type": "gamma","netAPR": 274.1094567870083,"composite": {"boost": 0,"poolAPY": 0,"boostedAPR": 0,"baseAPR": 0,"cvxAPR": 0,"rewardsAPR": 0.7736404011577269}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": false,"isPool": false,"poolProvider": "Gamma","stability": "Unknown","category": "Gamma"},"strategies": [],"migration": {"available": false,"address": "0x42908891cBC13301C910B4E71055431bf134AAa0","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"sourceURL": "https://app.gamma.xyz/vault/qi/polygon/details/wmatic-usdc.e-narrow","riskLevel": 2,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [0,0,0,0,0,0,0,0,0,0,0]},"featuringScore": 0,"pricePerShare": "1402727933033016948"}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=base_inquirer)

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
    assert state_after is not None
    assert int(state_after) == 2

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F'),
        chain_id=ChainID.BASE,
    )
    assert token is not None
    assert token.name == 'AaveV3 DAI Lender'
    assert token.symbol == 'ysDAI'
    assert token.protocol == YEARN_VAULTS_V3_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=base_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_arbitrum(database: 'DBHandler', arbitrum_one_inquirer: 'ArbitrumOneInquirer') -> None:  # noqa: E501
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB.

    the ydaemon for base has 33 vaults, only v3 and without staking
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url: str, timeout: Any) -> MockResponse | requests.Response:
        """Return only two yearn vaults for the API response"""
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":1}')
        if f'{YDAEMON_API}/list' in url and '&skip=0' in url:
            return MockResponse(HTTPStatus.OK, """[{"address": "0x9FA306b1F4a6a83FEC98d8eBbaBEDfF78C407f6B","type": "Yearn Vault","kind": "Multi Strategy","symbol": "yvUSDC-2","display_symbol": "yvUSDC.e-2","formated_symbol": "yvUSDC","name": "USDC-2 yVault","display_name": "USDC.e-2","formated_name": "USDC.e-2 yVault","description": "Multi strategy USDC.e vault. <br/><br/>Vaults labeled with the category of -2 will use strategies deploying into less proven but potentially higher yielding protocols than the standard vaults. These strategies may have a higher likelyhood of becoming temporarily illiquid or even producing losses, but are expected to earn more yield than others.","icon": "https://assets.smold.app/api/token/42161/0x9FA306b1F4a6a83FEC98d8eBbaBEDfF78C407f6B/logo-128.png","version": "3.0.2","category": "Stablecoin","decimals": 6,"chainID": 42161,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8","underlyingTokensAddresses": [],"name": "USD Coin (Arb1)","symbol": "USDC","type": "","display_name": "USD Coin (Arb1)","display_symbol": "USDC","description": "","icon": "https://assets.smold.app/api/token/42161/0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8/logo-128.png","decimals": 6},"tvl": {"totalAssets": "245709382901","tvl": 245640.0928550219,"price": 0.999718},"apr": {"type": "v3:averaged","netAPR": 0.1320624664069851,"fees": {"performance": 0.1,"management": 0},"points": {"weekAgo": 0.21492168314699148,"monthAgo": 0.1320624664069851,"inception": 0.029997000000000048},"pricePerShare": {"today": 1.029997,"weekAgo": 1.025769,"monthAgo": 1.018937},"extra": {"stakingRewardsAPR": 0,"gammaRewardAPR": null},"forwardAPR": {"type": "v3:onchainOracle","netAPR": 0.1834805646532489,"composite": {"boost": null,"poolAPY": null,"boostedAPR": null,"baseAPR": null,"cvxAPR": null,"rewardsAPR": null,"v3OracleCurrentAPR": 0.1834805646532489,"v3OracleStratRatioAPR": 0.1651176603439275}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": true,"isPool": false,"stability": "Unknown","category": "Stablecoin"},"strategies": [{"address": "0xb739AE19620f7ECB4fb84727f205453aa5bc1AD2","name": "Silo Lender ARB/USDC.e","details": {"totalDebt": "245709382901","totalLoss": "0","totalGain": "0","performanceFee": 1000,"lastReport": 1734502195,"debtRatio": 10000}}],"migration": {"available": false,"address": "0x9FA306b1F4a6a83FEC98d8eBbaBEDfF78C407f6B","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "0x9b8f59e6edADbA3043874e3Ce3857113353E7a22","available": true,"source": "V3 Staking","rewards": [{"address": "0x7DEB119b92b76f78C212bc54FBBb34CEA75f4d4A","name": "ARB-1 yVault","symbol": "yvARB-1","decimals": 18,"price": 0.838515,"isFinished": true,"finishedAt": 1724876752,"apr": 0,"perWeek": 0}]},"info": {"riskLevel": 2,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [0,0,0,0,0,0,0,0,0,0,0]},"featuringScore": 0,"pricePerShare": "1029981"}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=arbitrum_one_inquirer)

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
    assert state_after is not None
    assert int(state_after) == 1

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x9FA306b1F4a6a83FEC98d8eBbaBEDfF78C407f6B'),
        chain_id=ChainID.ARBITRUM_ONE,
    )
    assert token is not None
    assert token.name == 'USDC-2 yVault'
    assert token.symbol == 'yvUSDC-2'
    assert token.protocol == YEARN_VAULTS_V3_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=arbitrum_one_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_polygon(database: 'DBHandler', polygon_pos_inquirer: 'PolygonPOSInquirer') -> None:  # noqa: E501
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB.

    Only V3 vaults without staking available on polygon_pos
    """
    # mock coingecko response
    original_request = requests.get

    def mock_yearn_api(url: str, timeout: Any) -> MockResponse | requests.Response:
        """Return only two yearn vaults for the API response"""
        if f'{YDAEMON_API}/count' in url:
            return MockResponse(HTTPStatus.OK, '{"numberOfVaults":2}')
        if f'{YDAEMON_API}/list' in url and '&skip=0' in url:
            return MockResponse(HTTPStatus.OK, """[{"address": "0xb1403908F772E4374BB151F7C67E88761a0Eb4f1","type": "Yearn Vault","kind": "Single Strategy","symbol": "ysUSDC","display_symbol": "ysUSDC.e","formated_symbol": "yvysUSDC.e","name": "Compound V3 USDC Lender","display_name": "Compound V3 USDC.e Lender","formated_name": "Compound V3 USDC.e Lender yVault","description": "Supplies {{token}} on [Compound Finance](https://app.compound.finance/markets/usdc.e-polygon) to generate interest and earn COMP. Earned tokens are harvested, sold for more {{token}} which is deposited back into the strategy.","icon": "https://assets.smold.app/api/token/137/0xb1403908F772E4374BB151F7C67E88761a0Eb4f1/logo-128.png","version": "3.0.1","category": "Stablecoin","decimals": 6,"chainID": 137,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174","underlyingTokensAddresses": [],"name": "USD Coin (PoS)","symbol": "USDC","type": "","display_name": "USD Coin (PoS)","display_symbol": "USDC","description": "","icon": "https://assets.smold.app/api/token/137/0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174/logo-128.png","decimals": 6},"tvl": {"totalAssets": "353999874484","tvl": 352983.18684448197,"price": 0.997128},"apr": {"type": "v3:averaged","netAPR": 0.08188022261718782,"fees": {"performance": 0.1,"management": 0},"points": {"weekAgo": 0.026872495981194188,"monthAgo": 0.08188022261718782,"inception": 0.23083499999999987},"pricePerShare": {"today": 1.230835,"weekAgo": 1.230201,"monthAgo": 1.222607},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "v3:onchainOracle","netAPR": 0.06196348958191766,"composite": {"boost": null,"poolAPY": null,"boostedAPR": null,"baseAPR": null,"cvxAPR": null,"rewardsAPR": null,"v3OracleCurrentAPR": 0.06196348958191766,"v3OracleStratRatioAPR": 0}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Stablecoin"},"strategies": [],"migration": {"available": false,"address": "0xb1403908F772E4374BB151F7C67E88761a0Eb4f1","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"riskLevel": 1,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [3,1,1,1,1,1,1,1,1,1,1]},"featuringScore": 0,"pricePerShare": "1230835"},{"address": "0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F","type": "Yearn Vault","kind": "Single Strategy","symbol": "ysDAI","display_symbol": "ysDAI","formated_symbol": "yvysDAI","name": "AaveV3 DAI Lender","display_name": "Aave V3 DAI Lender","formated_name": "Aave V3 DAI Lender yVault","description": "Supplies {{token}} to [Aave V3](https://app.aave.com/) to generate interest and earn any applicable rewards. Earned tokens are harvested, sold for more {{token}} which is deposited back into the strategy.","icon": "https://assets.smold.app/api/token/137/0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F/logo-128.png","version": "3.0.1","category": "Stablecoin","decimals": 18,"chainID": 137,"endorsed": true,"boosted": false,"emergency_shutdown": false,"token": {"address": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063","underlyingTokensAddresses": [],"name": "(PoS) Dai Stablecoin","symbol": "DAI","type": "","display_name": "(PoS) Dai Stablecoin","display_symbol": "DAI","description": "","icon": "https://assets.smold.app/api/token/137/0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063/logo-128.png","decimals": 18},"tvl": {"totalAssets": "773470631748246083818712","tvl": 769966.8097864266,"price": 0.99547},"apr": {"type": "v3:averaged","netAPR": 0.07538930146288543,"fees": {"performance": 0.05,"management": 0},"points": {"weekAgo": 0.03255456949348464,"monthAgo": 0.07538930146288543,"inception": 0.07304584512866774},"pricePerShare": {"today": 1.0730458451286677,"weekAgo": 1.072376323904235,"monthAgo": 1.0664377903286812},"extra": {"stakingRewardsAPR": null,"gammaRewardAPR": null},"forwardAPR": {"type": "v3:onchainOracle","netAPR": 0.10098772085969099,"composite": {"boost": null,"poolAPY": null,"boostedAPR": null,"baseAPR": null,"cvxAPR": null,"rewardsAPR": null,"v3OracleCurrentAPR": 0.10098772085969099,"v3OracleStratRatioAPR": 0}}},"details": {"isRetired": false,"isHidden": false,"isAggregator": false,"isBoosted": false,"isAutomated": false,"isHighlighted": false,"isPool": false,"stability": "Unknown","category": "Stablecoin"},"strategies": [],"migration": {"available": false,"address": "0xf4F9d5697341B4C9B0Cc8151413e05A90f7dc24F","contract": "0x0000000000000000000000000000000000000000"},"staking": {"address": "","available": false,"source": "","rewards": null},"info": {"riskLevel": 1,"isRetired": false,"isBoosted": false,"isHighlighted": false,"riskScore": [3,1,1,1,1,1,1,1,1,1,1]},"featuringScore": 0,"pricePerShare": "1073045845128667647"}]""")  # noqa: E501
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=polygon_pos_inquirer)

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
    assert state_after is not None
    assert int(state_after) == 2

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xb1403908F772E4374BB151F7C67E88761a0Eb4f1'),
        chain_id=ChainID.POLYGON_POS,
    )
    assert token is not None
    assert token.name == 'Compound V3 USDC Lender'
    assert token.symbol == 'ysUSDC'
    assert token.protocol == YEARN_VAULTS_V3_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, evm_inquirer=polygon_pos_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts
