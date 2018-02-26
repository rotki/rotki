import tempfile
import shutil
import os
from json.decoder import JSONDecodeError
import zlib
from rotkelchen.crypto import encrypt, decrypt

from rotkelchen.utils import (
    createTimeStamp,
    rlk_jsonloads,
    rlk_jsondumps,
    is_number,
    get_pair_position,
)
from rotkelchen.history import get_external_trades, EXTERNAL_TRADES_FILE
from rotkelchen.fval import FVal
from rotkelchen.inquirer import FIAT_CURRENCIES
from rotkelchen.dbhandler import DBHandler
from rotkelchen.errors import AuthenticationError

import logging
logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "01/08/2015"
STATS_FILE = "value.txt"

empty_settings = {
    'ui_floating_precision': 2,
    'main_currency': 'EUR',
    'historical_data_start_date': DEFAULT_START_DATE,
}


otc_fields = [
    'otc_time',
    'otc_pair',
    'otc_type',
    'otc_amount',
    'otc_rate',
    'otc_fee',
    'otc_link',
    'otc_notes'
]
otc_optional_fields = ['otc_fee', 'otc_link', 'otc_notes']
otc_numerical_fields = ['otc_amount', 'otc_rate', 'otc_fee']


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

    if data['otc_type'] not in ('buy', 'sell'):
        return None, 'Trade type can only be buy or sell'

    try:
        timestamp = createTimeStamp(data['otc_time'], formatstr='%d/%m/%Y %H:%M')
    except ValueError as e:
        return None, 'Could not process the given datetime: {}'.format(e)

    return timestamp, ''


class DataHandler(object):

    def __init__(self, data_directory):

        self.data_directory = data_directory

        try:
            with open(os.path.join(self.data_directory, 'settings.json')) as f:
                self.settings = rlk_jsonloads(f.read())
        except JSONDecodeError as e:
            logger.critical('settings.json file could not be decoded and is corrupt: {}'.format(e))
            self.settings = empty_settings
        except FileNotFoundError:
            self.settings = empty_settings

        self.db = None
        self.eth_tokens = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'eth_tokens.json'), 'r') as f:
            self.eth_tokens = rlk_jsonloads(f.read())

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
        return self.settings['main_currency']

    def historical_start_date(self):
        return self.settings.get('historical_data_start_date', DEFAULT_START_DATE)

    def save_balances_data(self, data):
        self.db.write_balances_data(data)

    def write_owned_eth_tokens(self, tokens):
        self.db.write_owned_tokens(tokens)

    def add_blockchain_account(self, blockchain, account):
        self.db.add_blockchain_account(blockchain, account)

    def remove_blockchain_account(self, blockchain, account):
        self.db.remove_blockchain_account(blockchain, account)

    def set_premium_credentials(self, api_key, api_secret):
        self.db.set_rotkehlchen_premium(api_key, api_secret)

    def set_main_currency(self, currency, accountant):
        self.settings['main_currency'] = currency
        accountant.set_main_currency(currency)
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

    def set_ui_floating_precision(self, val):
        self.settings['ui_floating_precision'] = val
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

    def set_settings(self, settings, accountant):
        self.settings = settings
        accountant.set_main_currency(settings['main_currency'])
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

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
        return get_external_trades(self.data_directory)

    def add_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        rate = float(data['otc_rate'])
        amount = float(data['otc_amount'])
        cost = rate * amount
        pair = data['otc_pair']
        external_trades = get_external_trades(self.data_directory)
        external_trades.append({
            'timestamp': timestamp,
            'pair': pair,
            'type': data['otc_type'],
            'rate': rate,
            'cost': cost,
            # for now cost/fee currency is always second.
            # TODO: Make it configurable
            'cost_currency': get_pair_position(pair, 'second'),
            'fee_currency': get_pair_position(pair, 'second'),
            'fee': data['otc_fee'],
            'amount': amount,
            'location': 'external',
            'link': data['otc_link'],
            'notes': data['otc_notes'],
        })
        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def edit_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        rate = float(data['otc_rate'])
        amount = float(data['otc_amount'])
        cost = rate * amount
        pair = data['otc_pair']
        external_trades = get_external_trades(self.data_directory)

        # TODO: When we switch to sql, editing should be done with the primary key
        found = False
        for idx, trade in enumerate(external_trades):
            if timestamp == trade['timestamp']:
                external_trades[idx] = {
                    'timestamp': timestamp,
                    'pair': pair,
                    'type': data['otc_type'],
                    'rate': rate,
                    'cost': cost,
                    # for now cost/fee currency is always second.
                    # TODO: Make it configurable
                    'cost_currency': get_pair_position(pair, 'second'),
                    'fee_currency': get_pair_position(pair, 'second'),
                    'fee': data['otc_fee'],
                    'amount': amount,
                    'location': 'external',
                    'link': data['otc_link'],
                    'notes': data['otc_notes'],
                }
                found = True
                break

        if not found:
            return False, 'Could not find the requested trade for editing'

        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def delete_external_trade(self, data):
        external_trades = get_external_trades(self.data_directory)
        # TODO: When using sql just use primary key as id
        found_idx = -1
        for idx, trade in enumerate(external_trades):
            if trade['timestamp'] == data['timestamp']:
                found_idx = idx
                break

        if found_idx == -1:
            return False, 'Could not find the requested trade for deletion'

        del external_trades[found_idx]
        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def compress_and_encrypt_db(self, password):
        """ Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdb = os.path.join(tmpdirname, 'temp.db')
            self.db.export_unencrypted(tempdb)
            with open(tempdb, 'rb') as f:
                data_blob = f.read()

        compressed_data = zlib.compress(data_blob, level=9)
        encrypted_data = encrypt(password.encode(), compressed_data)
        print('COMPRESSED-ENCRYPTED LENGTH: {}'.format(len(encrypted_data)))

        return encrypted_data.encode()

    def decompress_and_decrypt_db(self, password, encrypted_data):
        """ Decrypt and decompress the encrypted data we receive from the server

        If succesfull then replace our local Database"""
        decrypted_data = decrypt(password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data, password)
