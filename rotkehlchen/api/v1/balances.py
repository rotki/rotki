"""Async implementation of balance endpoints

This module provides high-performance async balance querying.
"""
import asyncio
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.v1.dependencies import get_rotkehlchen
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.balances.manual import ManuallyTrackedBalance
# APIError was removed, using HTTPException instead
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['balances'])


# Import dependency injection
from rotkehlchen.api.v1.dependencies import get_rotkehlchen


@router.get('/balances', response_model=dict)
async def get_all_balances(
    save_data: bool = Query(default=False),
    ignore_cache: bool = Query(default=False),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get all balances across all accounts"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_all_balances',
                method=rotkehlchen.query_balances,
                save_data=save_data,
                ignore_cache=ignore_cache,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.query_balances,
            save_data=save_data,
            ignore_cache=ignore_cache,
        )

        return create_success_response(result)

    except HTTPException as e:
        return JSONResponse(
            content=create_error_response(e.detail),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f'Error querying all balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/balances/blockchains/{blockchain}', response_model=dict)
async def get_blockchain_balances(
    blockchain: str,
    ignore_cache: bool = Query(default=False),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get balances for a specific blockchain"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate blockchain
        try:
            blockchain_obj = rotkehlchen.chains_aggregator.get_chain(blockchain)
        except KeyError:
            return JSONResponse(
                content=create_error_response(f'Unknown blockchain: {blockchain}'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
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

    except HTTPException as e:
        return JSONResponse(
            content=create_error_response(e.detail),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f'Error querying {blockchain} balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/balances/manual', response_model=dict)
async def get_manual_balances(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get manually tracked balances"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get manual balances from database
        with rotkehlchen.data.db.conn.read_ctx() as cursor:
            manual_balances = rotkehlchen.data.db.get_manually_tracked_balances(cursor)

        # Format response
        balances = [{
                'id': balance.id,
                'location': str(balance.location),
                'label': balance.label,
                'asset': balance.asset.identifier,
                'amount': str(balance.amount),
                'tags': balance.tags,
            } for balance in manual_balances]

        return create_success_response({'balances': balances})

    except Exception as e:
        log.error(f'Error getting manual balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/balances/manual', response_model=dict)
async def add_manual_balance(
    location: str = Query(...),
    label: str = Query(...),
    asset: str = Query(...),
    amount: str = Query(...),
    tags: list[str] | None = Query(default=None),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Add a manually tracked balance"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate inputs
        try:
            location_obj = Location.deserialize(location)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid location: {e}'),
                status_code=400,
            )

        try:
            asset_obj = rotkehlchen.resolve_asset(asset)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid asset: {e}'),
                status_code=400,
            )

        try:
            amount_val = FVal(amount)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid amount: {e}'),
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
        with rotkehlchen.data.db.user_write() as write_cursor:
            rotkehlchen.data.db.add_manually_tracked_balances(write_cursor, [balance])

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error adding manual balance: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/balances/manual', response_model=dict)
async def delete_manual_balance(
    ids: list[int] = Query(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Delete manually tracked balances"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Delete from database
        with rotkehlchen.data.db.user_write() as write_cursor:
            rotkehlchen.data.db.remove_manually_tracked_balances(write_cursor, ids)

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error deleting manual balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/balances/historical', response_model=dict)
async def get_historical_balances(
    timestamp: int = Query(..., ge=0),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get balances at a specific timestamp"""

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_historical_balances',
                method=rotkehlchen.query_balances_at_timestamp,
                timestamp=Timestamp(timestamp),
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.query_balances_at_timestamp,
            timestamp=Timestamp(timestamp),
        )

        return create_success_response(result)

    except HTTPException as e:
        return JSONResponse(
            content=create_error_response(e.detail),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f'Error querying historical balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
