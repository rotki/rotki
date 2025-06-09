"""Async implementation of spam token management endpoints

This module provides high-performance async spam token operations.
"""
import asyncio
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rotkehlchen.api.v1.dependencies import get_rotkehlchen
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['spam'])


# Pydantic models
class SpamTokenData(BaseModel):
    """Data for spam token operations"""
    token: str


class FalsePositiveData(BaseModel):
    """Data for false positive spam token operations"""
    token: str


# Dependency injection
async def get_rotkehlchen() -> "Rotkehlchen":
    """Get Rotkehlchen instance - will be injected by the app"""
    raise NotImplementedError('Rotkehlchen injection not configured')


@router.get('/spam/evm/tokens/false_positive', response_model=dict)
async def get_false_positive_spam_tokens(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get false positive spam tokens"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get false positive tokens
        with rotkehlchen.data.db.conn.read_ctx() as cursor:
            tokens = rotkehlchen.data.db.get_false_positive_spam_tokens(cursor)

        return create_success_response({
            'tokens': [token.identifier for token in tokens],
        })

    except Exception as e:
        log.error(f'Error getting false positive spam tokens: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/spam/evm/tokens/false_positive', response_model=dict)
async def add_false_positive_spam_token(
    token_data: FalsePositiveData,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Mark a token as false positive (not spam)"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate token
        try:
            asset = Asset(token_data.token)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid token: {e}'),
                status_code=400,
            )

        # Add false positive
        with rotkehlchen.data.db.user_write() as write_cursor:
            success = rotkehlchen.data.db.add_false_positive_spam_token(
                write_cursor,
                token=asset,
            )

        if not success:
            return JSONResponse(
                content=create_error_response(f'Token {token_data.token} is already marked as false positive'),
                status_code=409,
            )

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error adding false positive spam token: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/spam/evm/tokens/false_positive', response_model=dict)
async def remove_false_positive_spam_tokens(
    tokens: list[str] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Remove tokens from false positive list"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate tokens
        assets = []
        for token in tokens:
            try:
                assets.append(Asset(token))
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid token {token}: {e}'),
                    status_code=400,
                )

        # Remove false positives
        with rotkehlchen.data.db.user_write() as write_cursor:
            removed_count = rotkehlchen.data.db.remove_false_positive_spam_tokens(
                write_cursor,
                tokens=assets,
            )

        return create_success_response({
            'result': True,
            'removed': removed_count,
        })

    except Exception as e:
        log.error(f'Error removing false positive spam tokens: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/spam/evm/tokens', response_model=dict)
async def mark_tokens_as_spam(
    tokens: list[str] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Mark tokens as spam"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate tokens
        assets = []
        for token in tokens:
            try:
                assets.append(Asset(token))
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid token {token}: {e}'),
                    status_code=400,
                )

        # Mark as spam
        marked_count = await asyncio.to_thread(
            rotkehlchen.mark_tokens_as_spam,
            tokens=assets,
        )

        return create_success_response({
            'result': True,
            'marked': marked_count,
        })

    except Exception as e:
        log.error(f'Error marking tokens as spam: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/spam/evm/tokens', response_model=dict)
async def unmark_tokens_as_spam(
    tokens: list[str] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Unmark tokens as spam"""
    if not async_features.is_enabled(AsyncFeature.ASSETS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate tokens
        assets = []
        for token in tokens:
            try:
                assets.append(Asset(token))
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid token {token}: {e}'),
                    status_code=400,
                )

        # Unmark as spam
        unmarked_count = await asyncio.to_thread(
            rotkehlchen.unmark_tokens_as_spam,
            tokens=assets,
        )

        return create_success_response({
            'result': True,
            'unmarked': unmarked_count,
        })

    except Exception as e:
        log.error(f'Error unmarking tokens as spam: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
