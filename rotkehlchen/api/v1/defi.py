"""Async implementation of DeFi protocol endpoints

This module provides high-performance async DeFi protocol operations.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.errors.api import APIError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.chain.evm.types import string_to_evm_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["defi"])


# Pydantic models
class DeFiBalanceQuery(BaseModel):
    """Parameters for DeFi balance queries"""
    async_query: bool = Field(default=True)
    ignore_cache: bool = Field(default=False)


class LiquityQuery(BaseModel):
    """Parameters for Liquity protocol queries"""
    async_query: bool = Field(default=True)


class LoopringQuery(BaseModel):
    """Parameters for Loopring queries"""
    async_query: bool = Field(default=True)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/blockchains/ethereum/modules/{module_name}/balances", response_model=dict)
async def get_evm_module_balances(
    module_name: str,
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get balances for specific EVM modules (Sushiswap, Balancer, etc.)"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Validate module name
        if module_name not in ['sushiswap', 'balancer', 'uniswap', 'compound']:
            return JSONResponse(
                content=create_error_response(f"Unknown module: {module_name}"),
                status_code=400,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{module_name}_balances',
                method=rest_api.rotkehlchen.chains_aggregator.get_module_balances,
                module_name=module_name,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_module_balances,
            module_name=module_name,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting {module_name} balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/uniswap/{version}/balances", response_model=dict)
async def get_uniswap_balances(
    version: str,
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Uniswap balances for specific version (v2/v3)"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Validate version
        if version not in ['v2', 'v3']:
            return JSONResponse(
                content=create_error_response(f"Invalid Uniswap version: {version}"),
                status_code=400,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_uniswap_{version}_balances',
                method=rest_api.rotkehlchen.chains_aggregator.get_uniswap_balances,
                version=version,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_uniswap_balances,
            version=version,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Uniswap {version} balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/loopring/balances", response_model=dict)
async def get_loopring_balances(
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Loopring L2 balances"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_loopring_balances',
                method=rest_api.rotkehlchen.chains_aggregator.get_loopring_balances,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_loopring_balances,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Loopring balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/liquity/troves", response_model=dict)
async def get_liquity_troves(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Liquity trove positions"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_liquity_troves',
                method=rest_api.rotkehlchen.chains_aggregator.get_liquity_troves,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_liquity_troves,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Liquity troves: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/liquity/staking", response_model=dict)
async def get_liquity_staking(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Liquity staking data"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_liquity_staking',
                method=rest_api.rotkehlchen.chains_aggregator.get_liquity_staking,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_liquity_staking,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Liquity staking: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/liquity/pool", response_model=dict)
async def get_liquity_stability_pool(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Liquity stability pool positions"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_liquity_stability_pool',
                method=rest_api.rotkehlchen.chains_aggregator.get_liquity_stability_pool,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_liquity_stability_pool,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Liquity stability pool: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/pickle/dill", response_model=dict)
async def get_pickle_dill_balance(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Pickle Finance DILL balance"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_pickle_dill',
                method=rest_api.rotkehlchen.chains_aggregator.get_pickle_dill_balance,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_pickle_dill_balance,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Pickle DILL balance: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/blockchains/ethereum/modules/liquity/stats", response_model=dict)
async def get_liquity_stats(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Liquity protocol statistics"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_liquity_stats',
                method=rest_api.rotkehlchen.chains_aggregator.get_liquity_stats,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_liquity_stats,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting Liquity stats: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/defi/metadata", response_model=dict)
async def get_defi_metadata(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get DeFi protocol metadata"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get DeFi metadata
        metadata = rest_api.rotkehlchen.get_defi_metadata()
        
        return create_success_response(metadata)
        
    except Exception as e:
        log.error(f"Error getting DeFi metadata: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']