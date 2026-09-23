"""Small backend sender for Sigil custom events."""

from typing import Any, Final, Literal, TypedDict

import requests

from rotkehlchen.utils.misc import ROTKI_USER_AGENT, is_production

SIGIL_BATCH_ENDPOINT: Final = 'https://sigil.rotki.com/api/batch'
SIGIL_DEVELOPMENT_WEBSITE_ID: Final = 'a3d69a71-060f-4397-afc5-e2ea1b6d389e'
SIGIL_PRODUCTION_WEBSITE_ID: Final = '4c195fc3-2beb-4492-a4f5-4c0f860bfbee'


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


class SigilBatchEntry(TypedDict):
    type: Literal['event']
    payload: SigilEventPayload


def create_sigil_events_batch(
        events: list[tuple[str, str, dict[str, Any]]],
        website_id: str | None = None,
) -> list[SigilBatchEntry]:
    website = website_id or (
        SIGIL_PRODUCTION_WEBSITE_ID if is_production() else SIGIL_DEVELOPMENT_WEBSITE_ID
    )
    return [{
        'type': 'event',
        'payload': {
            'website': website,
            'hostname': '',
            'screen': '',
            'language': '',
            'title': '',
            'url': url,
            'referrer': '',
            'name': name,
            'data': data,
        },
    } for name, url, data in events]


def submit_sigil_batch(batch: list[SigilBatchEntry], timeout: float) -> bool:
    try:
        response = requests.post(
            url=SIGIL_BATCH_ENDPOINT,
            json=batch,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': ROTKI_USER_AGENT,
            },
            timeout=timeout,
        )
    except requests.exceptions.RequestException:
        return False

    return response.ok
