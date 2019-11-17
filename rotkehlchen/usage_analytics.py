import platform
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import Any, Dict, NamedTuple, Optional

import requests

from rotkehlchen.db.settings import DBSettings
from rotkehlchen.utils.misc import get_system_spec, ts_now
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

# A "best" geolocation API list: https://rapidapi.com/blog/ip-geolocation-api/

LOCATION_DATA_QUERY_TIMEOUT = 5


class GeolocationData(NamedTuple):
    country_code: str
    city: str


def query_ipwhoisio() -> Optional[GeolocationData]:
    """10,000 requests per month per IP
    https://ipwhois.io/documentation
    """
    try:
        response = requests.get(
            'http://free.ipwhois.io/json/',
            timeout=LOCATION_DATA_QUERY_TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code != HTTPStatus.OK:
        return None

    try:
        json_ret = rlk_jsonloads_dict(response.text)
    except JSONDecodeError:
        return None

    return GeolocationData(
        country_code=json_ret.get('country_code', 'unknown'),
        city=json_ret.get('city', 'unknown'),
    )


def query_ipinfo() -> Optional[GeolocationData]:
    """
    50,000 requests per month tied to the API Key
    https://ipinfo.io/developers
    """
    try:
        response = requests.get(
            'https://ipinfo.io/json?token=16ab40aad9bd5b',
            timeout=LOCATION_DATA_QUERY_TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code != HTTPStatus.OK:
        return None

    try:
        json_ret = rlk_jsonloads_dict(response.text)
    except JSONDecodeError:
        return None

    return GeolocationData(
        country_code=json_ret.get('country', 'unknown'),
        city=json_ret.get('city', 'unknown'),
    )


def query_ipstack() -> Optional[GeolocationData]:
    """
    10,000 requests per month tied to the API Key
    https://ipstack.com/
    """
    try:
        response = requests.get(
            'http://api.ipstack.com/check?access_key=affd920d6e1008a614900dbc31d52fa6',
            timeout=LOCATION_DATA_QUERY_TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code != HTTPStatus.OK:
        return None

    try:
        json_ret = rlk_jsonloads_dict(response.text)
    except JSONDecodeError:
        return None

    return GeolocationData(
        country_code=json_ret.get('country_code', 'unknown'),
        city=json_ret.get('city', 'unknown'),
    )


def retrieve_location_data() -> Optional[GeolocationData]:
    # First try asking the no api key service
    location_data = query_ipwhoisio()
    if location_data:
        return location_data

    # Then the one with the most API requests per key
    location_data = query_ipinfo()
    if location_data:
        return location_data

    # finally the 3rd one as backup
    location_data = query_ipstack()
    # Can also be None if last query also fails
    # TODO: Add more fallbacks
    return location_data


def create_usage_analytics() -> Dict[str, Any]:
    analytics = dict()

    analytics['timestamp'] = ts_now()
    analytics['system_os'] = platform.system()
    analytics['system_release'] = platform.release()
    analytics['system_version'] = platform.version()
    analytics['rotki_version'] = get_system_spec()['rotkehlchen']

    location_data = retrieve_location_data()
    if not location_data:
        location_data = GeolocationData('unknown', 'unknown')

    analytics['country'] = location_data.country_code
    analytics['city'] = location_data.city

    return analytics


def maybe_submit_usage_analytics(settings: DBSettings) -> None:
    if settings.submit_usage_analytics is False:
        return

    analytics = create_usage_analytics()
    # TODO: Submit usage analytics here
