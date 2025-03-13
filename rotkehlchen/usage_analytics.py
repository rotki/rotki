import logging
import platform
import shutil
from http import HTTPStatus
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, NamedTuple

import maxminddb
import miniupnpc
import requests

from rotkehlchen.constants.misc import APPDIR_NAME, MISCDIR_NAME
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_date
from rotkehlchen.utils.misc import get_system_spec, is_production

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GeolocationData(NamedTuple):
    country_code: str


def _handle_retrieval_error(geoip_dir: Path, message: str) -> Path | None:
    log.error(message)
    if len(old_files := list(geoip_dir.glob('*.mmdb'))) == 0:
        return None

    return old_files[0]


def retrieve_location_data(data_dir: Path) -> GeolocationData | None:
    """This functions tries to get the country of the user based on the ip.
    To do that it makes use of an open ip to country database and tries to obtain
    the ip using UPnP protocol.

    If UpNP fails we just return None

    **IMPORTANT:** The ip never leaves the user's machine. It's all calculated locally.
    """
    geoip_dir = data_dir / APPDIR_NAME / MISCDIR_NAME
    geoip_dir.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(
            url='https://api.github.com/repos/geoacumen/geoacumen-country/branches/master',
            timeout=CachedSettings().get_timeout_tuple(),
        )
        data = response.json()
        date = deserialize_timestamp_from_date(
            date=data['commit']['commit']['author']['date'],
            formatstr='%Y-%m-%dT%H:%M:%S',
            location='Analytics',
        )
    except requests.exceptions.RequestException as e:
        filename = _handle_retrieval_error(geoip_dir, f'Failed to get metadata information for geoip file. {e!s}')  # noqa: E501
    except (DeserializationError, JSONDecodeError) as e:
        filename = _handle_retrieval_error(geoip_dir, f'Failed to deserialize date in metadata information for geoip file. {e!s}')  # noqa: E501
    except KeyError as e:
        filename = _handle_retrieval_error(geoip_dir, f'Github response for geoip file had missing key {e!s}')  # noqa: E501
    else:
        filename = geoip_dir / f'geoip-{date}.mmdb'

    if filename is None:
        return None

    if not filename.is_file():
        # Remove old files
        files = geoip_dir.glob('*.*')
        for f in files:
            f.unlink()
        # Download latest version
        try:
            response = requests.get(
                url='https://github.com/geoacumen/geoacumen-country/raw/master/Geoacumen-Country.mmdb',
                timeout=CachedSettings().get_timeout_tuple(),
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            log.debug(f'Failed to download geoip database file. {e!s}')
            return None
        with open(filename, 'wb') as outfile:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, outfile)

    # get user ip
    try:
        u = miniupnpc.UPnP()
        u.discoverdelay = 200
        u.discover()
        u.selectigd()
        user_ip = u.externalipaddress()
    except Exception as e:  # pylint: disable=broad-except
        # can raise base exception so we catch it
        log.debug(f'Failed to get ip via UPnP for analytics. {e!s}')
        return None

    try:
        with maxminddb.open_database(filename) as reader:
            data = reader.get(user_ip)
            location = data['country']['iso_code']
            if location == 'None':
                return None
            return GeolocationData(country_code=location)
    except maxminddb.errors.InvalidDatabaseError as e:
        filename.unlink()
        log.debug(f'Failed to read database {e!s}')
    except ValueError as e:
        log.debug(f'Wrong ip search {e!s}')
    return None


def create_usage_analytics(data_dir: Path) -> dict[str, Any]:
    analytics = {}

    analytics['system_os'] = platform.system()
    analytics['system_release'] = platform.release()
    analytics['system_version'] = platform.version()
    analytics['rotki_version'] = get_system_spec()['rotkehlchen']

    location_data = retrieve_location_data(data_dir)
    if location_data is None:
        location_data = GeolocationData('unknown')

    analytics['country'] = location_data.country_code
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
            headers={'User-Agent': f'rotki/{analytics["rotki_version"]}'},
            timeout=CachedSettings().get_timeout_tuple(),
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code == HTTPStatus.NO_CONTENT:
        # Successfully submitted
        log.info('Submitted usage analytics')

    return None
