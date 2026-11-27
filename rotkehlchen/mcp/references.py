"""Opaque references and privacy filtering for the accounting diagnosis tools.

The diagnosis endpoints return raw identifiers: account addresses, transaction hashes and
the group identifiers derived from them. Outside ``raw`` privacy mode none of them reach the
agent. Each is replaced by the same ``anon_…`` hash the analytics tables use for it, so a
diagnosis can be joined with ``query_sql`` results, and the hash is remembered so the agent
can hand it back to another tool, which resolves it here. Buckets get a ``bucket_…``
reference the same way.

References live in this process only. They are dropped whenever the privacy mode or the
logged-in user changes, so a reference handed out for one user never resolves against another
user's data. An unknown reference is reported as such and never
echoed into an error message together with a raw value.

Event and issue identifiers are database row numbers, not personal data, and pass through so
that they stay actionable everywhere. Free text, such as an error message, is scrubbed of
embedded addresses and hashes.
"""
from __future__ import annotations

import hmac
import json
import threading
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import quote

from rotkehlchen.mcp.analytics import (
    READABLE_LOCATION_LABELS,
    _hash_identifier,
    _scrub_identifiers,
    _session_seed,
    on_session_change,
    resolve_hashed_value,
)

if TYPE_CHECKING:
    from rotkehlchen.mcp.constants import PrivacyMode

# Values that identify the user's accounts or transactions. Hashed outside raw mode.
ACCOUNT_KEYS: Final = frozenset({
    'account',
    'address',
    'from_address',
    'location_label',
    'to_address',
    'user_address',
})
TRANSACTION_KEYS: Final = frozenset({'group_identifier', 'tx_hash', 'tx_ref', 'transfer_id'})
# Values passed through untouched: asset identifiers embed public token contract addresses
# that the scrubber would otherwise mistake for an account.
PASSTHROUGH_KEYS: Final = frozenset({
    'asset',
    'assets',
    'assets_considered',
    'event_asset',
    'excluded_assets',
    'from_asset',
    'to_asset',
})
BUCKET_KEYS: Final = frozenset({'location', 'location_label', 'protocol', 'asset'})
# The rotki app route listing a transaction's events. It names the transaction, so it is only
# handed out in raw mode.
HISTORY_EVENTS_ROUTE: Final = '/history/events?groupIdentifiers='
# The rotki app route opening one data issue. An issue id is a row number, so this one is
# handed out in every privacy mode, and the issue's drawer leads on to its events.
DATA_ISSUE_ROUTE: Final = '/history/data-issues/issues?issue='


class UnknownReferenceError(Exception):
    """A reference that this session did not hand out, or that was invalidated."""


class ReferenceRegistry:
    """The bucket references handed out in this process, and resolution of all references.

    ``anon_…`` references are the analytics hashes, whose values the analytics module keeps.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, Any] = {}

    def clear(self) -> None:
        with self._lock:
            self._values.clear()

    @staticmethod
    def reference(value: str) -> str:
        """The analytics hash of the value, which resolve() maps back to it."""
        return str(_hash_identifier(value))

    def bucket_reference(self, bucket: dict[str, Any]) -> str:
        canonical = {key: bucket.get(key) for key in sorted(BUCKET_KEYS)}
        digest = hmac.new(
            _session_seed,
            json.dumps(canonical, sort_keys=True).encode(),
            sha256,
        ).hexdigest()[:16]
        reference = f'bucket_{digest}'
        with self._lock:
            self._values[reference] = canonical
        return reference

    def resolve(self, reference: str, privacy_mode: PrivacyMode) -> Any:
        """The raw value of a reference. In raw mode a raw value is accepted as is.

        May raise UnknownReferenceError.
        """
        if (value := resolve_hashed_value(reference)) is not None:
            return value
        if privacy_mode == 'raw' and not reference.startswith(('anon_', 'bucket_')):
            return reference
        raise UnknownReferenceError(
            'Unknown or expired reference. References are valid for this session only; '
            'get a fresh one from a diagnosis tool',
        )

    def resolve_bucket(self, reference: str) -> dict[str, Any]:
        """May raise UnknownReferenceError."""
        with self._lock:
            if isinstance(value := self._values.get(reference), dict):
                return value
        raise UnknownReferenceError(
            'Unknown or expired bucket reference. Get a fresh one from a diagnosis tool',
        )


_registry = ReferenceRegistry()
on_session_change(_registry.clear)


def get_reference_registry() -> ReferenceRegistry:
    return _registry


def _sanitize_account(value: Any, privacy_mode: PrivacyMode) -> Any:
    if not isinstance(value, str):
        return value
    if privacy_mode == 'balanced' and value.lower() in READABLE_LOCATION_LABELS:
        return value  # a venue name, not the user's own text, see READABLE_LOCATION_LABELS
    return _registry.reference(value)


def _issue_id(value: dict[str, Any]) -> Any:
    """The id of the data issue the dict is, or refers to by ``issue_id``."""
    if 'issue_id' in value:
        return value['issue_id']
    return value.get('id') if value.keys() >= {'id', 'kind', 'state'} else None


def sanitize(value: Any, privacy_mode: PrivacyMode, key: str | None = None) -> Any:
    """Return a copy of a diagnosis payload that is safe to hand to the agent.

    Every bucket gets a ``bucket_ref`` the agent can pass back, and every data issue an
    ``issue_ui_route`` that opens it in rotki, in every privacy mode. In raw mode everything
    naming a transaction also gets the ``ui_route`` that opens it in rotki.
    """
    if isinstance(value, dict):
        is_ignore_action = value.get('action') in ('ignore_action', 'ignore_group')
        sanitized = {
            child_key: (
                {
                    param_key: sanitize(
                        param_val,
                        privacy_mode=privacy_mode,
                        key='group_identifier' if param_key == 'data' else param_key,
                    )
                    for param_key, param_val in child.items()
                }
                if is_ignore_action and child_key == 'params' and isinstance(child, dict)
                else sanitize(child, privacy_mode=privacy_mode, key=child_key)
            )
            for child_key, child in value.items()
        }
        if value.keys() >= BUCKET_KEYS:
            sanitized['bucket_ref'] = _registry.bucket_reference(value)
        if key != 'params':
            if privacy_mode == 'raw' and isinstance(group := value.get('group_identifier'), str):
                sanitized['ui_route'] = HISTORY_EVENTS_ROUTE + quote(group, safe='')
            if isinstance(issue_id := _issue_id(value), int):
                sanitized['issue_ui_route'] = f'{DATA_ISSUE_ROUTE}{issue_id}'
        return sanitized
    if isinstance(value, list):
        return [sanitize(item, privacy_mode=privacy_mode, key=key) for item in value]
    if privacy_mode == 'raw':
        if isinstance(value, str) and key in TRANSACTION_KEYS:
            _registry.reference(value)  # so a hash taken from analytics still resolves
        return value
    if not isinstance(value, str) or key in PASSTHROUGH_KEYS:
        return value
    if key in ACCOUNT_KEYS:
        return _sanitize_account(value, privacy_mode)
    if key in TRANSACTION_KEYS:
        return _registry.reference(value)
    return _scrub_identifiers(value)
