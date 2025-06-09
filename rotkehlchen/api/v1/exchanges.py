"""Async implementation of exchange endpoints

This module provides high-performance async exchange operations.
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
from fastapi import HTTPException
from rotkehlchen.constants.timing import TIMESTAMP_MAX_VALUE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['exchanges'])


# Pydantic models for exchange operations
class ExchangeCredentials(BaseModel):
    """Model for exchange credentials"""
    name: str = Field(..., description='Exchange instance name')
    location: str = Field(..., description='Exchange location')
    api_key: str = Field(..., description='API key')
    api_secret: str = Field(..., description='API secret')
    passphrase: str | None = Field(default=None, description='API passphrase (if required)')
    kraken_account_type: str | None = Field(default=None, description='Kraken account type')
    binance_selected_trade_pairs: list[str] | None = Field(default=None, description='Binance pairs to track')


class ExchangeEdit(BaseModel):
    """Model for editing exchange"""
    name: str = Field(..., description='Exchange instance name')
    new_name: str | None = Field(default=None, description='New name for the exchange')
    location: str = Field(..., description='Exchange location')
    api_key: str | None = Field(default=None, description='New API key')
    api_secret: str | None = Field(default=None, description='New API secret')
    passphrase: str | None = Field(default=None, description='New API passphrase')
    kraken_account_type: str | None = Field(default=None, description='Kraken account type')
    binance_selected_trade_pairs: list[str] | None = Field(default=None, description='Binance pairs')


# Dependency injection
async def get_rotkehlchen() -> "Rotkehlchen":
    """Get Rotkehlchen instance - will be injected by the app"""
    raise NotImplementedError('Rotkehlchen injection not configured')


@router.get('/exchanges', response_model=dict)
async def get_exchanges(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get list of connected exchanges"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get connected exchanges
        exchanges_list = []
        for exchange_name, exchange_obj in rotkehlchen.exchange_manager.connected_exchanges.items():
            exchanges_list.append({
                'name': exchange_name,
                'location': str(exchange_obj.location),
                'type': exchange_obj.location.value,
            })

        return create_success_response(exchanges_list)

    except Exception as e:
        log.error(f'Error getting exchanges: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/exchanges', response_model=dict)
async def add_exchange(
    credentials: ExchangeCredentials,
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Add a new exchange connection"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate location
        try:
            location = Location.deserialize(credentials.location)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid location: {e}'),
                status_code=400,
            )

        if location not in SUPPORTED_EXCHANGES:
            return JSONResponse(
                content=create_error_response(f'Unsupported exchange: {location}'),
                status_code=400,
            )

        # Check if exchange already exists
        if credentials.name in rotkehlchen.exchange_manager.connected_exchanges:
            return JSONResponse(
                content=create_error_response(f'Exchange {credentials.name} already exists'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name=f'add_exchange_{credentials.name}',
                method=rotkehlchen.exchange_manager.setup_exchange,
                name=credentials.name,
                location=location,
                api_key=credentials.api_key,
                api_secret=credentials.api_secret,
                passphrase=credentials.passphrase,
                kraken_account_type=credentials.kraken_account_type,
                binance_selected_trade_pairs=credentials.binance_selected_trade_pairs,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous add
        result = await asyncio.to_thread(
            rotkehlchen.exchange_manager.setup_exchange,
            name=credentials.name,
            location=location,
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            passphrase=credentials.passphrase,
            kraken_account_type=credentials.kraken_account_type,
            binance_selected_trade_pairs=credentials.binance_selected_trade_pairs,
        )

        return create_success_response({'result': result})

    except RemoteError as e:
        return JSONResponse(
            content=create_error_response(f'Exchange connection failed: {e}'),
            status_code=502,
        )
    except Exception as e:
        log.error(f'Error adding exchange: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/exchanges', response_model=dict)
async def edit_exchange(
    exchange_edit: ExchangeEdit,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Edit an existing exchange connection"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check if exchange exists
        if exchange_edit.name not in rotkehlchen.exchange_manager.connected_exchanges:
            return JSONResponse(
                content=create_error_response(f'Exchange {exchange_edit.name} not found'),
                status_code=404,
            )

        # Edit exchange
        result = await asyncio.to_thread(
            rotkehlchen.exchange_manager.edit_exchange,
            name=exchange_edit.name,
            new_name=exchange_edit.new_name,
            api_key=exchange_edit.api_key,
            api_secret=exchange_edit.api_secret,
            passphrase=exchange_edit.passphrase,
            kraken_account_type=exchange_edit.kraken_account_type,
            binance_selected_trade_pairs=exchange_edit.binance_selected_trade_pairs,
        )

        return create_success_response({'result': result})

    except Exception as e:
        log.error(f'Error editing exchange: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/exchanges/{name}', response_model=dict)
async def remove_exchange(
    name: str,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Remove an exchange connection"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check if exchange exists
        if name not in rotkehlchen.exchange_manager.connected_exchanges:
            return JSONResponse(
                content=create_error_response(f'Exchange {name} not found'),
                status_code=404,
            )

        # Remove exchange
        result = await asyncio.to_thread(
            rotkehlchen.exchange_manager.delete_exchange,
            name=name,
        )

        return create_success_response({'result': result})

    except Exception as e:
        log.error(f'Error removing exchange: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/exchanges/balances', response_model=dict)
async def get_exchange_balances(
    location: str | None = Query(default=None),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get balances for exchanges"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate location if provided
        location_obj = None
        if location:
            try:
                location_obj = Location.deserialize(location)
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid location: {e}'),
                    status_code=400,
                )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='query_exchange_balances',
                method=rotkehlchen.query_exchange_balances,
                location=location_obj,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.query_exchange_balances,
            location=location_obj,
        )

        return create_success_response(result)

    except APIError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f'Error querying exchange balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/exchanges/data/{location}', response_model=dict)
async def query_exchange_data(
    location: str,
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(TIMESTAMP_MAX_VALUE, ge=0),
    async_query: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Query exchange historical data (trades, deposits, withdrawals)"""
    if not async_features.is_enabled(AsyncFeature.EXCHANGES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate location
        try:
            location_obj = Location.deserialize(location)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid location: {e}'),
                status_code=400,
            )

        # Check if exchange is connected
        exchange_names = [
            name for name, exchange in rotkehlchen.exchange_manager.connected_exchanges.items()
            if exchange.location == location_obj
        ]

        if not exchange_names:
            return JSONResponse(
                content=create_error_response(f'No {location} exchange connected'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{location}_data',
                method=rotkehlchen.query_exchange_data,
                location=location_obj,
                from_ts=Timestamp(from_timestamp),
                to_ts=Timestamp(to_timestamp),
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rotkehlchen.query_exchange_data,
            location=location_obj,
            from_ts=Timestamp(from_timestamp),
            to_ts=Timestamp(to_timestamp),
        )

        return create_success_response(result)

    except APIError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=e.status_code,
        )
    except Exception as e:
        log.error(f'Error querying exchange data: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
