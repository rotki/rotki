import base64
import hashlib
import hmac
import logging
import platform
import time
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from collections.abc import Sequence
from enum import Enum
from http import HTTPStatus
from json import JSONDecodeError
from typing import Any, Literal, NamedTuple, Optional
from urllib.parse import urlencode

import machineid
import requests
from urllib3.util.retry import Retry

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.timing import ROTKEHLCHEN_SERVER_BACKUP_TIMEOUT
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


class RemoteMetadata(NamedTuple):
    # This is the last upload timestamp of the remote DB data
    upload_ts: Timestamp
    # This is the last modify timestamp of the remote DB data
    last_modify_ts: Timestamp
    # This is the hash of the remote DB data
    data_hash: str
    # This is the size in bytes of the remote DB data
    data_size: int


DEFAULT_ERROR_MSG = 'Failed to contact rotki server. Check logs for more details'
DEFAULT_OK_CODES = (HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.BAD_REQUEST)


def check_response_status_code(
        response: requests.Response,
        status_codes: Sequence[HTTPStatus],
        user_msg: str = DEFAULT_ERROR_MSG,
) -> None:
    """
    Check the rotki.com response and if status code is not in the expected list
    log the error and raise RemoteError
    """
    if response.status_code not in status_codes:
        log.error(
            f'rotki server responded with an error response to {response.url} '
            f'{response.status_code=} and {response.text=}',
        )
        raise RemoteError(user_msg)


def _process_dict_response(
        response: requests.Response,
        status_codes: Sequence[HTTPStatus] = DEFAULT_OK_CODES,
        user_msg: str = DEFAULT_ERROR_MSG,
) -> dict:
    """Processess a dict response returned from the Rotkehlchen server and returns
    the result for success or raises RemoteError if an error happened"""
    check_response_status_code(
        response=response,
        status_codes=status_codes,
        user_msg=user_msg,
    )
    try:
        result_dict = jsonloads_dict(response.text)
    except JSONDecodeError as e:
        log.error(f'Could not decode rotki response {response.text} as json due to {e}')
        raise RemoteError('Could not decode rotki server response as json. Check logs') from e

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise PremiumAuthenticationError(result_dict.get('error', 'no message given'))

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

    def __init__(self, credentials: PremiumCredentials, username: str):
        self.status = SubscriptionStatus.UNKNOWN
        self.session = requests.session()
        # Make sure to have 3 retries on read/connect/other errors for all requests
        # The reason for this is that we have noticed that in unstable/slow connections
        # rotki.com server will close/cause the connection to result to a read timeout
        # At the moment this only happens for the backup upload endpoint. More info:
        # https://github.com/rotki/rotki/pull/6423
        adapter = requests.adapters.HTTPAdapter()
        # Have to set retries like this, since this granularity is not given by HTTPAdapter ctor
        adapter.max_retries = Retry(
            total=3,  # have to set each one individually as the code checks them all
            read=3,
            connect=3,
            other=3,
            allowed_methods=False,  # retry on all method verbs
        )
        self.session.mount('https://', adapter)
        self.session.verify = False
        self.apiversion = '1'
        self.rotki_api = f'https://localhost/api/{self.apiversion}/'
        self.rotki_web = f'https://localhost/webapi/{self.apiversion}/'
        self.rotki_nest = f'https://localhost/nest/{self.apiversion}/'
        self.reset_credentials(credentials)
        self.username = username

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

    def get_remote_devices_information(self) -> dict:
        """Get the list of devices for the current user"""
        method = 'manage/premium/devices'
        signature, data = self.sign(
            method=method,
            api_endpoint='webapi',
        )
        self.session.headers.update({'API-SIGN': base64.b64encode(signature.digest())})

        try:
            response = self.session.get(
                f'{self.rotki_web}{method}',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        data = _process_dict_response(response)
        return data

    def authenticate_device(self) -> None:
        """
        Check if the device is in the list of the devices and if it isn't add it when possible.
        May raise:
        - PremiumAuthenticationError: when the device can't be registered
        """
        device_data = self.get_remote_devices_information()
        num_devices = len(device_data['devices'])
        devices_limit = device_data['limit']
        device_id = machineid.hashed_id(self.username)

        device_found = False
        for device in device_data['devices']:
            if device['device_identifier'] != device_id:
                continue
            device_found = True
            break

        if not device_found:
            if num_devices < devices_limit:
                # try to sign up the device
                self._register_new_device(device_id)
            else:
                # user has to edit his devices
                raise PremiumAuthenticationError('The limit of devices has been reached')

    def _register_new_device(self, device_id: str) -> dict:
        log.debug(f'Registering new device {device_id}')
        method = 'devices'
        device_name = platform.system()
        signature, data = self.sign(
            method=method,
            device_identifier=device_id,
            device_name=device_name,
        )
        self.session.headers.update({'API-SIGN': base64.b64encode(signature.digest())})

        try:
            resposne = self.session.put(
                url=f'{self.rotki_api}{method}',
                data=data,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to register device due to {e!s}')
            raise RemoteError from e

        response_body = _process_dict_response(resposne)
        return response_body

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

    def sign(
            self,
            method: str,
            api_endpoint: str = '/api/',
            **kwargs: Any,
    ) -> tuple[hmac.HMAC, dict]:
        urlpath = f'{api_endpoint}{self.apiversion}/{method}'

        req = kwargs
        if method != 'watchers':
            # the watchers endpoint accepts json and not url query data
            # and since that endpoint we don't send nonces
            req['nonce'] = int(1000 * time.time())
        post_data = urlencode(req)
        hashable = post_data.encode()
        if method == 'backup':
            # nest uses hex for generating the signature since digest returns a string with the \x
            # format in python.
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
        """Uploads data to the server and returns the response dict. We upload the encrypted
        database as a file in an http form.

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

        try:
            response = self.session.post(
                self.rotki_nest + 'backup',
                data=data,
                files={'db_file': data_blob},
                timeout=ROTKEHLCHEN_SERVER_BACKUP_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        return _process_dict_response(
            response=response,
            status_codes=(HTTPStatus.OK,),
            user_msg='Size limit reached' if response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE else f'Could not upload database backup due to: {response.text}',  # noqa: E501
        )

    def pull_data(self) -> Optional[bytes]:
        """Pulls data from the server and returns the binary file with the database encrypted

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
                self.rotki_nest + 'backup',
                params=data,
                timeout=ROTKEHLCHEN_SERVER_BACKUP_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        check_response_status_code(response, (HTTPStatus.OK, HTTPStatus.NOT_FOUND))
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

        check_response_status_code(
            response=response,
            status_codes=(HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.BAD_REQUEST),
        )
        return _decode_premium_json(response)


def premium_create_and_verify(credentials: PremiumCredentials, username: str) -> Premium:
    """Create a Premium object with the key pairs and verify them.

    Returns the created premium object

    May Raise:
    - PremiumAuthenticationError if the given key is rejected by the server
    - RemoteError if there are problems reaching the server
    """
    premium = Premium(credentials=credentials, username=username)

    if premium.is_active(catch_connection_errors=True):
        return premium

    raise PremiumAuthenticationError('rotki API key was rejected by server')
