import base64
import hashlib
import hmac
import io
import logging
import time
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from enum import Enum
from http import HTTPStatus
from typing import Any, Literal, NamedTuple, Optional
from urllib.parse import urlencode

import requests

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.errors.api import (
    IncorrectApiKeyFormat,
    PremiumApiError,
    PremiumAuthenticationError,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import set_user_agent
from rotkehlchen.utils.serialization import jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

HANDLABLE_STATUS_CODES = [
    HTTPStatus.OK,
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.BAD_REQUEST,
]


class RemoteMetadata(NamedTuple):
    # This is the last upload timestamp of the remote DB data
    upload_ts: Timestamp
    # This is the last modify timestamp of the remote DB data
    last_modify_ts: Timestamp
    # This is the hash of the remote DB data
    data_hash: str
    # This is the size in bytes of the remote DB data
    data_size: int


def _process_dict_response(response: requests.Response) -> dict:
    """Processess a dict response returned from the Rotkehlchen server and returns
    the result for success or raises RemoteError if an error happened"""
    if response.status_code not in HANDLABLE_STATUS_CODES:
        raise RemoteError(
            f'Unexpected status response({response.status_code}) from '
            f'rotki server. {response.text=}',
        )

    result_dict = jsonloads_dict(response.text)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise PremiumAuthenticationError(result_dict.get('message', 'no message given'))

    if 'error' in result_dict:
        raise RemoteError(result_dict['error'])

    return result_dict


class SubscriptionStatus(Enum):
    UNKNOWN = 1
    ACTIVE = 2
    INACTIVE = 3


class PremiumCredentials:
    """Represents properly encoded premium credentials

    Constructor can raise IncorrectApiKeyFormat
    """

    def __init__(self, given_api_key: str, given_api_secret: str) -> None:
        self.api_key = given_api_key
        try:
            self.api_secret = b64decode(given_api_secret)
        except BinasciiError as e:
            raise IncorrectApiKeyFormat(
                'rotki api secret is not in the correct format',
            ) from e

    def serialize_key(self) -> str:
        """Turn the API key into the format to send outside rotki (network, DB e.t.c.)"""
        return self.api_key

    def serialize_secret(self) -> str:
        """Turn the API secret into the format to send outside rotki (network, DB e.t.c.)"""
        return b64encode(self.api_secret).decode()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PremiumCredentials):
            return NotImplemented
        return self.api_key == other.api_key and self.api_secret == other.api_secret


def _decode_response_json(response: requests.Response) -> Any:
    """Decodes a python requests response to json and returns it.

    May raise:
    - RemoteError if the response does not contain valid json
    """
    try:
        json_response = response.json()
    except ValueError as e:
        raise RemoteError(
            f'Could not decode json from {response.text} to {response.request.method} '
            f'query {response.url}',
        ) from e

    return json_response


def _decode_premium_json(response: requests.Response) -> Any:
    """Decodes a python requests response to the premium server to json and returns it.

    May raise:
    - RemoteError if the response does not contain valid json
    - PremiumApiError if there is an error in the returned json
    """
    json_data = _decode_response_json(response)
    if 'error' in json_data:
        raise PremiumApiError(json_data['error'])
    return json_data


