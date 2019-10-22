import base64
import hashlib
import logging
import os
import shutil
import tempfile
import time
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.datatyping import BalancesData
from rotkehlchen.db.dbhandler import DBHandler, DBSettings
from rotkehlchen.db.settings import db_settings_from_dict
from rotkehlchen.errors import AuthenticationError, DeserializationError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import FIAT_CURRENCIES
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    B64EncodedBytes,
    B64EncodedString,
    BlockchainAddress,
    ChecksumEthAddress,
    FilePath,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_START_DATE = "01/08/2015"


class DataHandler():

    def __init__(self, data_directory: FilePath, msg_aggregator: MessagesAggregator):

        self.logged_in = False
        self.data_directory = data_directory
        self.eth_tokens = AssetResolver().get_all_eth_tokens()
        self.username = 'no_user'
        self.msg_aggregator = msg_aggregator

    def logout(self) -> None:
        if self.logged_in:
            self.username = 'no_user'
            self.user_data_dir: Optional[FilePath] = None
            del self.db
            self.logged_in = False

    def unlock(
            self,
            username: str,
            password: str,
            create_new: bool,
    ) -> FilePath:
        self.username = username
        user_data_dir = FilePath(os.path.join(self.data_directory, username))
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
                # on their own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    os.path.join(
                        self.data_directory,
                        f'auto_backup_{username}_{ts_now()}',
                    ),
                )

                raise AuthenticationError(
                    'User {} exists but DB is missing. Somehow must have been manually '
                    'deleted or is corrupt. Please recreate the user account. '
                    'A backup of the user directory was created.'.format(username))

        self.db: DBHandler = DBHandler(user_data_dir, password, self.msg_aggregator)
        self.user_data_dir = user_data_dir
        self.logged_in = True
        return user_data_dir

    def main_currency(self) -> Asset:
        return self.db.get_main_currency()

    def save_balances_data(self, data: BalancesData, timestamp: Timestamp) -> None:
        """Save the balances data at the given timestamp"""
        self.db.write_balances_data(data=data, timestamp=timestamp)

    def write_owned_eth_tokens(self, tokens: List[EthereumToken]) -> None:
        self.db.write_owned_tokens(tokens)

    def add_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        if blockchain == SupportedBlockchain.ETHEREUM:
            account = to_checksum_address(account)
        self.db.add_blockchain_account(blockchain, account)

    def remove_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        if blockchain == SupportedBlockchain.ETHEREUM:
            account = to_checksum_address(account)
        self.db.remove_blockchain_account(blockchain, account)

    def add_ignored_asset(self, given_asset: str) -> Tuple[bool, str]:
        try:
            asset = Asset(given_asset)
        except UnknownAsset:
            return False, f'Given asset {given_asset} for ignoring is not known/supported'
        except DeserializationError:
            return False, f'Given asset for ignoring is not a string'

        ignored_assets = self.db.get_ignored_assets()
        if asset in ignored_assets:
            return False, f'{asset.identifier} is already in ignored assets'
        self.db.add_to_ignored_assets(asset)
        return True, ''

    def remove_ignored_asset(self, given_asset: str) -> Tuple[bool, str]:
        try:
            asset = Asset(given_asset)
        except UnknownAsset:
            return False, f'Given asset {given_asset} for ignoring is not known/supported'
        except DeserializationError:
            return False, f'Given asset for ignoring is not a string'

        ignored_assets = self.db.get_ignored_assets()
        if asset not in ignored_assets:
            return False, f'{asset.identifier} is not in ignored assets'
        self.db.remove_from_ignored_assets(asset)
        return True, ''

    def set_premium_credentials(
            self,
            api_key: ApiKey,
            api_secret: ApiSecret,
    ) -> None:
        self.db.set_rotkehlchen_premium(api_key, api_secret)

    def set_settings(
            self,
            settings_dict: Dict[str, Any],
            accountant: 'Accountant',
    ) -> bool:
        """Takes in a settings dict with setttings to change and dispatches change in the code"""
        settings = db_settings_from_dict(settings_dict, self.msg_aggregator)
        # ignore invalid settings
        invalid = []
        all_okay = True
        for x in list(settings_dict):  # list() makes copy of the dict since we modify it in loop
            if x not in DBSettings._fields:
                invalid.append(x)
                del settings_dict[x]
                all_okay = False
                continue

            # We need to save booleans as strings in the DB
            deserealized_value = getattr(settings, x)
            if isinstance(deserealized_value, bool):
                settings_dict[x] = str(deserealized_value)

        if not all_okay:
            log.warning(f'provided settings: {",".join(invalid)} are invalid')

        if 'main_currency' in settings_dict:
            accountant.set_main_currency(settings_dict['main_currency'])

        self.db.set_settings(settings_dict)
        return True

    def should_save_balances(self) -> bool:
        """ Returns whether or not we can save data to the database depending on
        the balance data saving frequency setting"""
        last_save = self.db.get_last_balance_save_time()
        settings = self.db.get_settings()
        # Setting is saved in hours, convert to seconds here
        period = settings.balance_save_frequency * 60 * 60
        now = Timestamp(int(time.time()))
        return now - last_save > period

    def get_users(self) -> Dict[str, str]:
        """Returns a dict with all users in the system.

        Each key is a user's name and the value is denoting whether that
        particular user is logged in or not
        """
        users = dict()
        data_dir = Path(self.data_directory)
        for x in data_dir.iterdir():
            if x.is_dir() and (x / 'rotkehlchen.db').exists():
                users[x.stem] = 'loggedin' if x.stem == self.username else 'loggedout'
        return users

    def get_eth_accounts(self) -> List[ChecksumEthAddress]:
        blockchain_accounts = self.db.get_blockchain_accounts()
        return blockchain_accounts.eth

    def set_fiat_balance(
            self,
            currency: str,
            provided_balance: str,
    ) -> Tuple[bool, str]:
        if currency not in FIAT_CURRENCIES:
            return False, 'Provided currency {} is unknown'

        currency_asset = Asset(currency)

        msg = 'Provided balance for set_fiat_balance should be a string'
        assert isinstance(provided_balance, str), msg

        if provided_balance == '':
            self.db.remove_fiat_balance(currency_asset)
        else:
            try:
                balance = FVal(provided_balance)
            except ValueError:
                return False, 'Provided amount is not a number'

            self.db.add_fiat_balance(currency_asset, balance)

        return True, ''

    def get_fiat_balances(self) -> Dict[Asset, str]:
        return self.db.get_fiat_balances()

    def compress_and_encrypt_db(self, password: str) -> Tuple[B64EncodedBytes, str]:
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        log.info('Compress and encrypt DB')
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdb = FilePath(os.path.join(tmpdirname, 'temp.db'))
            self.db.export_unencrypted(tempdb)
            with open(tempdb, 'rb') as f:
                data_blob = f.read()

        original_data_hash = base64.b64encode(
            hashlib.sha256(data_blob).digest(),
        ).decode()
        compressed_data = zlib.compress(data_blob, level=9)
        encrypted_data = encrypt(password.encode(), compressed_data)

        return B64EncodedBytes(encrypted_data.encode()), original_data_hash

    def decompress_and_decrypt_db(self, password: str, encrypted_data: B64EncodedString) -> None:
        """Decrypt and decompress the encrypted data we receive from the server

        If successful then replace our local Database

        Can raise UnableToDecryptRemoteData due to decrypt().
        """
        log.info('Decompress and decrypt DB')

        # First make a backup of the DB we are about to replace
        date = timestamp_to_date(ts=ts_now(), formatstr='%Y_%m_%d_%H_%M_%S')
        shutil.copyfile(
            os.path.join(self.data_directory, self.username, 'rotkehlchen.db'),
            os.path.join(self.data_directory, self.username, f'rotkehlchen_db_{date}.backup'),
        )

        decrypted_data = decrypt(password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data, password)
