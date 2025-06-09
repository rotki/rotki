"""Async implementation of utility and miscellaneous endpoints

This module provides high-performance async utility operations.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.errors.api import APIError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["utils"])


# Pydantic models
class RpcNodeData(BaseModel):
    """Data for RPC node configuration"""
    name: str
    endpoint: str
    owned: bool = False
    active: bool = True
    weight: Optional[float] = Field(default=1.0, ge=0.0)
    blockchain: str


class AssetIconUpload(BaseModel):
    """Data for asset icon upload"""
    asset: str
    file: UploadFile


class OracleData(BaseModel):
    """Data for oracle configuration"""
    oracle: str
    active: bool = True


class ProtocolRefreshData(BaseModel):
    """Data for protocol data refresh"""
    async_query: bool = Field(default=True)
    ignore_cache: bool = Field(default=False)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/blockchains/evm/rpc", response_model=dict)
async def get_rpc_nodes(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get configured RPC nodes"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get RPC nodes
        nodes = rest_api.rotkehlchen.get_rpc_nodes()
        
        return create_success_response(nodes)
        
    except Exception as e:
        log.error(f"Error getting RPC nodes: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/blockchains/evm/rpc", response_model=dict)
async def add_rpc_node(
    node_data: RpcNodeData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a new RPC node"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Add RPC node
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.add_rpc_node,
            name=node_data.name,
            endpoint=node_data.endpoint,
            owned=node_data.owned,
            active=node_data.active,
            weight=node_data.weight,
            blockchain=node_data.blockchain,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error adding RPC node: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/blockchains/evm/rpc", response_model=dict)
async def edit_rpc_node(
    node_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit an existing RPC node"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Edit RPC node
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.edit_rpc_node,
            node_data=node_data,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error editing RPC node: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/blockchains/evm/rpc", response_model=dict)
async def delete_rpc_node(
    identifier: str = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete an RPC node"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete RPC node
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.delete_rpc_node,
            identifier=identifier,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error deleting RPC node: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/assets/icon", response_model=dict)
async def upload_asset_icon(
    file: UploadFile = File(...),
    asset: str = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Upload custom asset icon"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Read file content
        content = await file.read()
        
        # Upload icon
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.upload_asset_icon,
            asset=asset,
            file_content=content,
            filename=file.filename,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error uploading asset icon: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/assets/icon/refresh", response_model=dict)
async def refresh_asset_icons(
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Refresh asset icons from external sources"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
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
                task_name='refresh_asset_icons',
                method=rest_api.rotkehlchen.refresh_asset_icons,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous refresh
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.refresh_asset_icons,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error refreshing asset icons: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/oracles", response_model=dict)
async def get_oracles(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get configured oracles"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get oracles
        oracles = rest_api.rotkehlchen.get_oracles()
        
        return create_success_response(oracles)
        
    except Exception as e:
        log.error(f"Error getting oracles: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/oracles", response_model=dict)
async def set_oracle_settings(
    oracle_data: OracleData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Set oracle configuration"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Set oracle configuration
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.set_oracle_settings,
            oracle=oracle_data.oracle,
            active=oracle_data.active,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error setting oracle configuration: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/oracles/{oracle}/cache", response_model=dict)
async def purge_oracle_cache(
    oracle: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Purge oracle cache"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Purge cache
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.purge_oracle_cache,
            oracle=oracle,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error purging oracle cache: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/messages", response_model=dict)
async def get_messages(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get system messages"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get messages
        messages = rest_api.rotkehlchen.get_messages()
        
        return create_success_response(messages)
        
    except Exception as e:
        log.error(f"Error getting messages: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/evm/counterparties", response_model=dict)
async def get_evm_counterparties(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get EVM counterparties"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get counterparties
        counterparties = rest_api.rotkehlchen.get_evm_counterparties()
        
        return create_success_response(counterparties)
        
    except Exception as e:
        log.error(f"Error getting EVM counterparties: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/evm/products", response_model=dict)
async def get_evm_products(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get EVM products"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get products
        products = rest_api.rotkehlchen.get_evm_products()
        
        return create_success_response(products)
        
    except Exception as e:
        log.error(f"Error getting EVM products: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/locations", response_model=dict)
async def get_locations(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get supported locations"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication  
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get locations
        locations = rest_api.rotkehlchen.get_locations()
        
        return create_success_response(locations)
        
    except Exception as e:
        log.error(f"Error getting locations: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/types/mappings", response_model=dict)
async def get_type_mappings(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get type mappings"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get type mappings
        mappings = rest_api.rotkehlchen.get_type_mappings()
        
        return create_success_response(mappings)
        
    except Exception as e:
        log.error(f"Error getting type mappings: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/cache", response_model=dict)
async def clear_cache(
    cache_type: Optional[str] = Query(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Clear application cache"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Clear cache
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.clear_cache,
            cache_type=cache_type,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error clearing cache: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/protocol/data/refresh", response_model=dict)
async def refresh_protocol_data(
    refresh_data: ProtocolRefreshData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Refresh protocol data"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if refresh_data.async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='refresh_protocol_data',
                method=rest_api.rotkehlchen.refresh_protocol_data,
                ignore_cache=refresh_data.ignore_cache,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous refresh
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.refresh_protocol_data,
            ignore_cache=refresh_data.ignore_cache,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error refreshing protocol data: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']