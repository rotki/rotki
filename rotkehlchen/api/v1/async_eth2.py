"""Async implementation of Ethereum 2.0 staking endpoints

This module provides high-performance async ETH2 staking operations.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.feature_flags import AsyncFeature, async_features
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

router = APIRouter(prefix="/api/1", tags=["eth2"])


# Pydantic models
class Eth2ValidatorQuery(BaseModel):
    """Parameters for ETH2 validator queries"""
    async_query: bool = Field(default=True)
    ignore_cache: bool = Field(default=False)


class Eth2StakePerformanceQuery(BaseModel):
    """Parameters for ETH2 stake performance queries"""
    async_query: bool = Field(default=True)
    validators: Optional[list[int]] = None
    from_timestamp: Optional[int] = Field(default=None, ge=0)
    to_timestamp: Optional[int] = Field(default=None, ge=0)


class Eth2DailyStatsQuery(BaseModel):
    """Parameters for ETH2 daily statistics queries"""
    async_query: bool = Field(default=True)
    validators: Optional[list[int]] = None
    from_timestamp: Optional[int] = Field(default=None, ge=0)
    to_timestamp: Optional[int] = Field(default=None, ge=0)


class Eth2ValidatorData(BaseModel):
    """Data for adding ETH2 validators"""
    validator_index: Optional[int] = None
    validator_publickey: Optional[str] = None
    ownership_proportion: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/eth2/validators", response_model=dict)
async def get_eth2_validators(
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get ETH2 validators"""
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
                task_name='query_eth2_validators',
                method=rest_api.rotkehlchen.chains_aggregator.eth2.get_validators,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.get_validators,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting ETH2 validators: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/eth2/validators", response_model=dict)
async def add_eth2_validators(
    validators: list[Eth2ValidatorData],
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add ETH2 validators to track"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Prepare validator data
        validator_data = []
        for validator in validators:
            data = {}
            if validator.validator_index is not None:
                data['validator_index'] = validator.validator_index
            if validator.validator_publickey is not None:
                data['public_key'] = validator.validator_publickey
            if validator.ownership_proportion is not None:
                data['ownership_proportion'] = validator.ownership_proportion
            validator_data.append(data)
        
        # Add validators
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.add_validators,
            validator_data=validator_data,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error adding ETH2 validators: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/eth2/validators", response_model=dict)
async def remove_eth2_validators(
    validators: list[int] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Remove ETH2 validators from tracking"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Remove validators
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.remove_validators,
            validator_indices=validators,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error removing ETH2 validators: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/eth2/stake_performance", response_model=dict)
async def get_eth2_stake_performance(
    async_query: bool = Query(default=True),
    validators: Optional[str] = Query(default=None),
    from_timestamp: Optional[int] = Query(default=None, ge=0),
    to_timestamp: Optional[int] = Query(default=None, ge=0),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get ETH2 staking performance"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Parse validators
        validator_list = None
        if validators:
            try:
                validator_list = [int(v.strip()) for v in validators.split(',')]
            except ValueError as e:
                return JSONResponse(
                    content=create_error_response(f"Invalid validator index: {e}"),
                    status_code=400,
                )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_eth2_stake_performance',
                method=rest_api.rotkehlchen.chains_aggregator.eth2.get_staking_performance,
                validators=validator_list,
                from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
                to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.get_staking_performance,
            validators=validator_list,
            from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
            to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting ETH2 stake performance: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/eth2/daily_stats", response_model=dict)
async def get_eth2_daily_stats(
    async_query: bool = Query(default=True),
    validators: Optional[str] = Query(default=None),
    from_timestamp: Optional[int] = Query(default=None, ge=0),
    to_timestamp: Optional[int] = Query(default=None, ge=0),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get ETH2 daily statistics"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Parse validators
        validator_list = None
        if validators:
            try:
                validator_list = [int(v.strip()) for v in validators.split(',')]
            except ValueError as e:
                return JSONResponse(
                    content=create_error_response(f"Invalid validator index: {e}"),
                    status_code=400,
                )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_eth2_daily_stats',
                method=rest_api.rotkehlchen.chains_aggregator.eth2.get_daily_stats,
                validators=validator_list,
                from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
                to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.get_daily_stats,
            validators=validator_list,
            from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
            to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting ETH2 daily stats: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/eth2/staking_events", response_model=dict)
async def get_eth2_staking_events(
    async_query: bool = Query(default=True),
    validators: Optional[str] = Query(default=None),
    from_timestamp: Optional[int] = Query(default=None, ge=0),
    to_timestamp: Optional[int] = Query(default=None, ge=0),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get ETH2 staking events"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Parse validators
        validator_list = None
        if validators:
            try:
                validator_list = [int(v.strip()) for v in validators.split(',')]
            except ValueError as e:
                return JSONResponse(
                    content=create_error_response(f"Invalid validator index: {e}"),
                    status_code=400,
                )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_eth2_staking_events',
                method=rest_api.rotkehlchen.chains_aggregator.eth2.get_staking_events,
                validators=validator_list,
                from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
                to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.eth2.get_staking_events,
            validators=validator_list,
            from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
            to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting ETH2 staking events: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']