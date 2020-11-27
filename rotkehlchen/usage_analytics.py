import logging
import platform
import sys
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import Any, Dict, NamedTuple, Optional

import requests

from rotkehlchen.utils.misc import get_system_spec
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

# A "best" geolocation API list: https://rapidapi.com/blog/ip-geolocation-api/

LOCATION_DATA_QUERY_TIMEOUT = 5


log = logging.getLogger(__name__)


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
    analytics = {}

    analytics['system_os'] = platform.system()
    analytics['system_release'] = platform.release()
    analytics['system_version'] = platform.version()
    analytics['rotki_version'] = get_system_spec()['rotkehlchen']

    location_data = retrieve_location_data()
    if location_data is None:
        location_data = GeolocationData('unknown', 'unknown')

    analytics['country'] = location_data.country_code
    analytics['city'] = location_data.city

    return analytics


def maybe_submit_usage_analytics(should_submit: bool) -> None:
    if not getattr(sys, 'frozen', False):
        # not packaged -- must be in develop mode. Don't submit analytics
        return None

    if should_submit is False:
        return None

    analytics = create_usage_analytics()
    try:
        response = requests.put('https://rotki.com/api/1/usage_analytics', json=analytics)
    except requests.exceptions.RequestException:
        return None

    if response.status_code == HTTPStatus.NO_CONTENT:
        # Succesfully submitted
        log.info('Submitted usage analytics')

    return None
