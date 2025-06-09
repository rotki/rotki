"""Async implementation of user management endpoints

This module provides high-performance async user operations.
"""
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.db.settings import DEFAULT_PREMIUM_SHOULD_SYNC, ModifiableDBSettings
from rotkehlchen.errors.api import APIError
from rotkehlchen.errors.misc import (
    DBSchemaError,
    DBUpgradeError,
    SystemPermissionError,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.types import SupportedBlockchain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["users"])


# Pydantic models
class UserCredentials(BaseModel):
    """Model for user credentials"""
    name: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    initial_settings: Optional[ModifiableDBSettings] = Field(default=None, description="Initial settings")
    premium_api_key: Optional[str] = Field(default=None, description="Premium API key")
    premium_api_secret: Optional[str] = Field(default=None, description="Premium API secret")
    sync_database: bool = Field(default=DEFAULT_PREMIUM_SHOULD_SYNC, description="Sync with premium")
    async_query: bool = Field(default=False, description="Run as async task")


class UserAction(BaseModel):
    """Model for user actions (login/logout)"""
    name: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    sync_approval: str = Field(default="unknown", regex="^(yes|no|unknown)$")
    async_query: bool = Field(default=False, description="Run as async task")


class PasswordChange(BaseModel):
    """Model for password change"""
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=1, description="New password")


class PremiumCredentialsModel(BaseModel):
    """Model for premium credentials"""
    api_key: str = Field(..., description="Premium API key")
    api_secret: str = Field(..., description="Premium API secret")


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/users", response_model=dict)
async def get_users(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get list of all users"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Get users from data handler
        users = rest_api.rotkehlchen.data_importer.db_handler.get_users()
        
        # Get logged in user if any
        logged_in_user = None
        if rest_api.rotkehlchen.user_is_logged_in:
            with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
                logged_in_user = rest_api.rotkehlchen.data.db.get_main_user_properties(cursor)
        
        result = {'result': users}
        if logged_in_user:
            result[logged_in_user[0]] = 'loggedin'
        
        return result
        
    except Exception as e:
        log.error(f"Error getting users: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/users", response_model=dict)
async def create_user(
    credentials: UserCredentials,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Create a new user"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user already exists
        users = rest_api.rotkehlchen.data_importer.db_handler.get_users()
        if credentials.name in users:
            return JSONResponse(
                content=create_error_response(f"User {credentials.name} already exists"),
                status_code=409,
            )
        
        # Check if another user is logged in
        if rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("Cannot create user while another user is logged in"),
                status_code=403,
            )
        
        # Create premium credentials if provided
        premium_credentials = None
        if credentials.premium_api_key and credentials.premium_api_secret:
            premium_credentials = PremiumCredentials(
                given_api_key=credentials.premium_api_key,
                given_api_secret=credentials.premium_api_secret,
            )
        
        if credentials.async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'create_user_{credentials.name}',
                method=rest_api.rotkehlchen.unlock_user,
                user=credentials.name,
                password=credentials.password,
                create_new=True,
                initial_settings=credentials.initial_settings,
                premium_credentials=premium_credentials,
                sync_database=credentials.sync_database,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous creation
        await asyncio.to_thread(
            rest_api.rotkehlchen.unlock_user,
            user=credentials.name,
            password=credentials.password,
            create_new=True,
            initial_settings=credentials.initial_settings,
            premium_credentials=premium_credentials,
            sync_database=credentials.sync_database,
        )
        
        # Get settings and exchanges
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = rest_api.rotkehlchen.data.db.get_settings(cursor)
            exchanges = rest_api.rotkehlchen.exchange_manager.get_connected_exchange_names()
        
        return create_success_response({
            'settings': settings.serialize(),
            'exchanges': exchanges,
        })
        
    except SystemPermissionError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )
    except DBUpgradeError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )
    except Exception as e:
        log.error(f"Error creating user: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/users/{name}/login", response_model=dict)
