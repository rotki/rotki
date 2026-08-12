"""Session and MCP tokens used in the authenticated Docker deployment.

core is the password authority: on a successful ``authenticate`` (and account
creation) it mints a short-lived HMAC-SHA256 token with the key the operator
injects as ``ROTKI_SESSION_KEY``, and ships it as the HttpOnly ``rotki_session``
cookie. core **and colibri** then validate that cookie on every gated request
(defence in depth — both are reachable on loopback). The HMAC key is the raw
UTF-8 bytes of the injected key string, so the signers and validators agree
without any encoding negotiation. A ``None`` key means the feature is off and no
token is minted or required, so the Electron app and dev/standalone behave
exactly as before.

Wire format (headerless, JWT-like):
``b64url(payload).b64url(HMAC_SHA256(key, b64url(payload)))`` where ``payload`` is
the compact JSON ``{"u":<username>,"iat":<unix>,"exp":<unix>,"sid":<session id>}``.
The signature covers the first segment verbatim so the validator never
re-serializes the JSON.

MCP credentials use a purpose-derived signing key and carry ``"aud":"mcp"``.
That cryptographic domain separation means a bearer token exposed to an MCP
client can never validate as a browser cookie. MCP-to-core requests additionally
carry a proof made with a second purpose-derived key; Starling strips that
internal-only header from externally proxied API requests.

``sid`` is the **active-session id**: a random nonce minted per login and held in
memory by core as the single active session (the backend is single-user). core
and the WS validate ``sid == active`` so a new login revokes every previously
issued cookie (closes #3156); colibri validates ``sid`` too, reading core's
``session.db`` read-only so a session core has kicked is rejected there
immediately as well (signature + ``exp`` + ``sid`` membership).
"""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, TypedDict

if TYPE_CHECKING:
    from werkzeug.datastructures import Headers
    from werkzeug.wrappers import Response

log = logging.getLogger(__name__)

# Token lifetime. Matters mainly for a stable Docker key; on expiry the validators
# return 401 and the frontend falls back to its login redirect.
SESSION_TOKEN_TTL: Final = 7 * 24 * 60 * 60  # 7 days

# Rolling idle window carried as the token `exp`. An active session is re-issued past
# half of this (see the server after_request), so it never expires mid-use; an idle
# one dies once `exp` passes and the validators 401. Colibri enforces this for free
# via its `exp` check, so the value also bounds colibri's revocation window.
SESSION_IDLE_TTL: Final = 24 * 60 * 60  # 1 day

# Absolute ceiling a rolling session can never be extended past. Held server-side in
# the SessionStore / session.db (the `abs` column), not in the token — core caps each
# refresh at it and stops re-issuing beyond it. Colibri never needs it.
SESSION_ABSOLUTE_TTL: Final = 7 * 24 * 60 * 60  # 7 days

# Name of the signed HttpOnly cookie carrying the session token.
SESSION_COOKIE_NAME: Final = 'rotki_session'

# Opt-in control over the cookie's `Secure` attribute. See `cookie_secure_mode`.
SESSION_COOKIE_SECURE_ENV: Final = 'ROTKI_SESSION_COOKIE_SECURE'

# Set by starling on every proxied request, never passed through from the client.
FORWARDED_PROTO_HEADER: Final = 'X-Forwarded-Proto'

MCP_BACKEND_PROOF_HEADER: Final = 'X-Rotki-MCP-Proof'
MCP_TOKEN_AUDIENCE: Final = 'mcp'
_MCP_TOKEN_KEY_CONTEXT: Final = b'rotki-mcp-access-v1'
_MCP_BACKEND_PROOF_KEY_CONTEXT: Final = b'rotki-mcp-backend-proof-v1'


class SessionClaims(NamedTuple):
    """The validated claims carried by a session token."""
    username: str
    exp: int
    sid: str


class MintedSessionToken(TypedDict):
    """The signed token and its expiry, as returned by :func:`mint_session_token`."""
    token: str
    exp: int


