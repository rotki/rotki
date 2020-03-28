import base64
import hashlib
import hmac
import logging
import time
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from enum import Enum
from http import HTTPStatus
from typing import Any, Dict, NamedTuple, Tuple
from urllib.parse import urlencode

import requests
from typing_extensions import Literal

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.errors import IncorrectApiKeyFormat, PremiumAuthenticationError, RemoteError
from rotkehlchen.typing import B64EncodedBytes, Timestamp
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


class PremiumCredentials():
    """Represents properly encoded premium credentials

    Constructor can raise IncorrectApiKeyFormat
    """

    def __init__(self, given_api_key: str, given_api_secret: str) -> None:
        self.api_key = given_api_key
        try:
            self.api_secret = b64decode(given_api_secret)
        except BinasciiError:
            raise IncorrectApiKeyFormat('Rotkehlchen api secret is not in the correct format')

    def serialize_key(self) -> str:
        """Turn the API key into the format to send outside Rotki (network, DB e.t.c.)"""
        return self.api_key

    def serialize_secret(self) -> str:
        """Turn the API secret into the format to send outside Rotki (network, DB e.t.c.)"""
        return b64encode(self.api_secret).decode()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PremiumCredentials):
            return NotImplemented
        return self.api_key == other.api_key and self.api_secret == other.api_secret


class Premium():

    def __init__(self, credentials: PremiumCredentials):
        self.status = SubscriptionStatus.UNKNOWN
        self.session = requests.session()
        self.apiversion = '1'
        self.uri = 'https://rotki.com/api/{}/'.format(self.apiversion)
        self.reset_credentials(credentials)

    def reset_credentials(self, credentials: PremiumCredentials) -> None:
        self.credentials = credentials
        self.session.headers.update({
            'API-KEY': self.credentials.serialize_key(),
        })

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
            raise IncorrectApiKeyFormat(f'Secret Key formatting error: {str(e)}')

        active = self.is_active()
        if not active:
            self.reset_credentials(old_credentials)
            raise PremiumAuthenticationError('Rotkehlchen API key was rejected by server')

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

    def sign(self, method: str, **kwargs: Any) -> Tuple[hmac.HMAC, Dict]:
        urlpath = '/api/' + self.apiversion + '/' + method

        req = kwargs
        req['nonce'] = int(1000 * time.time())
        # print('HASH OF BLOB: {}'.format(hashlib.sha256(req['data_blob']).digest()))
        post_data = urlencode(req)
        hashable = post_data.encode()
        message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            self.credentials.api_secret,
            message,
            hashlib.sha512,
        )
        return signature, req

    def upload_data(
            self,
            data_blob: B64EncodedBytes,
            our_hash: str,
            last_modify_ts: Timestamp,
            compression_type: Literal['zlib'],
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
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),  # type: ignore
        })

        try:
            response = self.session.put(
                self.uri + 'save_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        return _process_dict_response(response)

    def pull_data(self) -> Dict:
        """Pulls data from the server and returns the response dict

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign('get_saved_data')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),  # type: ignore
        })

        try:
            response = self.session.get(
                self.uri + 'get_saved_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        return _process_dict_response(response)

    def query_last_data_metadata(self) -> RemoteMetadata:
        """Queries last metadata from the server and returns the response
        as a RemoteMetadata object.

        Raises RemoteError if there are problems reaching the server or if
        there is an error returned by the server
        """
        signature, data = self.sign('last_data_metadata')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),  # type: ignore
        })

        try:
            response = self.session.get(
                self.uri + 'last_data_metadata',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.ConnectionError:
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
        signature, data = self.sign('statistics_rendererv2')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),  # type: ignore
        })

        try:
            response = self.session.get(
                self.uri + 'statistics_rendererv2',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except requests.exceptions.ConnectionError:
            raise RemoteError('Could not connect to rotkehlchen server')

        result = _process_dict_response(response)
        return result['data']


def premium_create_and_verify(credentials: PremiumCredentials) -> Premium:
    """Create a Premium object with the key pairs and verify them.

    Returns the created premium object

    raises PremiumAuthenticationError if the given key is rejected by the server
    """
    premium = Premium(credentials)

    if premium.is_active():
        return premium

    raise PremiumAuthenticationError('Rotkehlchen API key was rejected by server')