class Premium:

    def __init__(self, credentials: PremiumCredentials):
        self.status = SubscriptionStatus.UNKNOWN
        self.session = requests.session()
        self.apiversion = '1'
        self.rotki_base_url = 'https://staging.rotki.com'
        self.rotki_api = f'{self.rotki_base_url}/api/{self.apiversion}/'
        self.rotki_nest = f'{self.rotki_base_url}/nest/'
        self.reset_credentials(credentials)

    def reset_credentials(self, credentials: PremiumCredentials) -> None:
        self.credentials = credentials
        self.session.headers.update({'API-KEY': self.credentials.serialize_key()})
        set_user_agent(self.session)

    def set_credentials(self, credentials: PremiumCredentials) -> None:
        """Try to set the credentials for a premium rotkehlchen subscription

        Raises PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        old_credentials = self.credentials

        # Forget the last active value since we are trying new credentials
        self.status = SubscriptionStatus.UNKNOWN

        # If what's given is not even valid b64 encoding then stop here
        try:
            self.reset_credentials(credentials)
        except BinasciiError as e:
            raise IncorrectApiKeyFormat(f'Secret Key formatting error: {e!s}') from e

        active = self.is_active()
        if not active:
            self.reset_credentials(old_credentials)
            raise PremiumAuthenticationError('rotki API key was rejected by server')

    def is_active(self, catch_connection_errors: bool = True) -> bool:
        if self.status == SubscriptionStatus.ACTIVE:
            return True

        try:
            self.query_last_data_metadata()
        except RemoteError:
            self.status = SubscriptionStatus.INACTIVE
            if catch_connection_errors is False:
                raise
            return False
        except PremiumAuthenticationError:
            self.status = SubscriptionStatus.INACTIVE
            return False
        else:
            self.status = SubscriptionStatus.ACTIVE
            return True

    def sign(self, method: str, **kwargs: Any) -> tuple[hmac.HMAC, dict]:
        urlpath = '/api/' + self.apiversion + '/' + method

        req = kwargs
        if method != 'watchers':
            # the watchers endpoint accepts json and not url query data
            # and since that endpoint we don't send nonces
            req['nonce'] = int(1000 * time.time())
        post_data = urlencode(req)
        hashable = post_data.encode()
        if method == 'backup':
            # nest uses hex for the backup
            message = urlpath.encode() + hashlib.sha256(hashable).digest().hex().encode()
        else:
            message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            self.credentials.api_secret,
            message,
            hashlib.sha512,
        )
        return signature, req

    def upload_data(
            self,
            data_blob: bytes,
            our_hash: str,
            last_modify_ts: Timestamp,
            compression_type: Literal['zlib'],
    ) -> dict:
        """Uploads data to the server and returns the response dict

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        signature, data = self.sign(
            'backup',
            original_hash=our_hash,
            last_modify_ts=last_modify_ts,
            index=0,
            length=len(data_blob),
            compression=compression_type,
        )
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        tmp_file = io.BytesIO()
        tmp_file.write(data_blob)
        tmp_file.seek(0)
        try:
            response = self.session.post(
                self.rotki_nest + '1/backup',
                data=data,
                files={'db_file': tmp_file},
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT * 10,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        return _process_dict_response(response)

    def pull_data(self) -> Optional[bytes]:
        """Pulls data from the server and returns the response dict

        Returns None if there is no DB saved in the server.

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        signature, data = self.sign('backup')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.rotki_nest + '1/backup',
                params=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        if response.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
            msg = 'Could not connect to rotki server.'
            log.error(f'{msg} due to {response.text}')
            raise RemoteError(msg)
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None

        return response.content

    def query_last_data_metadata(self) -> RemoteMetadata:
        """Queries last metadata from the server and returns the response
        as a RemoteMetadata object.

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        signature, data = self.sign('last_data_metadata')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.rotki_api + 'last_data_metadata',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        result = _process_dict_response(response)

        try:
            metadata = RemoteMetadata(
                upload_ts=Timestamp(result['upload_ts']),
                last_modify_ts=Timestamp(result['last_modify_ts']),
                data_hash=result['data_hash'],
                data_size=result['data_size'],
            )
        except KeyError as e:
            msg = f'Problem connecting to rotki server. last_data_metadata response missing {e!s} key'  # noqa: E501
            log.error(f'{msg}. Response was {result}')
            raise RemoteError(msg) from e

        return metadata

    def query_premium_components(self) -> str:
        """Queries for the source code of the premium components from the server

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - Raises PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        signature, data = self.sign('statistics_rendererv2', version=6)
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.rotki_api + 'statistics_rendererv2',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        result = _process_dict_response(response)
        if 'data' not in result:
            msg = 'Problem connecting to rotki server. statistics_rendererv2 response missing data key'  # noqa: E501
            log.error(f'{msg}. Response was {result}')
            raise RemoteError(msg)

        return result['data']

    def watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: Optional[dict[str, Any]],
    ) -> Any:
        if data is None:
            data = {}

        signature, _ = self.sign('watchers', **data)
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.request(
                method=method,
                url=self.rotki_api + 'watchers',
                json=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        return _decode_premium_json(response)


def premium_create_and_verify(credentials: PremiumCredentials) -> Premium:
    """Create a Premium object with the key pairs and verify them.

    Returns the created premium object

    May Raise:
    - PremiumAuthenticationError if the given key is rejected by the server
    - RemoteError if there are problems reaching the server
    """
    premium = Premium(credentials)

    if premium.is_active(catch_connection_errors=True):
        return premium

    raise PremiumAuthenticationError('rotki API key was rejected by server')