def cookie_secure_mode() -> Literal['off', 'on', 'forwarded']:
    """Read ``ROTKI_SESSION_COOKIE_SECURE``.

    ``off`` (unset) keeps the cookie usable over plain http, which is what a
    loopback or LAN deployment needs. ``on`` always marks it ``Secure``, for an
    operator who knows TLS is terminated in front and whose proxy may not send
    ``X-Forwarded-Proto``. ``forwarded`` derives it per request from that header.

    An unrecognised value warns rather than silently meaning ``off``: this
    decides whether a credential may cross a plaintext connection, so a typo
    must not quietly leave it unset.
    """
    raw = os.environ.get(SESSION_COOKIE_SECURE_ENV, '').strip().lower()
    if raw in {'', '0', 'false', 'no', 'off'}:
        return 'off'
    if raw in {'1', 'true', 'yes', 'on'}:
        return 'on'
    if raw == 'forwarded':
        return 'forwarded'

    log.warning(
        'Unrecognised %s value %r; treating it as "off" so the session cookie is not '
        'marked Secure. Use "1", "forwarded" or leave it unset.',
        SESSION_COOKIE_SECURE_ENV,
        raw,
    )
    return 'off'


def session_cookie_is_secure(headers: Headers) -> bool:
    """Whether the session cookie should carry ``Secure`` for this request.

    In ``forwarded`` mode this trusts ``X-Forwarded-Proto``, which is safe only
    because starling rewrites that header on every proxied request, keeping an
    inbound value solely when the peer is a trusted hop. core cannot make that
    judgement itself: it sits on loopback behind starling, so every request
    looks like it came from ``127.0.0.1``.
    """
    mode = cookie_secure_mode()
    if mode == 'on':
        return True
    if mode == 'forwarded':
        # Read the leftmost entry, the same way starling does. It always writes a
        # single token, so today the two agree on any input; parsing it the same
        # way here means they cannot drift apart if that ever stops being true.
        raw = headers.get(FORWARDED_PROTO_HEADER, '')
        return raw.split(',')[0].strip().lower() == 'https'
    return False


def set_session_cookie(response: Response, token: str, secure: bool = False) -> None:
    """Attach the signed session token as the HttpOnly ``rotki_session`` cookie.

    ``HttpOnly`` keeps it out of JS (XSS can't exfiltrate it); ``SameSite=Lax``
    stops a third-party site riding it on a navigation while still allowing the
    same-origin SPA.

    ``secure`` defaults to off because the Docker deployment is plain http on
    loopback / a LAN, where the flag would stop the cookie being sent at all.
    Behind a TLS terminator the operator turns it on with
    ``ROTKI_SESSION_COOKIE_SECURE``; see :func:`session_cookie_is_secure`.
    """
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TOKEN_TTL,
        httponly=True,
        samesite='Lax',
        path='/',
        secure=secure,
    )


def clear_session_cookie(response: Response, secure: bool = False) -> None:
    """Delete the session cookie (logout).

    ``path`` must match the one it was set with, since a cookie is keyed on
    (name, domain, path). The flags are *not* part of that key, so clearing does
    not depend on them matching; ``secure`` is passed to keep the clearing cookie
    consistent with the scheme of the request it answers, which in ``forwarded``
    mode is the scheme the live cookie was set under.
    """
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path='/',
        httponly=True,
        samesite='Lax',
        secure=secure,
    )


def _b64url(raw: bytes) -> str:
    """URL-safe base64 without padding (matches the validator's decoder)."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64url_decode(segment: str) -> bytes:
    """Inverse of :func:`_b64url`: re-pad to a multiple of 4, then decode."""
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _derive_key(key: bytes, context: bytes) -> bytes:
    """Derive a purpose-specific HMAC key without exposing the operator's root key."""
    return hmac.new(key, context, hashlib.sha256).digest()


