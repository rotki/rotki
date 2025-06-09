"""Async implementation of assets management endpoints

Provides high-performance asset querying and management.
"""
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    AssetModel,
    CreateAssetModel,
    EditAssetModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.assets.asset import Asset, AssetWithNameAndType
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants import ZERO
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, EvmTokenKind, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1/assets", tags=["assets"])


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


async def get_async_db() -> AsyncDBHandler:
    """Get async database handler - will be injected by the app"""
    raise NotImplementedError("AsyncDBHandler injection not configured")


@router.get("/all", response_model=dict)
async def get_all_assets(
    # Query parameters
    asset_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=10000),
    offset: Optional[int] = Query(None, ge=0),
    # Dependencies
    rest_api: RestAPI = Depends(get_rest_api),
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Get all assets with optional filtering"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Run in thread pool for compatibility
        loop = asyncio.get_event_loop()
        
        def _get_assets():
            # Use GlobalDB to get assets
            globaldb = GlobalDBHandler()
            
            # Apply filters
            filters = {}
            if asset_type:
                filters['asset_type'] = AssetType.deserialize(asset_type)
                
            # Get assets
            assets_list = globaldb.get_all_assets(
                limit=limit,
                offset=offset,
                **filters
            )
            
            # Convert to response format
            assets_data = []
            for asset in assets_list:
                assets_data.append({
                    'identifier': asset.identifier,
                    'name': asset.name,
                    'symbol': asset.symbol,
                    'asset_type': asset.asset_type.serialize(),
                })
                
            return assets_data
            
        assets = await loop.run_in_executor(None, _get_assets)
        
        return create_success_response({
            'entries': assets,
            'entries_found': len(assets),
            'entries_limit': limit or -1,
            'entries_total': len(assets),  # Would need proper total count
        })
        
    except Exception as e:
        log.error(f"Error getting assets: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/search", response_model=dict)