async def login_user(
    name: str,
    action: UserAction,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Login a user"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Validate username matches
        if name != action.name:
            return JSONResponse(
                content=create_error_response("Username in URL does not match username in request"),
                status_code=400,
            )
        
        # Check if user exists
        users = rest_api.rotkehlchen.data_importer.db_handler.get_users()
        if name not in users:
            return JSONResponse(
                content=create_error_response(f"User {name} does not exist"),
                status_code=404,
            )
        
        # Check if another user is logged in
        if rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("Another user is already logged in"),
                status_code=403,
            )
        
        if action.async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'login_user_{name}',
                method=rest_api.rotkehlchen.unlock_user,
                user=name,
                password=action.password,
                sync_approval=action.sync_approval,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous login
        await asyncio.to_thread(
            rest_api.rotkehlchen.unlock_user,
            user=name,
            password=action.password,
            sync_approval=action.sync_approval,
        )
        
        # Get settings and exchanges
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = rest_api.rotkehlchen.data.db.get_settings(cursor)
            exchanges = rest_api.rotkehlchen.exchange_manager.get_connected_exchange_names()
        
        return create_success_response({
            'settings': settings.serialize(),
            'exchanges': exchanges,
        })
        
    except DBSchemaError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=426,  # Upgrade Required
        )
    except SystemPermissionError as e:
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )
    except Exception as e:
        log.error(f"Error logging in user: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/users/{name}/logout", response_model=dict)
async def logout_user(
    name: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Logout a user"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Check if correct user
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            username = rest_api.rotkehlchen.data.db.get_main_user_properties(cursor)[0]
        
        if username != name:
            return JSONResponse(
                content=create_error_response(f"User {name} is not logged in"),
                status_code=403,
            )
        
        # Logout
        await asyncio.to_thread(rest_api.rotkehlchen.logout)
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error logging out user: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/users/{name}/password", response_model=dict)
async def change_user_password(
    name: str,
    password_data: PasswordChange,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Change user password"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Check if correct user
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            username = rest_api.rotkehlchen.data.db.get_main_user_properties(cursor)[0]
        
        if username != name:
            return JSONResponse(
                content=create_error_response(f"User {name} is not logged in"),
                status_code=403,
            )
        
        # Change password
        success = await asyncio.to_thread(
            rest_api.rotkehlchen.data.db.update_user_password,
            password=password_data.current_password,
            new_password=password_data.new_password,
        )
        
        if not success:
            return JSONResponse(
                content=create_error_response("Invalid current password"),
                status_code=401,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error changing password: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/premium", response_model=dict)
async def get_premium_status(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get premium subscription status"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get premium status
        premium = rest_api.rotkehlchen.premium
        if premium is None:
            return create_success_response({'result': False})
        
        return create_success_response({
            'result': True,
            'username': premium.credentials.username,
            'subscription_end': premium.status.subscription_end,
            'active': premium.is_active(),
        })
        
    except Exception as e:
        log.error(f"Error getting premium status: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/premium", response_model=dict)
async def set_premium_credentials(
    credentials: PremiumCredentialsModel,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Set premium API credentials"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Set premium credentials
        success = await asyncio.to_thread(
            rest_api.rotkehlchen.set_premium_credentials,
            given_api_key=credentials.api_key,
            given_api_secret=credentials.api_secret,
        )
        
        if not success:
            return JSONResponse(
                content=create_error_response("Invalid premium credentials"),
                status_code=400,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error setting premium credentials: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/premium", response_model=dict)
async def delete_premium_credentials(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete premium API credentials"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete premium credentials
        await asyncio.to_thread(
            rest_api.rotkehlchen.delete_premium_credentials,
        )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error deleting premium credentials: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/premium/sync", response_model=dict)
async def sync_premium_database(
    async_query: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Sync user database with premium server"""
    if not async_features.is_enabled(AsyncFeature.USERS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check if user is logged in
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Check premium status
        if rest_api.rotkehlchen.premium is None:
            return JSONResponse(
                content=create_error_response("No premium subscription"),
                status_code=403,
            )
        
        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='premium_sync',
                method=rest_api.rotkehlchen.premium_sync_manager.sync_data,
            )
            
            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })
        
        # Synchronous sync
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.premium_sync_manager.sync_data,
        )
        
        return create_success_response(result)
        
    except Exception as e:
        log.error(f"Error syncing premium database: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']