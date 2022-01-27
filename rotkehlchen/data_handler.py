import base64
import hashlib
import logging
import shutil
import tempfile
import time
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors import AuthenticationError, SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import B64EncodedBytes, B64EncodedString, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DataHandler():

    def __init__(self, data_directory: Path, msg_aggregator: MessagesAggregator):

        self.logged_in = False
        self.data_directory = data_directory
        self.username = 'no_user'
        self.password = ''
        self.msg_aggregator = msg_aggregator

    def logout(self) -> None:
        if self.logged_in:
            self.username = 'no_user'
            self.password = ''
            self.user_data_dir: Optional[Path] = None
            self.db.update_owned_assets_in_globaldb()
            del self.db
            self.logged_in = False

    def change_password(self, new_password: str) -> bool:
        success: bool = False

        if self.logged_in:
            success = self.db.change_password(new_password)
            self.password = new_password

        return success

    def unlock(
            self,
            username: str,
            password: str,
            create_new: bool,
            initial_settings: Optional[ModifiableDBSettings] = None,
    ) -> Path:
        """Unlocks a user, either logging them in or creating a new user

        May raise:
        - SystemPermissionError if there are permission errors when accessing the DB
        or a directory in the user's filesystem
        - AuthenticationError if the given user does not exist, or if
        sqlcipher version problems are detected
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error.
        """
        user_data_dir = self.data_directory / username
        if create_new:
            try:
                if (user_data_dir / 'rotkehlchen.db').exists():
                    raise AuthenticationError(
                        f'User {username} already exists. User data dir: {user_data_dir}',
                    )

                user_data_dir.mkdir(exist_ok=True)
            except PermissionError as e:
                raise SystemPermissionError(
                    f'Failed to create directory for user: {str(e)}',
                ) from e

        else:
            try:
                if not user_data_dir.exists():
                    raise AuthenticationError('User {} does not exist'.format(username))

                if not (user_data_dir / 'rotkehlchen.db').exists():
                    raise PermissionError

            except PermissionError as e:
                # This is bad. User directory exists but database is missing.
                # Or either DB or user directory can't be accessed due to permissions
                # Make a backup of the directory that user should probably remove
                # on their own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    self.data_directory / f'auto_backup_{username}_{ts_now()}',
                )

                raise SystemPermissionError(
                    'User {} exists but DB is missing. Somehow must have been manually '
                    'deleted or is corrupt or access permissions do not allow reading. '
                    'Please recreate the user account. '
                    'A backup of the user directory was created.'.format(username),
                ) from e

        self.db: DBHandler = DBHandler(
            user_data_dir=user_data_dir,
            password=password,
            msg_aggregator=self.msg_aggregator,
            initial_settings=initial_settings,
        )
        self.user_data_dir = user_data_dir
        self.logged_in = True
        self.username = username
        self.password = password
        return user_data_dir

    def main_currency(self) -> Asset:
        return self.db.get_main_currency()

    def add_ignored_assets(self, assets: List[Asset]) -> Tuple[Optional[List[Asset]], str]:
        """Adds ignored assets to the DB.

        If any of the given assets is already in the DB the function does nothing
        and returns an error message.
        """
        ignored_assets = self.db.get_ignored_assets()
        for asset in assets:
            if asset in ignored_assets:
                msg = f'{asset.identifier} is already in ignored assets'
                return None, msg

        for asset in assets:
            self.db.add_to_ignored_assets(asset)

        return self.db.get_ignored_assets(), ''

    def remove_ignored_assets(self, assets: List[Asset]) -> Tuple[Optional[List[Asset]], str]:
        """Removes ignored assets from the DB.

        If any of the given assets is not in the DB the call function does nothing
        and returns an error message.
        """
        ignored_assets = self.db.get_ignored_assets()
        for asset in assets:
            if asset not in ignored_assets:
                msg = f'{asset.identifier} is not in ignored assets'
                return None, msg

        for asset in assets:
            self.db.remove_from_ignored_assets(asset)

        return self.db.get_ignored_assets(), ''

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
        users = {}
        for x in self.data_directory.iterdir():
            try:
                if x.is_dir() and (x / 'rotkehlchen.db').exists():
                    users[x.stem] = 'loggedin' if x.stem == self.username else 'loggedout'
            except PermissionError:
                # ignore directories that can't be accessed
                continue

        return users

    def compress_and_encrypt_db(self, password: str) -> Tuple[B64EncodedBytes, str]:
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        log.info('Compress and encrypt DB')
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdb = Path(tmpdirname) / 'temp.db'
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

        May Raise:
        - UnableToDecryptRemoteData due to decrypt()
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error.
        - SystemPermissionError if the DB file permissions are not correct
        """
        log.info('Decompress and decrypt DB')

        # First make a backup of the DB we are about to replace
        date = timestamp_to_date(ts=ts_now(), formatstr='%Y_%m_%d_%H_%M_%S', treat_as_local=True)
        shutil.copyfile(
            self.data_directory / self.username / 'rotkehlchen.db',
            self.data_directory / self.username / f'rotkehlchen_db_{date}.backup',
        )

        decrypted_data = decrypt(password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data, password)
