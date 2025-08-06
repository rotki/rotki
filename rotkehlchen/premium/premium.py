import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import time
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from collections.abc import Sequence
from enum import Enum
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, TypedDict, cast
from urllib.parse import urlencode
from uuid import uuid4

import machineid
import requests

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.api.websockets.typedefs import DBUploadStatusStep, WSMessageType
from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.constants.timing import ROTKEHLCHEN_SERVER_BACKUP_TIMEOUT
from rotkehlchen.errors.api import (
    IncorrectApiKeyFormat,
    PremiumApiError,
    PremiumAuthenticationError,
)
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import is_production, set_user_agent
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator

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


class UserLimits(TypedDict):
    """User limits for rotki premium subscription."""
    # Maximum number of devices that can be registered with the premium account
    limit_of_devices: int
    # Maximum number of profit and loss events that can be processed
    pnl_events_limit: int
    # Maximum size in megabytes for database backups stored on rotki servers
    max_backup_size_mb: int
    # Maximum number of history events that can be stored and processed
    history_events_limit: int
    # Maximum number of report lookups that can be performed
    reports_lookup_limit: int
    # Maximum amount of ETH that can be staked (validator balance limit)
    eth_staked_limit: int


class UserLimitType(Enum):
    """Enum of the different limits enforced by tiers"""
    HISTORY_EVENTS = 'history_events_limit'
    PNL_EVENTS = 'pnl_events_limit'
    PNL_REPORTS_LOOKUP = 'reports_lookup_limit'
    ETH_STAKED = 'eth_staked_limit'

    def get_free_limit(self) -> int:
        """Get the free limit for a specific limit type
        May raise:
        - NotImplementedError if the type is not yet supported.
        """
        if self == UserLimitType.HISTORY_EVENTS:
            return FREE_HISTORY_EVENTS_LIMIT
        if self == UserLimitType.PNL_EVENTS:
            return FREE_PNL_EVENTS_LIMIT
        if self == UserLimitType.PNL_REPORTS_LOOKUP:
            return FREE_REPORTS_LOOKUP_LIMIT
        if self == UserLimitType.ETH_STAKED:
            return 128  # 128 ETH limit for free users (4 validators * 32 ETH each)

        raise NotImplementedError(f'Unknown limit type: {self}. This indicates a bug in the code.')


COMPONENTS_VERSION: Final = 14
DEFAULT_ERROR_MSG: Final = 'Failed to contact rotki server. Check logs for more details'
KNOWN_STATUS_CODES: Final = (
    HTTPStatus.OK,
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.CREATED,
)
NEST_API_ENDPOINTS: Final = ('backup', 'backup/range', 'devices', 'limits')
UPLOAD_CHUNK_SIZE: Final = 10_000_000  # 10 MB
MAX_UPLOAD_CHUNK_RETRIES: Final = 1


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
        status_codes: Sequence[HTTPStatus] = KNOWN_STATUS_CODES,
        user_msg: str = DEFAULT_ERROR_MSG,
) -> dict:
    """Processes a dict response returned from the Rotkehlchen server and returns
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

    def __hash__(self) -> int:
        return hash(self.api_key + str(self.api_secret))


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

    def __init__(
            self,
            credentials: PremiumCredentials,
            username: str,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.status = SubscriptionStatus.UNKNOWN
        self.session = create_session()
        self.apiversion = '1'
        rotki_base_url = 'rotki.com'
        self.is_production = is_production()
        if self.is_production is False and os.environ.get('ROTKI_API_ENVIRONMENT') == 'staging':
            rotki_base_url = 'staging.rotki.com'

        self.rotki_api = f'https://{rotki_base_url}/api/{self.apiversion}/'
        self.rotki_web = f'https://{rotki_base_url}/webapi/{self.apiversion}/'
        self.rotki_nest = f'https://{rotki_base_url}/nest/{self.apiversion}/'
        self.reset_credentials(credentials)
        self.username = username
        # Cache user limits to avoid repeated API calls during the session
        self._cached_limits: UserLimits | None = None
        self.msg_aggregator = msg_aggregator

    def reset_credentials(self, credentials: PremiumCredentials) -> None:
        self.credentials = credentials
        self.session.headers.update({'API-KEY': self.credentials.serialize_key()})
        set_user_agent(self.session)
        # Clear cached limits when credentials change
        self._cached_limits = None

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
        try:
            response = self.session.get(
                f'{self.rotki_nest}{(method := "devices")}',
                params=self.sign(method=method),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        result = _process_dict_response(response)
        result['current_device_id'] = machineid.hashed_id(self.username)
        return result

    def authenticate_device(self) -> None:
        """
        Check if the device is in the list of the devices and if it isn't add it when possible.
        May raise:
        - RemoteError
        - PremiumAuthenticationError: when the device can't be registered
        """
        device_id = machineid.hashed_id(self.username)

        # Check if device is already registered
        try:
            response = self.session.post(
                url=f'{self.rotki_nest}devices/check',
                json=self.sign(
                    method='devices',
                    device_identifier=device_id,
                ),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to check device registration due to: {e}') from e

        match response.status_code:
            case HTTPStatus.OK:
                return None  # Device is already registered
            case HTTPStatus.FORBIDDEN:
                raise PremiumAuthenticationError('Premium credentials not valid')
            case HTTPStatus.NOT_FOUND:
                # Device is not registered, try to register it
                return self._register_new_device(device_id)
            case _:
                return check_response_status_code(
                    response=response,
                    status_codes=[HTTPStatus.OK],
                )

    def _register_new_device(self, device_id: str) -> None:
        """
        Register a new device at the rotki server using the provided id.
        May raise:
        - RemoteError
        - PremiumAuthenticationError: if the queried API returns a 401 error
        """
        log.debug(f'Registering new device {device_id}')
        try:
            response = self.session.put(
                url=f'{self.rotki_nest}{(method := "devices")}',
                json=self.sign(
                    method=method,
                    device_identifier=device_id,
                    device_name=str(uuid4()),  # can be edited later.
                    platform=platform.system(),
                ),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to register device due to: {e}') from e

        if response.status_code in (HTTPStatus.CREATED, HTTPStatus.CONFLICT):
            return None  # device was created or it already exists

        check_response_status_code(
            response=response,
            status_codes=[HTTPStatus.CREATED],
        )

    def delete_device(self, device_id: str) -> None:
        """Deletes a device for the user from the rotki server
        May raise:
        - InputError
        - RemoteError
        """
        if device_id == machineid.hashed_id(self.username):
            raise InputError('Cannot delete the current device')

        log.debug(f'Deleting premium registered {device_id=}')
        try:
            response = self.session.delete(
                url=f'{self.rotki_nest}{(method := "devices")}',
                json=self.sign(
                    method=method,
                    device_identifier=device_id,
                ),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to delete device due to: {e}') from e

        check_response_status_code(response=response, status_codes=[HTTPStatus.OK])

    def edit_device(self, device_id: str, device_name: str) -> None:
        """Edit device name for the authenticated user
        May raise:
        - RemoteError
        """
        log.debug(f'Editing premium registered {device_id=} to name {device_name}')
        try:
            response = self.session.patch(
                url=f'{self.rotki_nest}{(method := "devices")}',
                json=self.sign(
                    method=method,
                    device_identifier=device_id,
                    device_name=device_name,
                ),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to edit device due to: {e}') from e

        check_response_status_code(response=response, status_codes=[HTTPStatus.OK])

    def is_active(self) -> bool:
        if self.status == SubscriptionStatus.ACTIVE:
            return True

        try:
            self.query_last_data_metadata()
        except RemoteError:
            self.status = SubscriptionStatus.INACTIVE
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
            **kwargs: Any,
    ) -> dict:
        """
        Create payload for signed requests. It sets the signature headers
        for the current session
        """
        urlpath = f'/api/{self.apiversion}/{method}'

        req = kwargs
        if method != 'watchers':
            # the watchers endpoint accepts json and not url query data
            # and since that endpoint we don't send nonces
            req['nonce'] = int(1000 * time.time())
        post_data = urlencode(req)
        hashable = post_data.encode()
        if method in NEST_API_ENDPOINTS:
            # nest uses hex for generating the signature since digest returns a string with the \x
            # format in python.
            message = urlpath.encode() + hashlib.sha256(hashable).hexdigest().encode()
        else:
            message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            self.credentials.api_secret,
            message,
            hashlib.sha512,
        )
        self.session.headers.update({'API-SIGN': base64.b64encode(signature.digest())})
        return req

    def upload_data(
            self,
            data_blob: bytes,
            our_hash: str,
            last_modify_ts: Timestamp,
            compression_type: Literal['zlib'],
    ) -> None:
        """Uploads data to the server. We upload the encrypted database in chunks via an http form.

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        total_size, upload_id = len(data_blob), None
        chunk_count = (total_size + UPLOAD_CHUNK_SIZE - 1) // UPLOAD_CHUNK_SIZE
        for chunk_idx, offset in enumerate(range(0, total_size, UPLOAD_CHUNK_SIZE)):
            chunk_end = min(offset + UPLOAD_CHUNK_SIZE, total_size)
            self.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS,
                data={
                    'type': str(DBUploadStatusStep.UPLOADING),
                    'current_chunk': chunk_idx + 1,
                    'total_chunks': chunk_count,
                },
            )

            form_kwargs: Any = {
                'file_hash': our_hash,
                'last_modify_ts': last_modify_ts,
                'compression': compression_type,
                'total_size': total_size,
            }
            if upload_id is not None:  # add upload_id if present
                form_kwargs['upload_id'] = upload_id

            retry_count, is_last_chunk = 0, (chunk_end == total_size)
            while True:
                try:
                    response = self.session.post(
                        self.rotki_nest + 'backup/range',
                        files={'chunk_data': ('chunk', data_blob[offset:chunk_end])},
                        data=self.sign(method='backup/range', **form_kwargs),
                        headers={'Content-Range': f'bytes {offset}-{chunk_end - 1}/{total_size}'},
                        timeout=ROTKEHLCHEN_SERVER_BACKUP_TIMEOUT,
                    )
                except requests.exceptions.RequestException as e:
                    log.error(msg := f'Could not connect to rotki server due to {e!s}')
                    raise RemoteError(msg) from e

                expected_status = HTTPStatus.OK if is_last_chunk else HTTPStatus.PARTIAL_CONTENT
                if response.status_code != expected_status:
                    if response.status_code != HTTPStatus.REQUEST_ENTITY_TOO_LARGE and retry_count < MAX_UPLOAD_CHUNK_RETRIES:  # noqa: E501
                        retry_count += 1
                        continue  # retry chunk upload

                    _process_dict_response(
                        response=response,
                        status_codes=(expected_status,),
                        user_msg='Size limit reached' if response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE else f'Could not upload database backup due to: {response.text}',  # noqa: E501
                    )
                    return

                break  # chunk upload was successful, leave retry loop.

            if not is_last_chunk and upload_id is None:
                try:  # Get upload_id from response for subsequent chunks
                    upload_id = response.json()['upload_id']
                except (json.JSONDecodeError, KeyError) as e:
                    log.error(msg := f'Invalid response from server during chunked upload: {e!s}')
                    raise RemoteError(msg) from e

    def pull_data(self) -> bytes | None:
        """Pulls data from the server and returns the binary file with the database encrypted

        Returns None if there is no DB saved in the server.

        May raise:
        - RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        data = self.sign('backup')

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
        data = self.sign('last_data_metadata')

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
        data = self.sign(
            'statistics_rendererv2',
            version=COMPONENTS_VERSION if self.is_production else int(os.environ.get('ROTKI_COMPONENTS_VERSION', COMPONENTS_VERSION)),  # noqa: E501
        )

        try:
            response = self.session.get(
                self.rotki_api + 'statistics_rendererv2',
                data=data,
                headers={} if self.is_production else {'ROTKI_DEV': 'true'},
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

    def fetch_limits(self) -> UserLimits:
        """Fetch user limits from the rotki server.

        Retrieves the current limits for the premium subscription from the server.
        The limits are cached during the session to avoid repeated API calls.

        May raise:
        - RemoteError: If there are problems connecting to the server
        - PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        if self._cached_limits is not None:
            return self._cached_limits

        try:
            response = self.session.get(
                f'{self.rotki_nest}{(method := "limits")}',
                params=self.sign(method=method),
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            msg = f'Could not connect to rotki server due to {e!s}'
            log.error(msg)
            raise RemoteError(msg) from e

        self._cached_limits = cast('UserLimits', _process_dict_response(response))
        log.debug(f'Fetched user limits from server: {self._cached_limits}')
        return self._cached_limits

    def watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: dict[str, Any] | None,
    ) -> Any:
        if data is None:
            data = {}

        self.sign('watchers', **data)
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


