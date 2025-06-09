"""Async authentication and session management

Replaces gevent-based session handling with async implementation.
"""
import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED

from rotkehlchen.api.v1.schemas_fastapi import (
    CreateUserModel,
    LoginModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.crypto import encrypt
from rotkehlchen.db.handler import DBHandler
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Session configuration
SESSION_TIMEOUT = 3600  # 1 hour
MAX_SESSIONS_PER_USER = 5
SESSION_TOKEN_LENGTH = 32


class Session:
    """Async session data"""

    def __init__(
        self,
        user_id: int,
        username: str,
        token: str,
        created_at: Timestamp,
        last_activity: Timestamp,
        ip_address: str,
        user_agent: str,
    ):
        self.user_id = user_id
        self.username = username
        self.token = token
        self.created_at = created_at
        self.last_activity = last_activity
        self.ip_address = ip_address
        self.user_agent = user_agent

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return time.time() - self.last_activity > SESSION_TIMEOUT

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = Timestamp(int(time.time()))


class AuthManager:
    """Manages authentication and sessions asynchronously"""

    def __init__(self, async_db: AsyncDBHandler):
        self.async_db = async_db
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, list[str]] = {}  # username -> [tokens]
        self._session_lock = asyncio.Lock()

    async def create_user(
        self,
        username: str,
        password: str,
        premium_api_key: str = '',
        premium_api_secret: str = '',
    ) -> dict[str, Any]:
        """Create a new user"""
        # Check if user exists
        async with self.async_db.async_conn.read_ctx() as cursor:
            await cursor.execute(
                'SELECT COUNT(*) FROM user_credentials WHERE name = ?',
                (username,),
            )
            count = (await cursor.fetchone())[0]

        if count > 0:
            raise AuthenticationError(f'User {username} already exists')

        # Hash password
        password_hash = self._hash_password(password)

        # Encrypt premium credentials if provided
        encrypted_api_key = ''
        encrypted_api_secret = ''
        if premium_api_key:
            encrypted_api_key = encrypt(premium_api_key, password).decode()
        if premium_api_secret:
            encrypted_api_secret = encrypt(premium_api_secret, password).decode()

        # Create user
        async with self.async_db.async_conn.write_ctx() as cursor:
            await cursor.execute(
                """
                INSERT INTO user_credentials (name, password, premium_api_key, premium_api_secret)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, encrypted_api_key, encrypted_api_secret),
            )
            user_id = cursor.lastrowid

        log.info(f'Created new user: {username}')

        return {
            'user_id': user_id,
            'username': username,
        }

    async def login(
        self,
        username: str,
        password: str,
        request: Request,
    ) -> dict[str, Any]:
        """Authenticate user and create session"""
        # Get user from database
        async with self.async_db.async_conn.read_ctx() as cursor:
            await cursor.execute(
                'SELECT id, password FROM user_credentials WHERE name = ?',
                (username,),
            )
            result = await cursor.fetchone()

        if not result:
            raise AuthenticationError('Invalid username or password')

        user_id, stored_hash = result

        # Verify password
        if not self._verify_password(password, stored_hash):
            raise AuthenticationError('Invalid username or password')

        # Create session
        session = await self._create_session(
            user_id=user_id,
            username=username,
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent', ''),
        )

        log.info(f'User {username} logged in from {session.ip_address}')

        return {
            'token': session.token,
            'username': username,
            'expires_in': SESSION_TIMEOUT,
        }

    async def logout(self, token: str):
        """Logout and destroy session"""
        async with self._session_lock:
            session = self._sessions.get(token)
            if session:
                # Remove from sessions
                del self._sessions[token]

                # Remove from user sessions
                if session.username in self._user_sessions:
                    self._user_sessions[session.username].remove(token)
                    if not self._user_sessions[session.username]:
                        del self._user_sessions[session.username]

                log.info(f'User {session.username} logged out')

    async def get_session(self, token: str) -> Session | None:
        """Get session by token"""
        async with self._session_lock:
            session = self._sessions.get(token)

            if session is None:
                return None

            if session.is_expired():
                # Remove expired session
                await self.logout(token)
                return None

            # Update activity
            session.update_activity()
            return session

    async def validate_session(self, token: str) -> Session:
        """Validate session token or raise exception"""
        session = await self.get_session(token)
        if session is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired session',
            )
        return session

    async def _create_session(
        self,
        user_id: int,
        username: str,
        ip_address: str,
        user_agent: str,
    ) -> Session:
        """Create a new session"""
        async with self._session_lock:
            # Clean up old sessions for user
            if username in self._user_sessions:
                user_tokens = self._user_sessions[username].copy()
                if len(user_tokens) >= MAX_SESSIONS_PER_USER:
                    # Remove oldest session
                    oldest_token = user_tokens[0]
                    del self._sessions[oldest_token]
                    self._user_sessions[username].remove(oldest_token)

            # Generate secure token
            token = secrets.token_urlsafe(SESSION_TOKEN_LENGTH)

            # Create session
            now = Timestamp(int(time.time()))
            session = Session(
                user_id=user_id,
                username=username,
                token=token,
                created_at=now,
                last_activity=now,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Store session
            self._sessions[token] = session
            if username not in self._user_sessions:
                self._user_sessions[username] = []
            self._user_sessions[username].append(token)

            return session

    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2"""
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,  # iterations
        )
        return salt.hex() + key.hex()

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        salt = bytes.fromhex(stored_hash[:64])
        stored_key = bytes.fromhex(stored_hash[64:])

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
        )

        return hmac.compare_digest(key, stored_key)

    async def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        async with self._session_lock:
            expired_tokens = []

            for token, session in self._sessions.items():
                if session.is_expired():
                    expired_tokens.append(token)

            for token in expired_tokens:
                session = self._sessions[token]
                del self._sessions[token]

                if session.username in self._user_sessions:
                    self._user_sessions[session.username].remove(token)
                    if not self._user_sessions[session.username]:
                        del self._user_sessions[session.username]

            if expired_tokens:
                log.info(f'Cleaned up {len(expired_tokens)} expired sessions')


