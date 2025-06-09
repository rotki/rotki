"""Async implementation of miscellaneous endpoints

This module provides various remaining endpoints for complete feature parity.
"""
import asyncio
import logging

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['misc'])


# Pydantic models
class XpubData(BaseModel):
    """Data for xpub management"""
    xpub: str
    label: str | None = None
    tags: list[str] | None = None


class WatcherData(BaseModel):
    """Data for premium watchers"""
    watcher_type: str
    args: dict


class DataImportData(BaseModel):
    """Data for import operations"""
    source: str
    file: UploadFile | None = None
    data: dict | None = None


class IgnoredActionData(BaseModel):
    """Data for ignored actions"""
    action_type: str
    identifier: str


class DetectTokensData(BaseModel):
    """Data for token detection"""
    blockchain: str
    addresses: list[str] | None = None
    async_query: bool = Field(default=True)


class StakingData(BaseModel):
    """Data for staking queries"""
    blockchain: str
    addresses: list[str] | None = None
    async_query: bool = Field(default=True)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


@router.put('/blockchains/btc/xpub', response_model=dict)
async def add_bitcoin_xpub(
    xpub_data: XpubData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add Bitcoin xpub"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Add xpub
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.add_bitcoin_xpub,
            xpub=xpub_data.xpub,
            label=xpub_data.label,
            tags=xpub_data.tags,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error adding Bitcoin xpub: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/blockchains/btc/xpub', response_model=dict)
async def edit_bitcoin_xpub(
    xpub_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit Bitcoin xpub"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Edit xpub
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.edit_bitcoin_xpub,
            xpub_data=xpub_data,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error editing Bitcoin xpub: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/blockchains/btc/xpub', response_model=dict)
async def delete_bitcoin_xpub(
    xpub: str = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete Bitcoin xpub"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Delete xpub
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.delete_bitcoin_xpub,
            xpub=xpub,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error deleting Bitcoin xpub: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/watchers', response_model=dict)
async def get_watchers(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get premium watchers"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check premium
        if not rest_api.rotkehlchen.premium:
            return JSONResponse(
                content=create_error_response('Premium subscription required'),
                status_code=402,
            )

        # Get watchers
        watchers = rest_api.rotkehlchen.get_watchers()

        return create_success_response(watchers)

    except Exception as e:
        log.error(f'Error getting watchers: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/watchers', response_model=dict)
async def add_watcher(
    watcher_data: WatcherData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a premium watcher"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check premium
        if not rest_api.rotkehlchen.premium:
            return JSONResponse(
                content=create_error_response('Premium subscription required'),
                status_code=402,
            )

        # Add watcher
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.add_watcher,
            watcher_type=watcher_data.watcher_type,
            args=watcher_data.args,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error adding watcher: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/watchers', response_model=dict)
async def edit_watcher(
    watcher_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit a premium watcher"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check premium
        if not rest_api.rotkehlchen.premium:
            return JSONResponse(
                content=create_error_response('Premium subscription required'),
                status_code=402,
            )

        # Edit watcher
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.edit_watcher,
            watcher_data=watcher_data,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error editing watcher: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/watchers', response_model=dict)
async def delete_watchers(
    watcher_ids: list[str] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete premium watchers"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check premium
        if not rest_api.rotkehlchen.premium:
            return JSONResponse(
                content=create_error_response('Premium subscription required'),
                status_code=402,
            )

        # Delete watchers
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.delete_watchers,
            watcher_ids=watcher_ids,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error deleting watchers: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/import', response_model=dict)
async def import_data(
    source: str = Body(...),
    file: UploadFile | None = File(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Import data from external source"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Read file if provided
        file_content = None
        if file:
            file_content = await file.read()

        # Import data
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.import_data,
            source=source,
            file_content=file_content,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error importing data: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/import', response_model=dict)
async def process_import_data(
    import_data: DataImportData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Process imported data"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Process import
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.process_import_data,
            source=import_data.source,
            data=import_data.data,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error processing import data: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/ignored/actions', response_model=dict)
async def add_ignored_action(
    action_data: IgnoredActionData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add ignored action"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Add ignored action
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.add_ignored_action(
                write_cursor,
                action_type=action_data.action_type,
                identifier=action_data.identifier,
            )

        return create_success_response({'result': success})

    except Exception as e:
        log.error(f'Error adding ignored action: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/ignored/actions', response_model=dict)
async def remove_ignored_actions(
    action_ids: list[str] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Remove ignored actions"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Remove ignored actions
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            removed = rest_api.rotkehlchen.data.db.remove_ignored_actions(
                write_cursor,
                action_ids=action_ids,
            )

        return create_success_response({
            'result': True,
            'removed': removed,
        })

    except Exception as e:
        log.error(f'Error removing ignored actions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/{blockchain}/evm/chains/supported', response_model=dict)
async def get_supported_evm_chains(
    blockchain: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get supported EVM chains"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get supported chains
        chains = rest_api.rotkehlchen.get_supported_evm_chains(blockchain)

        return create_success_response(chains)

    except Exception as e:
        log.error(f'Error getting supported EVM chains: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/all', response_model=dict)
async def get_all_evm_chains(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get all EVM chains"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get all chains
        chains = rest_api.rotkehlchen.get_all_evm_chains()

        return create_success_response(chains)

    except Exception as e:
        log.error(f'Error getting all EVM chains: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/blockchains/{blockchain}/evm/tokens/detect', response_model=dict)
async def detect_evm_tokens(
    blockchain: str,
    detect_data: DetectTokensData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Detect EVM tokens for addresses"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse addresses if provided
        addresses = None
        if detect_data.addresses:
            addresses = [string_to_evm_address(addr) for addr in detect_data.addresses]

        if detect_data.async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'detect_{blockchain}_tokens',
                method=rest_api.rotkehlchen.chains_aggregator.detect_tokens,
                blockchain=SupportedBlockchain.deserialize(blockchain),
                addresses=addresses,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous detection
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.detect_tokens,
            blockchain=SupportedBlockchain.deserialize(blockchain),
            addresses=addresses,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error detecting EVM tokens: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
