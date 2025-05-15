import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import requests
from freezegun import freeze_time

from rotkehlchen.chain.evm.decoding.curve.constants import CURVE_BASE_API_URL
from rotkehlchen.chain.evm.decoding.curve_lend.utils import query_curve_lending_vaults
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import CURVE_LENDING_VAULTS_PROTOCOL, CacheType, ChainID

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def test_curve_lend_api(database: 'DBHandler') -> None:
    """Test that vaults are queried correctly"""
    original_request = requests.get

    def mock_curve_api(url, timeout):
        """Return only two Curve lending vaults for the API response"""
        if url == f'{CURVE_BASE_API_URL}/v1/getLendingVaults/all':
            return MockResponse(HTTPStatus.OK, '{"success":true,"data":{"lendingVaultData":[{"id":"oneway-9","name":"Borrow crvUSD (WETH collateral)","address":"0xd3cA9BEc3e681b0f578FD87f20eBCf2B7e0bb739","controllerAddress":"0xB5c6082d3307088C98dA8D79991501E113e6365d","ammAddress":"0x57126764Dec272132244a10894Ef9bF7B4EE282f","monetaryPolicyAddress":"0xec48e0AF8f392Df8f4823A4be3D02853d3525901","rates":{"borrowApr":0.2358,"borrowApy":0.2658,"borrowApyPcent":26.5827,"lendApr":0.1973,"lendApy":0.2181,"lendApyPcent":21.8065},"gaugeAddress":"0xbe543fc11b6eb4ae1a80cb4e06828f06dc3791da","gaugeRewards":[{"gaugeAddress":"0xbe543fc11b6eb4ae1a80cb4e06828f06dc3791da","tokenPrice":0.946375,"name":"Arbitrum","symbol":"ARB","decimals":"18","apy":0,"metaData":{"rate":"99206349206349","periodFinish":1728938477},"tokenAddress":"0x912CE59144191C1204E64559FE8253a0e49E6548"}],"assets":{"borrowed":{"symbol":"crvUSD","decimals":18,"address":"0x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5","blockchainId":"arbitrum","usdPrice":1},"collateral":{"symbol":"WETH","decimals":18,"address":"0x82af49447d8a07e3bd95bd0d56f35241523fbab1","blockchainId":"arbitrum","usdPrice":3476.75}},"vaultShares":{"pricePerShare":0.001032916376960093,"totalShares":2096857938.08},"totalSupplied":{"total":2165878.9,"usdTotal":2159100.27},"borrowed":{"total":1812388.44,"usdTotal":1806716.14},"availableToBorrow":{"total":353490.47,"usdTotal":352384.13},"lendingVaultUrls":{"deposit":"https://lend.curve.fi/#/arbitrum/markets/one-way-market-9/vault/deposit","withdraw":"https://lend.curve.fi/#/arbitrum/markets/one-way-market-9/vault/withdraw"},"usdTotal":2159100.27,"ammBalances":{"ammBalanceBorrowed":5.14,"ammBalanceBorrowedUsd":5.12,"ammBalanceCollateral":758.07,"ammBalanceCollateralUsd":2635636.52},"blockchainId":"arbitrum","registryId":"oneway"},{"id":"oneway-9","name":"Borrow crvUSD (WBTC collateral)","address":"0xccd37EB6374Ae5b1f0b85ac97eFf14770e0D0063","controllerAddress":"0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617","ammAddress":"0x8eeDE294459EFaFf55d580bc95C98306Ab03F0C8","monetaryPolicyAddress":"0x188041aD83145351Ef45F4bb91D08886648aEaF8","rates":{"borrowApr":0.1657,"borrowApy":0.1801,"borrowApyPcent":18.0117,"lendApr":0.1372,"lendApy":0.1471,"lendApyPcent":14.7072},"gaugeAddress":"0x7dcb252f7ea2b8da6fa59c79edf63f793c8b63b6","gaugeRewards":[],"assets":{"borrowed":{"symbol":"crvUSD","decimals":18,"address":"0xf939e0a03fb07f59a73314e73794be0e57ac1b4e","blockchainId":"ethereum","usdPrice":1},"collateral":{"symbol":"WBTC","decimals":8,"address":"0x2260fac5e5542a773aa44fbcfedf7c193bc2c599","blockchainId":"ethereum","usdPrice":94349}},"vaultShares":{"pricePerShare":0.001029742912330429,"totalShares":3746518522.65},"totalSupplied":{"total":3857950.89,"usdTotal":3845874.72},"borrowed":{"total":3196221.49,"usdTotal":3186216.66},"availableToBorrow":{"total":661729.41,"usdTotal":659658.06},"lendingVaultUrls":{"deposit":"https://lend.curve.fi/#/ethereum/markets/one-way-market-9/vault/deposit","withdraw":"https://lend.curve.fi/#/ethereum/markets/one-way-market-9/vault/withdraw"},"usdTotal":3845874.72,"ammBalances":{"ammBalanceBorrowed":0,"ammBalanceBorrowedUsd":0,"ammBalanceCollateral":66.36,"ammBalanceCollateralUsd":6260692.2},"blockchainId":"ethereum","registryId":"oneway"}],"tvl":30600981.549999993},"generatedTimeMs":1732569459560}')  # noqa: E501

        nonlocal original_request
        return original_request(url=url, timeout=timeout)

    with patch.object(requests, 'get', wraps=mock_curve_api):
        query_curve_lending_vaults(database=database)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LENDING_VAULTS,),
        ) == '2'

        last_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LENDING_VAULTS,),
        )
        assert last_queried_ts is not None

    # check that a new vault was added
    assert (token := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xd3cA9BEc3e681b0f578FD87f20eBCf2B7e0bb739'),
        chain_id=ChainID.ARBITRUM_ONE,
    )) is not None
    assert token.name == 'Borrow crvUSD (WETH collateral)'
    assert token.symbol == 'cvcrvUSD'
    assert token.protocol == CURVE_LENDING_VAULTS_PROTOCOL
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_curve_api):
        query_curve_lending_vaults(database=database)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LENDING_VAULTS,),
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts
