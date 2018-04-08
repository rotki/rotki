import tempfile
import shutil
import os
import zlib
import base64
import hashlib
from rotkehlchen.crypto import encrypt, decrypt

from rotkehlchen.utils import (
    createTimeStamp,
    rlk_jsonloads,
    is_number,
    get_pair_position,
)
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import FIAT_CURRENCIES
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import AuthenticationError

import logging
logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "01/08/2015"
STATS_FILE = "value.txt"

otc_fields = [
    'otc_timestamp',
    'otc_pair',
    'otc_type',
    'otc_amount',
    'otc_rate',
    'otc_fee',
    'otc_fee_currency',
    'otc_link',
    'otc_notes'
]
otc_optional_fields = ['otc_fee', 'otc_link', 'otc_notes']
otc_numerical_fields = ['otc_amount', 'otc_rate', 'otc_fee']

VALID_SETTINGS = (
    'main_currency',
    'historical_data_start',
    'eth_rpc_port',
    'ui_floating_precision',
    'last_write_ts',
    'db_version',
    'last_data_upload_ts',
    'premium_should_sync',
)


def check_old_key_value(location, data, new_data, new_key=None):
    key = 'percentage_of_net_usd_in_{}'.format(location)
    if key in data:
        new_data[location if not new_key else new_key] = data[key]


def check_new_key_value(key, data, new_data, new_key=None):
    if not new_key:
        new_key = key
    if key in data:
        new_data[key] = data[key]


def check_otctrade_data_valid(data):
    for field in otc_fields:
        if field not in data:
            return None, '{} was not provided'.format(field)

        if data[field] in ('', None) and field not in otc_optional_fields:
            return None, '{} was empty'.format(field)

        if field in otc_numerical_fields and not is_number(data[field]):
            return None, '{} should be a number'.format(field)

    pair = data['otc_pair']
    first = get_pair_position(pair, 'first')
    second = get_pair_position(pair, 'second')

    if data['otc_fee_currency'] not in (first, second):
        return None, 'Trade fee currency should be one of the two in the currency pair'

    if data['otc_type'] not in ('buy', 'sell'):
        return None, 'Trade type can only be buy or sell'

    try:
        timestamp = createTimeStamp(data['otc_timestamp'], formatstr='%d/%m/%Y %H:%M')
    except ValueError as e:
        return None, 'Could not process the given datetime: {}'.format(e)

    return timestamp, ''


def get_all_eth_tokens():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, 'data', 'eth_tokens.json'), 'r') as f:
        return rlk_jsonloads(f.read())