# FastAPI dependencies
async def get_auth_manager(request: Request) -> AsyncAuthManager:
    """Get auth manager from app state"""
    return request.app.state.auth_manager


async def get_current_session(
    request: Request,
    auth_manager: AsyncAuthManager = Depends(get_auth_manager),
) -> Session:
    """Get current session from request"""
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail='Missing or invalid authorization header',
        )

    token = auth_header[7:]  # Remove 'Bearer ' prefix
    return await auth_manager.validate_session(token)


async def require_logged_in_user(
    session: Session = Depends(get_current_session),
) -> Session:
    """Require authenticated user"""
    return session


# Auth endpoints
from fastapi import APIRouter

router = APIRouter(prefix='/api/1', tags=['auth'])


@router.post('/users', response_model=dict)
async def create_user(
    user_data: CreateUserModel,
    auth_manager: AsyncAuthManager = Depends(get_auth_manager),
):
    """Create a new user"""
    try:
        result = await auth_manager.create_user(
            username=user_data.username,
            password=user_data.password,
            premium_api_key=user_data.premium_api_key or '',
            premium_api_secret=user_data.premium_api_secret or '',
        )
        return create_success_response(result, status_code=201)
    except AuthenticationError as e:
        return create_error_response(str(e), status_code=400)
    except Exception as e:
        log.error(f'Error creating user: {e}')
        return create_error_response('Failed to create user', status_code=500)


@router.post('/login', response_model=dict)
async def login(
    credentials: LoginModel,
    request: Request,
    auth_manager: AsyncAuthManager = Depends(get_auth_manager),
):
    """Login and create session"""
    try:
        result = await auth_manager.login(
            username=credentials.username,
            password=credentials.password,
            request=request,
        )
        return create_success_response(result)
    except AuthenticationError as e:
        return create_error_response(str(e), status_code=401)
    except Exception as e:
        log.error(f'Error during login: {e}')
        return create_error_response('Login failed', status_code=500)


@router.post('/logout', response_model=dict)
async def logout(
    session: Session = Depends(get_current_session),
    auth_manager: AsyncAuthManager = Depends(get_auth_manager),
):
    """Logout and destroy session"""
    await auth_manager.logout(session.token)
    return create_success_response({'message': 'Logged out successfully'})


@router.get('/user', response_model=dict)
async def get_current_user(
    session: Session = Depends(get_current_session),
):
    """Get current user information"""
    return create_success_response({
        'username': session.username,
        'user_id': session.user_id,
    })


# Export for inclusion
__all__ = ['AuthManager', 'require_logged_in_user', 'router']

