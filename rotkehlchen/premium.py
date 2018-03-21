import requests
import time
import hashlib
import hmac
import base64
from http import HTTPStatus
from urllib.parse import urlencode
from requests import ConnectionError
from binascii import Error as binascii_error
from rotkehlchen.utils import rlk_jsonloads
from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT

import logging
logger = logging.getLogger(__name__)

HANDLABLE_STATUS_CODES = [
    HTTPStatus.OK,
    HTTPStatus.NOT_FOUND,
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.BAD_REQUEST,
]


def premium_create_and_verify(api_key, api_secret):
    """Create a Premium object with the key pairs and verify them.

    Returns a tuple (premium_object, valid, empty_or_error) where:

    - premium_object: Is the initialized premium_object
    - valid: A boolean indicating if the api keys are actually valid. This
             is found out by making an API call.
    - empty_or_error: A string containing an error message if something went wrong
    """
    try:
        premium = Premium(api_key, api_secret)
        valid, empty_or_error = premium.is_active()
    except binascii_error:
        return None, False, 'incorrect api key format'

    return premium, valid, empty_or_error

class Premium(object):

    def __init__(self, api_key, api_secret):
        self.session = requests.session()
        self.apiversion = '1'
        self.uri = 'http://localhost:5001/api/{}/'.format(self.apiversion)
        self.reset_credentials(api_key, api_secret)

    def reset_credentials(self, api_key, api_secret):
        self.api_key = api_key
        self.secret = base64.b64decode(api_secret)
        self.session.headers.update({
            'API-KEY': self.api_key,
        })

    def set_credentials(self, api_key, api_secret):
        old_api_key = self.api_key
        old_secret = base64.b64encode(self.secret)

        # Forget the cached active value since we are trying new credentials
        if hasattr(self, 'active'):
            del self.active

        # If what's given is not even valid b64 encoding then stop here
        try:
            self.reset_credentials(api_key, api_secret)
        except binascii_error as e:
            return False, 'Secret Key formatting error: {}'.format(e)

        active, empty_or_error = self.is_active()
        if not active:
            self.reset_credentials(old_api_key, old_secret)
            return False, empty_or_error
        return True, ''

    def is_active(self):
        if hasattr(self, 'active'):
            return self.active, ''
        else:
            self.active, result_or_error = self.query_last_data_metadata()
        emptystr_or_error = '' if self.active else result_or_error
        return self.active, emptystr_or_error

    def process_response(self, response):
        result_or_error = ''
        success = False
        if response.status_code not in HANDLABLE_STATUS_CODES:
            result_or_error = (
                'Unexpected status response({}) from rotkehlchen server'.format(
                    response.status_code))
        else:
            result_or_error = rlk_jsonloads(response.text)
            if 'error' in result_or_error:
                result_or_error = result_or_error['error']
            else:
                success = True

        return success, result_or_error

    def sign(self, method, **kwargs):
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
            hashlib.sha512
        )
        return signature, req

    def upload_data(self, data_blob, our_hash, last_modify_ts, compression_type):
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
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.put(
                self.uri + 'save_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except ConnectionError as e:
            return False, 'Could not connect to rotkehlchen server'

        success, result_or_error = self.process_response(response)
        return success, result_or_error

    def pull_data(self):
        signature, data = self.sign('get_saved_data')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.uri + 'get_saved_data',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except ConnectionError as e:
            return False, 'Could not connect to rotkehlchen server'

        success, result_or_error = self.process_response(response)
        return success, result_or_error

    def query_last_data_metadata(self):
        signature, data = self.sign('last_data_metadata')
        self.session.headers.update({
            'API-SIGN': base64.b64encode(signature.digest()),
        })

        try:
            response = self.session.get(
                self.uri + 'last_data_metadata',
                data=data,
                timeout=ROTKEHLCHEN_SERVER_TIMEOUT,
            )
        except ConnectionError as e:
            return False, 'Could not connect to rotkehlchen server'
        success, result_or_error = self.process_response(response)
        return success, result_or_error
