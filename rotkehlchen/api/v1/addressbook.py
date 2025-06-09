"""Async implementation of address book and ENS endpoints

This module provides high-performance async address book and ENS operations.
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
from rotkehlchen.types import ChecksumEvmAddress, ChainAddress, Blockchain
from rotkehlchen.chain.evm.types import string_to_evm_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["addressbook"])


# Pydantic models
class AddressBookEntry(BaseModel):
    """Data for address book entries"""
    name: str
    address: str
    blockchain: Optional[str] = None
    notes: Optional[str] = None


class AddressBookUpdate(BaseModel):
    """Data for updating address book entries"""
    entries: list[AddressBookEntry]


class QueriedAddressData(BaseModel):
    """Data for managing queried addresses"""
    module: str
    address: str


class EnsLookup(BaseModel):
    """Data for ENS lookups"""
    name: Optional[str] = None
    address: Optional[str] = None
    blockchain: str = Field(default="ethereum")


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/addressbook", response_model=dict)
async def get_addressbook(
    blockchain: Optional[str] = Query(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get address book entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get address book entries
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            entries = rest_api.rotkehlchen.data.db.get_addressbook_entries(
                cursor,
                blockchain=Blockchain.deserialize(blockchain) if blockchain else None,
            )
        
        # Format response
        result = []
        for entry in entries:
            result.append({
                'name': entry.name,
                'address': entry.address,
                'blockchain': entry.blockchain.value if entry.blockchain else None,
                'notes': entry.notes,
            })
        
        return create_success_response({'entries': result})
        
    except Exception as e:
        log.error(f"Error getting address book: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/addressbook", response_model=dict)
async def add_addressbook_entries(
    entries_data: AddressBookUpdate,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add address book entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Add entries
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            for entry in entries_data.entries:
                rest_api.rotkehlchen.data.db.add_addressbook_entry(
                    write_cursor,
                    name=entry.name,
                    address=ChainAddress(
                        address=entry.address,
                        blockchain=Blockchain.deserialize(entry.blockchain) if entry.blockchain else None,
                    ),
                    notes=entry.notes,
                )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error adding address book entries: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/addressbook", response_model=dict)
async def update_addressbook_entries(
    entries_data: AddressBookUpdate,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Update address book entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Update entries
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            for entry in entries_data.entries:
                rest_api.rotkehlchen.data.db.update_addressbook_entry(
                    write_cursor,
                    old_address=ChainAddress(
                        address=entry.address,
                        blockchain=Blockchain.deserialize(entry.blockchain) if entry.blockchain else None,
                    ),
                    name=entry.name,
                    notes=entry.notes,
                )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error updating address book entries: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/addressbook", response_model=dict)
async def edit_addressbook_entry(
    entry_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit a single address book entry"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Edit entry
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.edit_addressbook_entry(
                write_cursor,
                entry_data=entry_data,
            )
        
        if not success:
            return JSONResponse(
                content=create_error_response("Address book entry not found"),
                status_code=404,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error editing address book entry: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/addressbook", response_model=dict)
async def delete_addressbook_entries(
    addresses: list[str] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete address book entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete entries
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            deleted_count = rest_api.rotkehlchen.data.db.delete_addressbook_entries(
                write_cursor,
                addresses=addresses,
            )
        
        return create_success_response({
            'result': True,
            'deleted': deleted_count,
        })
        
    except Exception as e:
        log.error(f"Error deleting address book entries: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/queried_addresses", response_model=dict)
async def get_queried_addresses(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get addresses queried by modules"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get queried addresses
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            addresses = rest_api.rotkehlchen.data.db.get_queried_addresses(cursor)
        
        # Format response
        result = {}
        for module, addrs in addresses.items():
            result[module] = [str(addr) for addr in addrs]
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error getting queried addresses: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/queried_addresses", response_model=dict)
async def add_queried_address(
    address_data: QueriedAddressData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a queried address for a module"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Add queried address
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.add_queried_address(
                write_cursor,
                module=address_data.module,
                address=string_to_evm_address(address_data.address),
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error adding queried address: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/queried_addresses", response_model=dict)
async def remove_queried_addresses(
    module: str = Body(...),
    addresses: list[str] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Remove queried addresses for a module"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Remove queried addresses
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            removed_count = rest_api.rotkehlchen.data.db.remove_queried_addresses(
                write_cursor,
                module=module,
                addresses=[string_to_evm_address(addr) for addr in addresses],
            )
        
        return create_success_response({
            'result': True,
            'removed': removed_count,
        })
        
    except Exception as e:
        log.error(f"Error removing queried addresses: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/ens/avatars", response_model=dict)
async def get_ens_avatars(
    addresses: str = Query(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get ENS avatars for addresses"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Parse addresses
        address_list = [string_to_evm_address(addr.strip()) for addr in addresses.split(',')]
        
        # Get ENS avatars
        avatars = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_ens_avatars,
            addresses=address_list,
        )
        
        return create_success_response(avatars)
        
    except Exception as e:
        log.error(f"Error getting ENS avatars: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/ens/resolve", response_model=dict)
async def resolve_ens_name(
    ens_data: EnsLookup,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Resolve ENS name to address"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if not ens_data.name:
            return JSONResponse(
                content=create_error_response("ENS name is required"),
                status_code=400,
            )
        
        # Resolve ENS name
        blockchain = Blockchain.deserialize(ens_data.blockchain)
        address = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.resolve_ens_name,
            name=ens_data.name,
            blockchain=blockchain,
        )
        
        if not address:
            return JSONResponse(
                content=create_error_response(f"Could not resolve ENS name {ens_data.name}"),
                status_code=404,
            )
        
        return create_success_response({'address': str(address)})
        
    except Exception as e:
        log.error(f"Error resolving ENS name: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/ens/reverse", response_model=dict)
async def reverse_ens_lookup(
    ens_data: EnsLookup,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Reverse ENS lookup - get name from address"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        if not ens_data.address:
            return JSONResponse(
                content=create_error_response("Address is required"),
                status_code=400,
            )
        
        # Reverse ENS lookup
        blockchain = Blockchain.deserialize(ens_data.blockchain)
        name = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.reverse_ens_lookup,
            address=string_to_evm_address(ens_data.address),
            blockchain=blockchain,
        )
        
        if not name:
            return JSONResponse(
                content=create_error_response(f"No ENS name found for {ens_data.address}"),
                status_code=404,
            )
        
        return create_success_response({'name': name})
        
    except Exception as e:
        log.error(f"Error in reverse ENS lookup: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']