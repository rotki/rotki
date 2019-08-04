import base64
import hashlib
import hmac
import logging
import time
from binascii import Error as BinasciiError
from enum import Enum
from http import HTTPStatus
from typing import Dict, NamedTuple, Tuple
from urllib.parse import urlencode

import requests

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.errors import AuthenticationError, IncorrectApiKeyFormat, RemoteError
from rotkehlchen.typing import ApiKey, ApiSecret, Timestamp
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

logger = logging.getLogger(__name__)

HANDLABLE_STATUS_CODES = [
    HTTPStatus.OK,
    HTTPStatus.NOT_FOUND,
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


def premium_create_and_verify(api_key: ApiKey, api_secret: ApiSecret):
    """Create a Premium object with the key pairs and verify them.

    Returns the created premium object

    raises IncorrectApiKeyFormat if the given key is in the wrong format
    raises AuthenticationError if the given key is rejected by the server
    """
    try:
        premium = Premium(api_key, api_secret)
    except BinasciiError:
        raise IncorrectApiKeyFormat('Rotkehlchen api key is not in the correct format')
    if premium.is_active():
        return premium

    raise AuthenticationError('Rotkehlchen API key was rejected by server')


def _process_dict_response(response: requests.Response) -> Dict:
    """Processess a dict response returned from the Rotkehlchen server and returns
    the result for success or raises RemoteError if an error happened"""
    if response.status_code not in HANDLABLE_STATUS_CODES:
        raise RemoteError(
            f'Unexpected status response({response.status_code}) from '
            'rotkehlchen server',
        )

    result_dict = rlk_jsonloads_dict(response.text)
    if 'error' in result_dict:
        raise RemoteError(result_dict['error'])

    return result_dict


class SubscriptionStatus(Enum):
    UNKNOWN = 1
    ACTIVE = 2
    INACTIVE = 3


class Premium():

    def __init__(self, api_key: ApiKey, api_secret: ApiSecret):
        self.status = SubscriptionStatus.UNKNOWN
        self.session = requests.session()
        self.apiversion = '1'
        self.uri = 'https://rotkehlchen.io/api/{}/'.format(self.apiversion)
        self.reset_credentials(api_key, api_secret)

    def reset_credentials(self, api_key: ApiKey, api_secret: ApiSecret) -> None:
        self.api_key = api_key
        self.secret = base64.b64decode(api_secret)
        self.session.headers.update({  # type: ignore
            'API-KEY': self.api_key,
        })

    def set_credentials(self, api_key: ApiKey, api_secret: ApiSecret) -> None:
        """Try to set the credentials for a premium rotkehlchen subscription

        Raises IncorrectApiKeyFormat if the given key is not in a proper format
        Raises AuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        old_api_key = self.api_key
        old_secret = ApiSecret(base64.b64encode(self.secret))

        # Forget the last active value since we are trying new credentials
        self.status = SubscriptionStatus.UNKNOWN

        # If what's given is not even valid b64 encoding then stop here
        try:
            self.reset_credentials(api_key, api_secret)
        except BinasciiError as e:
            raise IncorrectApiKeyFormat(f'Secret Key formatting error: {str(e)}')

        active = self.is_active()
        if not active:
            self.reset_credentials(old_api_key, old_secret)
            raise AuthenticationError('Rotkehlchen API key was rejected by server')

    def is_active(self) -> bool:
        if self.status == SubscriptionStatus.ACTIVE:
            return True

        try:
            self.query_last_data_metadata()
            self.status = SubscriptionStatus.ACTIVE
            return True
        except RemoteError:
            self.status = SubscriptionStatus.INACTIVE
            return False

    def sign(self, method: str, **kwargs) -> Tuple[hmac.HMAC, Dict]:
        urlpath = '/api/' + self.apiversion + '/' + method

        req = kwargs
        req['nonce'] = int(1000 * time.time())
        # print('HASH OF BLOB: {}'.format(hashlib.sha256(req['data_blob']).digest()))
        post_data = urlencode(req)
        hashable = post_data.encode()
        message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            self.secret,
            message,
            hashlib.sha512,
        )
        return signature, req

    def upload_data(
            self,
            data_blob,
            our_hash,
            last_modify_ts,
            compression_type,
    ) -> Dict:
        """Uploads data to the server and returns the response dict

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign(
            'save_data',
            data_blob=data_blob,
            original_hash=our_hash,
            last_modify_ts=last_modify_ts,
            index=0,
            length=len(data_blob),
            compression=compression_type,
        )
        self.session.headers.update({  # type: ignore
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.put(
                self.uri + 'save_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        return _process_dict_response(response)

    def pull_data(self) -> Dict:
        """Pulls data from the server and returns the response dict

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign('get_saved_data')
        self.session.headers.update({  # type: ignore
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.uri + 'get_saved_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        return _process_dict_response(response)

    def query_last_data_metadata(self) -> RemoteMetadata:
        """Queries last metadata from the server and returns the response
        as a RemoteMetadata object.

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign('last_data_metadata')
        self.session.headers.update({  # type: ignore
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.uri + 'last_data_metadata',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        result = _process_dict_response(response)
        metadata = RemoteMetadata(
            upload_ts=Timestamp(result['upload_ts']),
            last_modify_ts=Timestamp(result['last_modify_ts']),
            data_hash=result['data_hash'],
            data_size=result['data_size'],
        )
        return metadata

    def query_statistics_renderer(self) -> str:
        """Queries for the source of the statistics_renderer from the server

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign('statistics_renderer')
        self.session.headers.update({  # type: ignore
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.uri + 'statistics_renderer',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        result = _process_dict_response(response)
        return result['data']
