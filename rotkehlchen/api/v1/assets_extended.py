"""Async implementation of extended asset endpoints

This module provides high-performance async asset management operations.
"""
import asyncio
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.v1.dependencies import get_rotkehlchen
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.constants import ZERO
from rotkehlchen.types import Price, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['assets'])


# Pydantic models
class AssetSearchParams(BaseModel):
    """Parameters for asset search"""
    value: str = Field(..., min_length=1, description='Search value')
    column: str = Field(default='name', description='Column to search in')
    limit: int = Field(default=25, ge=1, le=100, description='Maximum results')


class AssetUpdateCheck(BaseModel):
    """Parameters for checking asset updates"""
    up_to_version: int | None = Field(default=None, description='Check updates up to version')
    async_query: bool = Field(default=False, description='Run as async task')


class CustomAssetData(BaseModel):
    """Data for creating/updating custom assets"""
    identifier: str
    name: str
    custom_asset_type: str
    notes: str | None = None
    symbol: str | None = None
    started: Timestamp | None = None
    coingecko: str | None = None
    cryptocompare: str | None = None
    manual_price: bool | None = None
    price_feed: str | None = None


# Dependency injection
async def get_rotkehlchen() -> "Rotkehlchen":
    """Get Rotkehlchen instance - will be injected by the app"""
    raise NotImplementedError('Rotkehlchen injection not configured')


