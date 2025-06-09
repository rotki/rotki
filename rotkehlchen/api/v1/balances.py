"""Async implementation of balance endpoints

This module provides high-performance async balance querying.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    BalanceSnapshotModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.ethereum.utils import deserialize_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.api import APIError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["balances"])


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/balances", response_model=dict)
async def get_all_balances(
    save_data: bool = Query(default=False),
    ignore_cache: bool = Query(default=False),
    async_query: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get all balances across all accounts"""
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
                task_name='query_all_balances',
                method=rest_api.rotkehlchen.query_balances,
                save_data=save_data,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.query_balances,
            save_data=save_data,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except APIError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f"Error querying all balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/balances/blockchains/{blockchain}", response_model=dict)
async def get_blockchain_balances(
    blockchain: str,
    ignore_cache: bool = Query(default=False),
    async_query: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get balances for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Validate blockchain
        try:
            blockchain_obj = rest_api.rotkehlchen.chains_aggregator.get_chain(blockchain)
        except KeyError:
            return JSONResponse(
                content=create_error_response(f"Unknown blockchain: {blockchain}"),
                status_code=400,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{blockchain}_balances',
                method=blockchain_obj.query_balances,
                ignore_cache=ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            blockchain_obj.query_balances,
            ignore_cache=ignore_cache,
        )
        
        return create_success_response(result)
        
    except APIError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f"Error querying {blockchain} balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/balances/manual", response_model=dict)
async def get_manual_balances(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get manually tracked balances"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get manual balances from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            manual_balances = rest_api.rotkehlchen.data.db.get_manually_tracked_balances(cursor)
        
        # Format response
        balances = []
        for balance in manual_balances:
            balances.append({
                'id': balance.id,
                'location': str(balance.location),
                'label': balance.label,
                'asset': balance.asset.identifier,
                'amount': str(balance.amount),
                'tags': balance.tags,
            })
        
        return create_success_response({'balances': balances})
        
    except Exception as e:
        log.error(f"Error getting manual balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/balances/manual", response_model=dict)
async def add_manual_balance(
    location: str = Query(...),
    label: str = Query(...),
    asset: str = Query(...),
    amount: str = Query(...),
    tags: list[str] | None = Query(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a manually tracked balance"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Validate inputs
        try:
            location_obj = Location.deserialize(location)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f"Invalid location: {e}"),
                status_code=400,
            )
        
        try:
            asset_obj = rest_api.rotkehlchen.resolve_asset(asset)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f"Invalid asset: {e}"),
                status_code=400,
            )
        
        try:
            amount_val = FVal(amount)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f"Invalid amount: {e}"),
                status_code=400,
            )
        
        # Create manual balance
        balance = ManuallyTrackedBalance(
            location=location_obj,
            label=label,
            asset=asset_obj,
            amount=amount_val,
            tags=tags or [],
        )
        
        # Add to database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.add_manually_tracked_balances(write_cursor, [balance])
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error adding manual balance: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/balances/manual", response_model=dict)
async def delete_manual_balance(
    ids: list[int] = Query(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete manually tracked balances"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete from database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.remove_manually_tracked_balances(write_cursor, ids)
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error deleting manual balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/balances/historical", response_model=dict)
async def get_historical_balances(
    timestamp: int = Query(..., ge=0),
    async_query: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get balances at a specific timestamp"""
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
                task_name='query_historical_balances',
                method=rest_api.rotkehlchen.query_balances_at_timestamp,
                timestamp=Timestamp(timestamp),
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.query_balances_at_timestamp,
            timestamp=Timestamp(timestamp),
        )
        
        return create_success_response(result)
        
    except APIError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f"Error querying historical balances: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']