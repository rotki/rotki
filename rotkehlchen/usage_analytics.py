import logging
import platform
from http import HTTPStatus
from pathlib import Path
from typing import Any

import requests

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ROTKI_USER_AGENT, get_system_spec, is_production

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def create_usage_analytics(data_dir: Path) -> dict[str, Any]:
    analytics = {}

    analytics['system_os'] = platform.system()
    analytics['system_release'] = platform.release()
    analytics['system_version'] = platform.version()
    analytics['rotki_version'] = get_system_spec()['rotkehlchen']
    analytics['country'] = 'unknown'  # deprecated -- we no longer use it
    analytics['city'] = 'unknown'  # deprecated -- we no longer use it

    return analytics


def maybe_submit_usage_analytics(data_dir: Path, should_submit: bool) -> None:
    if not is_production():
        return None  # only submit analytics for production

    if should_submit is False:
        return None

    analytics = create_usage_analytics(data_dir)
    try:
        response = requests.put(
            url='https://rotki.com/api/1/usage_analytics',
            json=analytics,
            headers={'User-Agent': ROTKI_USER_AGENT},
            timeout=CachedSettings().get_timeout_tuple(),
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code == HTTPStatus.NO_CONTENT:
        # Successfully submitted
        log.info('Submitted usage analytics')

    return None