@router.get('/assets/all', response_model=dict)
async def get_all_assets(
    asset_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    offset: int | None = Query(default=0, ge=0),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get list of all known assets"""
    try:
        # Parse asset type if provided
        asset_type_filter = None
        if asset_type:
            try:
                asset_type_filter = AssetType.deserialize(asset_type)
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid asset type: {e}'),
                    status_code=400,
                )

        # Get assets from global DB
        async with GlobalDBHandler().conn.read_ctx() as cursor:
            if asset_type_filter:
                assets = await GlobalDBHandler().get_all_asset_data(
                    cursor=cursor,
                    mapping=False,
                    serialized=True,
                    specific_ids=None,
                    asset_type=asset_type_filter,
                )
            else:
                assets = await GlobalDBHandler().get_all_asset_data(
                    cursor=cursor,
                    mapping=False,
                    serialized=True,
                )

        # Apply pagination
        total_assets = len(assets)
        if limit is not None:
            start = offset
            end = offset + limit
            assets = assets[start:end]

        return create_success_response({
            'assets': assets,
            'total': total_assets,
            'limit': limit,
            'offset': offset,
        })

    except Exception as e:
        log.error(f'Error getting all assets: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/assets/types', response_model=dict)
async def get_asset_types(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get list of valid asset types"""
    try:
        # Get all asset types
        asset_types = [t.serialize() for t in AssetType]

        return create_success_response(asset_types)

    except Exception as e:
        log.error(f'Error getting asset types: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/assets/search', response_model=dict)
async def search_assets(
    params: AssetSearchParams,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Search for assets by name, symbol, or other attributes"""
    try:
        # Validate column
        valid_columns = ['name', 'symbol', 'identifier']
        if params.column not in valid_columns:
            return JSONResponse(
                content=create_error_response(f'Invalid column. Must be one of: {valid_columns}'),
                status_code=400,
            )

        # Search in global DB
        with GlobalDBHandler().conn.read_ctx() as cursor:
            # Simple search implementation
            query = f"""
                SELECT identifier, name, symbol, asset_type
                FROM common_asset_details
                WHERE {params.column} LIKE ?
                LIMIT ?
            """
            cursor.execute(query, (f'%{params.value}%', params.limit))

            results = [{
                    'identifier': row[0],
                    'name': row[1],
                    'symbol': row[2],
                    'asset_type': row[3],
                } for row in cursor]

        return create_success_response({
            'results': results,
            'search_term': params.value,
            'column': params.column,
        })

    except Exception as e:
        log.error(f'Error searching assets: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/assets/ignored', response_model=dict)
async def get_ignored_assets(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get list of ignored assets"""
    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get ignored assets from database
        with rotkehlchen.data.db.conn.read_ctx() as cursor:
            ignored_assets = rotkehlchen.data.db.get_ignored_asset_ids(cursor)

        return create_success_response(list(ignored_assets))

    except Exception as e:
        log.error(f'Error getting ignored assets: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/assets/ignored', response_model=dict)
async def add_ignored_assets(
    assets: list[str] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Add assets to ignore list"""
    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate assets exist
        invalid_assets = []
        for asset_id in assets:
            try:
                Asset(asset_id)
            except UnknownAsset:
                invalid_assets.append(asset_id)

        if invalid_assets:
            return JSONResponse(
                content=create_error_response(f'Unknown assets: {invalid_assets}'),
                status_code=400,
            )

        # Add to ignored list
        with rotkehlchen.data.db.user_write() as write_cursor:
            for asset_id in assets:
                rotkehlchen.data.db.add_to_ignored_assets(write_cursor, Asset(asset_id))

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error adding ignored assets: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/assets/ignored', response_model=dict)
async def remove_ignored_assets(
    assets: list[str] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Remove assets from ignore list"""
    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Remove from ignored list
        with rotkehlchen.data.db.user_write() as write_cursor:
            for asset_id in assets:
                try:
                    asset = Asset(asset_id)
                    rotkehlchen.data.db.remove_from_ignored_assets(write_cursor, asset)
                except UnknownAsset:
                    # Skip unknown assets silently
                    pass

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error removing ignored assets: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/assets/prices/latest', response_model=dict)
async def get_latest_asset_prices(
    assets: list[str] = Query(...),
    target_asset: str = Query(default='USD'),
    ignore_cache: bool = Query(default=False),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get latest prices for given assets"""
    try:
        # Validate assets
        asset_objects = []
        for asset_id in assets:
            try:
                asset_objects.append(AssetWithOracles(asset_id))
            except UnknownAsset:
                return JSONResponse(
                    content=create_error_response(f'Unknown asset: {asset_id}'),
                    status_code=400,
                )

        # Validate target asset
        try:
            target = Asset(target_asset)
        except UnknownAsset:
            return JSONResponse(
                content=create_error_response(f'Unknown target asset: {target_asset}'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_latest_asset_prices',
                method=rotkehlchen.inquirer.query_prices,
                assets=asset_objects,
                target_asset=target,
                ignore_cache=ignore_cache,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        prices = {}
        for asset in asset_objects:
            price = rotkehlchen.inquirer.find_price(
                from_asset=asset,
                to_asset=target,
                ignore_cache=ignore_cache,
            )
            prices[asset.identifier] = str(price) if price != Price(ZERO) else None

        return create_success_response({
            'assets': prices,
            'target_asset': target_asset,
        })

    except Exception as e:
        log.error(f'Error getting latest asset prices: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/assets/prices/historical', response_model=dict)
async def get_historical_asset_price(
    assets: list[str] = Body(...),
    target_asset: str = Body(default='USD'),
    timestamp: int = Body(..., ge=0),
    async_query: bool = Body(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get historical price for assets at specific timestamp"""
    try:
        # Validate assets
        asset_objects = []
        for asset_id in assets:
            try:
                asset_objects.append(Asset(asset_id))
            except UnknownAsset:
                return JSONResponse(
                    content=create_error_response(f'Unknown asset: {asset_id}'),
                    status_code=400,
                )

        # Validate target asset
        try:
            target = Asset(target_asset)
        except UnknownAsset:
            return JSONResponse(
                content=create_error_response(f'Unknown target asset: {target_asset}'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_historical_prices',
                method=rotkehlchen.query_historical_prices,
                assets=asset_objects,
                target_asset=target,
                timestamp=Timestamp(timestamp),
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        historian = PriceHistorian()
        prices = {}

        for asset in asset_objects:
            price = historian.query_historical_price(
                from_asset=asset,
                to_asset=target,
                timestamp=Timestamp(timestamp),
            )
            prices[asset.identifier] = str(price) if price != Price(ZERO) else None

        return create_success_response({
            'assets': prices,
            'target_asset': target_asset,
            'timestamp': timestamp,
        })

    except Exception as e:
        log.error(f'Error getting historical prices: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/assets/updates', response_model=dict)
async def check_for_asset_updates(
    params: AssetUpdateCheck,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Check for asset database updates"""
    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        if params.async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='check_asset_updates',
                method=rotkehlchen.check_for_asset_updates,
                up_to_version=params.up_to_version,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous check
        result = await asyncio.to_thread(
            rotkehlchen.check_for_asset_updates,
            up_to_version=params.up_to_version,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error checking for asset updates: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