def _mint_token(
        key: bytes,
        username: str,
        sid: str,
        now: int | None = None,
        expires_at: int | None = None,
        audience: str | None = None,
) -> MintedSessionToken:
    issued_at = int(time.time()) if now is None else now
    if expires_at is None:
        expires_at = issued_at + SESSION_TOKEN_TTL
    payload_data: dict[str, int | str] = {
        'u': username,
        'iat': issued_at,
        'exp': expires_at,
        'sid': sid,
    }
    if audience is not None:
        payload_data['aud'] = audience
    payload = json.dumps(payload_data, separators=(',', ':')).encode('utf-8')
    payload_b64 = _b64url(payload)
    signature = hmac.new(key, payload_b64.encode('ascii'), hashlib.sha256).digest()
    return {'token': f'{payload_b64}.{_b64url(signature)}', 'exp': expires_at}


def _read_token(
        key: bytes,
        token: str,
        now: int | None = None,
        audience: str | None = None,
) -> SessionClaims | None:
    current_time = int(time.time()) if now is None else now
    try:
        payload_b64, signature_b64 = token.split('.')
    except ValueError:
        return None

    try:
        expected = hmac.new(key, payload_b64.encode('ascii'), hashlib.sha256).digest()
        provided = _b64url_decode(signature_b64)
    except (ValueError, binascii.Error):
        return None
    if not hmac.compare_digest(provided, expected):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, binascii.Error):
        return None

    expires_at = payload.get('exp')
    username = payload.get('u')
    sid = payload.get('sid')
    if (
        not isinstance(expires_at, int) or
        not isinstance(username, str) or
        not isinstance(sid, str) or
        payload.get('aud') != audience
    ):
        return None
    if current_time >= expires_at:
        return None
    return SessionClaims(username=username, exp=expires_at, sid=sid)


def mint_session_token(
        key: bytes,
        username: str,
        sid: str,
        now: int | None = None,
        expires_at: int | None = None,
) -> MintedSessionToken:
    """Mint a signed browser-session token carrying the active ``sid``."""
    return _mint_token(
        key=key,
        username=username,
        sid=sid,
        now=now,
        expires_at=expires_at,
    )


def read_session_token(key: bytes, token: str, now: int | None = None) -> SessionClaims | None:
    """Validate a browser-session token and return its claims."""
    return _read_token(key=key, token=token, now=now)


def mint_mcp_token(
        key: bytes,
        username: str,
        sid: str,
        expires_at: int,
        now: int | None = None,
) -> MintedSessionToken:
    """Mint an MCP-only bearer linked to the active browser session ``sid``."""
    return _mint_token(
        key=_derive_key(key, _MCP_TOKEN_KEY_CONTEXT),
        username=username,
        sid=sid,
        now=now,
        expires_at=expires_at,
        audience=MCP_TOKEN_AUDIENCE,
    )


def read_mcp_token(key: bytes, token: str, now: int | None = None) -> SessionClaims | None:
    """Validate an MCP-only bearer and return its linked session claims."""
    return _read_token(
        key=_derive_key(key, _MCP_TOKEN_KEY_CONTEXT),
        token=token,
        now=now,
        audience=MCP_TOKEN_AUDIENCE,
    )


def create_mcp_backend_proof(key: bytes, token: str) -> str:
    """Authenticate an MCP process's direct request to core without a session cookie."""
    proof_key = _derive_key(key, _MCP_BACKEND_PROOF_KEY_CONTEXT)
    return _b64url(hmac.new(proof_key, token.encode('ascii'), hashlib.sha256).digest())


def verify_mcp_backend_proof(key: bytes, token: str, proof: str) -> bool:
    """Validate the internal MCP-to-core proof, failing closed for malformed input."""
    try:
        expected = create_mcp_backend_proof(key=key, token=token)
        return hmac.compare_digest(expected, proof)
    except (TypeError, UnicodeError):
        return False


def verify_session_token(key: bytes, token: str, now: int | None = None) -> str | None:
    """Validate a session token and return the username it was minted for (or
    ``None`` on any failure). A thin wrapper over :func:`read_session_token` for
    callers that only need the identity (signature + ``exp``, no ``sid`` check)."""
    claims = read_session_token(key, token, now)
    return claims.username if claims is not None else None
