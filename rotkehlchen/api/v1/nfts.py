"""Async implementation of NFT-related endpoints

This module provides high-performance async NFT operations.
"""
import asyncio
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.v1.dependencies import get_rotkehlchen
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['nfts'])


# Pydantic models
class NFTQuery(BaseModel):
    """Parameters for NFT queries"""
    async_query: bool = Field(default=True)
    ignore_cache: bool = Field(default=False)
    addresses: list[str] | None = None


class NFTBalanceQuery(BaseModel):
    """Parameters for NFT balance queries"""
    async_query: bool = Field(default=True)
    ignore_cache: bool = Field(default=False)


class NFTPriceQuery(BaseModel):
    """Parameters for NFT price queries"""
    nfts: list[dict] = Field(..., min_items=1)
    async_query: bool = Field(default=True)


# Dependency injection
async def get_rotkehlchen() -> "Rotkehlchen":
    """Get Rotkehlchen instance - will be injected by the app"""
    raise NotImplementedError('Rotkehlchen injection not configured')


@router.get('/nfts', response_model=dict)
async def get_nfts(
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    addresses: str | None = Query(default=None),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get NFTs for user accounts"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse addresses if provided
        address_list = None
        if addresses:
            try:
                address_list = [string_to_evm_address(addr.strip()) for addr in addresses.split(',')]
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid address: {e}'),
                    status_code=400,
                )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_nfts',
                method=rotkehlchen.nft_manager.get_nfts,
                addresses=address_list,
                ignore_cache=ignore_cache,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.nft_manager.get_nfts,
            addresses=address_list,
            ignore_cache=ignore_cache,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting NFTs: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/nfts/balances', response_model=dict)
async def get_nft_balances(
    query: NFTBalanceQuery,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get NFT balances for user accounts"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        if query.async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_nft_balances',
                method=rotkehlchen.nft_manager.get_balances,
                ignore_cache=query.ignore_cache,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.nft_manager.get_balances,
            ignore_cache=query.ignore_cache,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting NFT balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/nfts/prices', response_model=dict)
async def get_nft_prices(
    query: NFTPriceQuery,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get current prices for specific NFTs"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate NFT data
        nft_identifiers = []
        try:
            for nft_data in query.nfts:
                if 'token_identifier' not in nft_data:
                    return JSONResponse(
                        content=create_error_response('token_identifier is required for each NFT'),
                        status_code=400,
                    )
                nft_identifiers.append(nft_data['token_identifier'])
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid NFT data: {e}'),
                status_code=400,
            )

        if query.async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_nft_prices',
                method=rotkehlchen.nft_manager.get_current_price,
                nft_identifiers=nft_identifiers,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.nft_manager.get_current_price,
            nft_identifiers=nft_identifiers,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting NFT prices: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