def premium_create_and_verify(
        credentials: PremiumCredentials,
        username: str,
        msg_aggregator: 'MessagesAggregator',
) -> Premium:
    """Create a Premium object with the key pairs and verify them.

    Returns the created premium object

    May Raise:
    - PremiumAuthenticationError if the given key is rejected by the server
    - RemoteError if there are problems reaching the server
    """
    premium = Premium(credentials=credentials, username=username, msg_aggregator=msg_aggregator)
    premium.authenticate_device()
    return premium


def has_premium_check(premium: Premium | None) -> bool:
    """Helper function to check if we have premium"""
    return premium is not None and premium.is_active()


def get_user_limit(premium: Premium | None, limit_type: UserLimitType) -> tuple[int, bool]:
    """Helper function to get a specific user limit and premium status

    Returns:
        tuple[int, bool]: (limit_value, has_premium)
    """
    if premium is None or premium.is_active() is False:
        log.debug(f'No premium subscription or inactive, returning free limit for {limit_type}')
        return limit_type.get_free_limit(), False

    try:
        limits = premium.fetch_limits()
        return limits[limit_type.value], True
    except (RemoteError, PremiumAuthenticationError, KeyError) as e:
        msg = str(e)
        if isinstance(e, KeyError):  # that's a bad error that needs action on our side
            msg = f'missing key {msg} from the premium limits response. Report this to rotki devs.'
            premium.msg_aggregator.add_error(msg)  # make sure users see this error

        log.error(f'Failed to fetch limits from server: {e}. Falling back to free limits')
        return limit_type.get_free_limit(), False