class DataHandler(object):

    def __init__(self, data_directory):

        self.data_directory = data_directory
        self.db = None
        self.eth_tokens = get_all_eth_tokens()

    def unlock(self, username, password, create_new):
        user_data_dir = os.path.join(self.data_directory, username)
        if create_new:
            if os.path.exists(user_data_dir):
                raise AuthenticationError('User {} already exists'.format(username))
            else:
                os.mkdir(user_data_dir)
        else:
            if not os.path.exists(user_data_dir):
                raise AuthenticationError('User {} does not exist'.format(username))

            if not os.path.exists(os.path.join(user_data_dir, 'rotkehlchen.db')):
                # This is bad. User directory exists but database is missing.
                # Make a backup of the directory that user should probably remove
                # on his own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    os.path.join(self.data_directory, 'backup_%s' % username)
                )

                raise AuthenticationError(
                    'User {} exists but DB is missing. Somehow must have been manually '
                    'deleted or is corrupt. Please recreate the user account.'.format(username))

        self.db = DBHandler(user_data_dir, username, password)
        self.user_data_dir = user_data_dir
        return user_data_dir

    def main_currency(self):
        return self.db.get_main_currency()

    def save_balances_data(self, data):
        self.db.write_balances_data(data)

    def write_owned_eth_tokens(self, tokens):
        self.db.write_owned_tokens(tokens)

    def add_blockchain_account(self, blockchain, account):
        self.db.add_blockchain_account(blockchain, account)

    def remove_blockchain_account(self, blockchain, account):
        self.db.remove_blockchain_account(blockchain, account)

    def add_ignored_asset(self, asset):
        ignored_assets = self.db.get_ignored_assets()
        if asset in ignored_assets:
            return False, '%s already in ignored assets' % asset
        self.db.add_to_ignored_assets(asset)
        return True, ''

    def remove_ignored_asset(self, asset):
        ignored_assets = self.db.get_ignored_assets()
        if asset not in ignored_assets:
            return False, '%s not in ignored assets' % asset
        self.db.remove_from_ignored_assets(asset)
        return True, ''

    def set_premium_credentials(self, api_key, api_secret):
        self.db.set_rotkehlchen_premium(api_key, api_secret)

    def set_main_currency(self, currency, accountant):
        accountant.set_main_currency(currency)
        self.db.set_main_currency(currency)

    def set_settings(self, settings, accountant):
        given_items = list(settings.keys())
        msg = ''

        # ignore invalid settings
        invalid = []
        all_okay = True
        for x in given_items:
            if x not in VALID_SETTINGS:
                invalid.append(x)
                del settings[x]
                all_okay = False

        if not all_okay:
            msg = 'provided settings: {} are invalid'.format(','.join(invalid))

        if 'main_currency' in settings:
            accountant.set_main_currency(settings['main_currency'])

        self.db.set_settings(settings)
        return True, msg

    def get_eth_accounts(self):
        blockchain_accounts = self.db.get_blockchain_accounts()
        return blockchain_accounts['ETH'] if 'ETH' in blockchain_accounts else []

    def set_fiat_balance(self, currency, balance):
        if currency not in FIAT_CURRENCIES:
            return False, 'Provided currency {} is unknown'

        if balance == 0 or balance == '':
            self.db.remove_fiat_balance(currency)
        else:
            try:
                balance = FVal(balance)
            except ValueError:
                return False, 'Provided amount is not a number'

            self.db.add_fiat_balance(currency, str(balance))

        return True, ''

    def get_fiat_balances(self):
        return self.db.get_fiat_balances()

    def get_external_trades(self):
        return self.db.get_external_trades()

    def add_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        self.db.add_external_trade(
            time=timestamp,
            location='external',
            pair=data['otc_pair'],
            trade_type=data['otc_type'],
            amount=data['otc_amount'],
            rate=data['otc_rate'],
            fee=data['otc_fee'],
            fee_currency=data['otc_fee_currency'],
            link=data['otc_link'],
            notes=data['otc_notes'],
        )

        return True, ''

    def edit_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        result, message = self.db.edit_external_trade(
            trade_id=data['otc_id'],
            time=timestamp,
            location='external',
            pair=data['otc_pair'],
            trade_type=data['otc_type'],
            amount=data['otc_amount'],
            rate=data['otc_rate'],
            fee=data['otc_fee'],
            fee_currency=data['otc_fee_currency'],
            link=data['otc_link'],
            notes=data['otc_notes'],
        )

        return result, message

    def delete_external_trade(self, trade_id):
        return self.db.delete_external_trade(trade_id)

    def compress_and_encrypt_db(self, password):
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdb = os.path.join(tmpdirname, 'temp.db')
            self.db.export_unencrypted(tempdb)
            with open(tempdb, 'rb') as f:
                data_blob = f.read()

        original_data_hash = base64.b64encode(
            hashlib.sha256(data_blob).digest()
        ).decode()
        compressed_data = zlib.compress(data_blob, level=9)
        encrypted_data = encrypt(password.encode(), compressed_data)

        return encrypted_data.encode(), original_data_hash

    def decompress_and_decrypt_db(self, password, encrypted_data):
        """Decrypt and decompress the encrypted data we receive from the server

        If succesfull then replace our local Database"""
        decrypted_data = decrypt(password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data, password)
