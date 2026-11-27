"""Small backend sender for Sigil custom events."""

import platform
from typing import Any, Final, Literal, NotRequired, TypedDict

import requests

from rotkehlchen.utils.misc import ROTKI_USER_AGENT, is_production

SIGIL_BATCH_ENDPOINT: Final = 'https://sigil.rotki.com/api/batch'
SIGIL_DEVELOPMENT_WEBSITE_ID: Final = 'a3d69a71-060f-4397-afc5-e2ea1b6d389e'
SIGIL_PRODUCTION_WEBSITE_ID: Final = '4c195fc3-2beb-4492-a4f5-4c0f860bfbee'
SIGIL_DISTINCT_ID_MAX_LENGTH: Final = 50


def create_sigil_user_agent(system: str, machine: str) -> str:
    """Build the agent Sigil's Umami can attribute to an OS.

    Umami's bot check silently drops a bare ``name/version`` agent such as a release's
    ``rotki/1.44.1``, so the platform comment is what lets release events through. Its
    OS detection only knows browser tokens, hence ``Darwin`` and ``Windows`` are spelled
    the way browsers report them. Windows 11 also reports NT 10.0.
    """
    match system:
        case 'Darwin':
            os_token = 'Macintosh; Mac OS X'
        case 'Windows':
            os_token = 'Windows NT 10.0'
        case _:
            os_token = system

    return f'{ROTKI_USER_AGENT} ({os_token}; {machine})'


SIGIL_USER_AGENT: Final = create_sigil_user_agent(
    system=platform.system(),
    machine=platform.machine(),
)


class SigilEventPayload(TypedDict):
    website: str
    hostname: str
    screen: str
    language: str
    title: str
    url: str
    referrer: str
    name: str
    data: dict[str, Any]
    id: NotRequired[str]


class SigilBatchEntry(TypedDict):
    type: Literal['event']
    payload: SigilEventPayload


def client_id_from_frontend_settings(frontend_settings: dict[str, Any]) -> str | None:
    """Read the Sigil distinct id the frontend stores as its ``clientId`` setting"""
    if isinstance(client_id := frontend_settings.get('client_id'), str) and client_id:
        return client_id

    return None


def create_sigil_events_batch(
        events: list[tuple[str, str, dict[str, Any]]],
        website_id: str | None = None,
        distinct_id: str | None = None,
) -> list[SigilBatchEntry]:
    """Build Sigil event entries.

    ``distinct_id`` is the frontend's client id. Passing it attributes these events to the
    same user as the app's own events, which a backend user agent alone cannot do. A value
    longer than Sigil accepts is left out rather than sent.
    """
    website = website_id or (
        SIGIL_PRODUCTION_WEBSITE_ID if is_production() else SIGIL_DEVELOPMENT_WEBSITE_ID
    )
    batch: list[SigilBatchEntry] = []
    for name, url, data in events:
        payload: SigilEventPayload = {
            'website': website,
            'hostname': '',
            'screen': '',
            'language': '',
            'title': '',
            'url': url,
            'referrer': '',
            'name': name,
            'data': data,
        }
        if distinct_id is not None and len(distinct_id) <= SIGIL_DISTINCT_ID_MAX_LENGTH:
            payload['id'] = distinct_id

        batch.append({'type': 'event', 'payload': payload})

    return batch


def submit_sigil_batch(batch: list[SigilBatchEntry], timeout: float) -> bool:
    try:
        response = requests.post(
            url=SIGIL_BATCH_ENDPOINT,
            json=batch,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': SIGIL_USER_AGENT,
            },
            timeout=timeout,
        )
    except requests.exceptions.RequestException:
        return False

    return response.ok