async def search_assets(
    # Search parameters
    search_query: str = Query(..., min_length=1),
    search_type: str = Query("all", regex="^(all|name|symbol)$"),
    limit: int = Query(50, ge=1, le=100),
    # Dependencies
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Search for assets by name or symbol"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _search_assets():
            globaldb = GlobalDBHandler()
            
            # Perform search
            if search_type == "name":
                results = globaldb.search_assets_by_name(search_query, limit)
            elif search_type == "symbol":
                results = globaldb.search_assets_by_symbol(search_query, limit)
            else:
                # Search both
                name_results = globaldb.search_assets_by_name(search_query, limit // 2)
                symbol_results = globaldb.search_assets_by_symbol(search_query, limit // 2)
                
                # Combine and deduplicate
                seen = set()
                results = []
                for asset in name_results + symbol_results:
                    if asset.identifier not in seen:
                        seen.add(asset.identifier)
                        results.append(asset)
                        
            return results
            
        search_results = await loop.run_in_executor(None, _search_assets)
        
        # Format results
        formatted_results = []
        for asset in search_results:
            formatted_results.append({
                'identifier': asset.identifier,
                'name': asset.name,
                'symbol': asset.symbol,
                'asset_type': asset.asset_type.serialize(),
            })
            
        return create_success_response(formatted_results)
        
    except Exception as e:
        log.error(f"Error searching assets: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/{asset_identifier}", response_model=dict)
async def get_asset_details(
    asset_identifier: str,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get detailed information about a specific asset"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _get_asset_details():
            try:
                asset = Asset(asset_identifier).resolve_to_asset_with_name_and_type()
                
                # Get additional details
                globaldb = GlobalDBHandler()
                
                details = {
                    'identifier': asset.identifier,
                    'name': asset.name,
                    'symbol': asset.symbol,
                    'asset_type': asset.asset_type.serialize(),
                }
                
                # Add type-specific details
                if asset.asset_type == AssetType.EVM_TOKEN:
                    token_data = globaldb.get_evm_token(asset.identifier)
                    if token_data:
                        details.update({
                            'evm_chain': token_data.chain.serialize(),
                            'token_kind': token_data.token_kind.serialize(),
                            'decimals': token_data.decimals,
                            'protocol': token_data.protocol,
                        })
                        
                return details
                
            except UnknownAsset:
                return None
                
        asset_details = await loop.run_in_executor(None, _get_asset_details)
        
        if asset_details is None:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{asset_identifier}' not found"
            )
            
        return create_success_response(asset_details)
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting asset details: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/custom", response_model=dict)
async def add_custom_asset(
    asset_data: CreateAssetModel,
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Add a new custom asset"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Validate asset doesn't exist
        try:
            existing = Asset(asset_data.identifier)
            return JSONResponse(
                content=create_error_response(
                    f"Asset '{asset_data.identifier}' already exists"
                ),
                status_code=400,
            )
        except UnknownAsset:
            pass  # Good, asset doesn't exist
            
        # Add custom asset to database
        async with async_db.async_conn.write_ctx() as cursor:
            await cursor.execute(
                """
                INSERT INTO user_owned_assets (
                    identifier, name, symbol, asset_type,
                    started, swapped_for, coingecko, cryptocompare,
                    field1, field2, field3, field4, field5
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_data.identifier,
                    asset_data.name,
                    asset_data.symbol,
                    asset_data.asset_type,
                    asset_data.started,
                    asset_data.swapped_for,
                    asset_data.coingecko,
                    asset_data.cryptocompare,
                    asset_data.field1,
                    asset_data.field2,
                    asset_data.field3,
                    asset_data.field4,
                    asset_data.field5,
                )
            )
            
        return create_success_response({
            'identifier': asset_data.identifier,
            'name': asset_data.name,
            'symbol': asset_data.symbol,
        }, status_code=201)
        
    except Exception as e:
        log.error(f"Error adding custom asset: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/custom/{asset_identifier}", response_model=dict)
async def edit_custom_asset(
    asset_identifier: str,
    asset_updates: EditAssetModel,
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Edit an existing custom asset"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if asset exists and is custom
        async with async_db.async_conn.read_ctx() as cursor:
            await cursor.execute(
                "SELECT identifier FROM user_owned_assets WHERE identifier = ?",
                (asset_identifier,)
            )
            if not await cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail=f"Custom asset '{asset_identifier}' not found"
                )
                
        # Build update query
        updates = []
        params = []
        
        for field, value in asset_updates.model_dump(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)
                
        if not updates:
            return create_success_response({"message": "No updates provided"})
            
        params.append(asset_identifier)
        
        # Update asset
        async with async_db.async_conn.write_ctx() as cursor:
            await cursor.execute(
                f"UPDATE user_owned_assets SET {', '.join(updates)} WHERE identifier = ?",
                tuple(params)
            )
            
        return create_success_response({"message": "Asset updated successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error editing custom asset: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/custom/{asset_identifier}", response_model=dict)
async def delete_custom_asset(
    asset_identifier: str,
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Delete a custom asset"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Delete asset
        async with async_db.async_conn.write_ctx() as cursor:
            await cursor.execute(
                "DELETE FROM user_owned_assets WHERE identifier = ?",
                (asset_identifier,)
            )
            
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"Custom asset '{asset_identifier}' not found"
                )
                
        return create_success_response({"message": "Asset deleted successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting custom asset: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/prices/current", response_model=dict)
async def get_current_asset_prices(
    assets: list[str] = Query(...),
    target_asset: str = Query("USD"),
    ignore_cache: bool = Query(False),
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get current prices for multiple assets"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _get_prices():
            from rotkehlchen.inquirer import Inquirer
            inquirer = Inquirer()
            
            prices = {}
            target = Asset(target_asset)
            
            for asset_id in assets:
                try:
                    asset = Asset(asset_id)
                    price = inquirer.find_price(
                        from_asset=asset,
                        to_asset=target,
                        ignore_cache=ignore_cache,
                    )
                    prices[asset_id] = str(price)
                except Exception as e:
                    log.warning(f"Failed to get price for {asset_id}: {e}")
                    prices[asset_id] = None
                    
            return prices
            
        price_data = await loop.run_in_executor(None, _get_prices)
        
        return create_success_response({
            'assets': price_data,
            'target_asset': target_asset,
            'oracles_queried': ['coingecko', 'cryptocompare'],  # Would track actual
        })
        
    except Exception as e:
        log.error(f"Error getting asset prices: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router for inclusion
__all__ = ['router']