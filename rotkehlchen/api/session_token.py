"""Session token — the signed HttpOnly cookie used in the Docker deployment.

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
import time
from typing import TYPE_CHECKING, Final, NamedTuple, TypedDict

if TYPE_CHECKING:
    from werkzeug.wrappers import Response

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


class SessionClaims(NamedTuple):
    """The validated claims carried by a session token."""
    username: str
    exp: int
    sid: str


class MintedSessionToken(TypedDict):
    """The signed token and its expiry, as returned by :func:`mint_session_token`."""
    token: str
    exp: int


def set_session_cookie(response: Response, token: str) -> None:
    """Attach the signed session token as the HttpOnly ``rotki_session`` cookie.

    ``HttpOnly`` keeps it out of JS (XSS can't exfiltrate it); ``SameSite=Lax``
    stops a third-party site riding it on a navigation while still allowing the
    same-origin SPA. Not ``Secure`` — the Docker deployment is plain http on
    loopback / a LAN; a TLS terminator in front can upgrade it.
    """
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TOKEN_TTL,
        httponly=True,
        samesite='Lax',
        path='/',
    )


def clear_session_cookie(response: Response) -> None:
    """Delete the session cookie (logout)."""
    response.delete_cookie(SESSION_COOKIE_NAME, path='/')


def _b64url(raw: bytes) -> str:
    """URL-safe base64 without padding (matches the validator's decoder)."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64url_decode(segment: str) -> bytes:
    """Inverse of :func:`_b64url`: re-pad to a multiple of 4, then decode."""
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def mint_session_token(
        key: bytes,
        username: str,
        sid: str,
        now: int | None = None,
        expires_at: int | None = None,
) -> MintedSessionToken:
    """Mint a signed session token for ``username`` carrying the active ``sid``.

    Returns ``{'token': <str>, 'exp': <unix seconds>}``. ``now`` is injectable
    for tests; production uses the wall clock. ``expires_at`` lets the caller set
    the token ``exp`` explicitly (the SessionStore passes a rolling value capped at
    the absolute ceiling); when omitted it defaults to ``now + SESSION_TOKEN_TTL``.
    """
    issued_at = int(time.time()) if now is None else now
    if expires_at is None:
        expires_at = issued_at + SESSION_TOKEN_TTL
    payload = json.dumps(
        {'u': username, 'iat': issued_at, 'exp': expires_at, 'sid': sid},
        separators=(',', ':'),
    ).encode('utf-8')
    payload_b64 = _b64url(payload)
    signature = hmac.new(key, payload_b64.encode('ascii'), hashlib.sha256).digest()
    return {'token': f'{payload_b64}.{_b64url(signature)}', 'exp': expires_at}


def read_session_token(key: bytes, token: str, now: int | None = None) -> SessionClaims | None:
    """Validate a session token and return its claims (username, exp, sid).

    Recomputes the HMAC over the first segment (constant-time compare) and checks
    the expiry. Returns the claims on success, or ``None`` for any failure —
    malformed token, bad signature, or expired. ``now`` is injectable for tests.
    The ``exp`` lets the caller implement rolling refresh past half the lifetime;
    ``sid`` lets core/WS enforce single-session.
    """
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
        not isinstance(sid, str)
    ):
        return None
    if current_time >= expires_at:
        return None
    return SessionClaims(username=username, exp=expires_at, sid=sid)


def verify_session_token(key: bytes, token: str, now: int | None = None) -> str | None:
    """Validate a session token and return the username it was minted for (or
    ``None`` on any failure). A thin wrapper over :func:`read_session_token` for
    callers that only need the identity (signature + ``exp``, no ``sid`` check)."""
    claims = read_session_token(key, token, now)
    return claims.username if claims is not None else None
