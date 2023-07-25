import base64
import hashlib
import logging
import shutil
import tempfile
import zlib
from pathlib import Path
from typing import Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import B64EncodedBytes
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BUFFERSIZE = 64 * 1024


class DataHandler:

    def __init__(
            self,
            data_directory: Path,
            msg_aggregator: MessagesAggregator,
            sql_vm_instructions_cb: int,
    ):
        self.logged_in = False
        self.data_directory = data_directory
        self.username = 'no_user'
        self.msg_aggregator = msg_aggregator
        self.sql_vm_instructions_cb = sql_vm_instructions_cb

    def logout(self) -> None:
        if self.logged_in:
            self.username = 'no_user'
            self.user_data_dir: Optional[Path] = None
            db = getattr(self, 'db', None)
            if db is not None:
                with self.db.conn.read_ctx() as cursor:
                    self.db.update_owned_assets_in_globaldb(cursor)
                self.db.logout()
            self.logged_in = False

    def unlock(
            self,
            username: str,
            password: str,
            create_new: bool,
            resume_from_backup: bool,
            initial_settings: Optional[ModifiableDBSettings] = None,
    ) -> Path:
        """Unlocks a user, either logging them in or creating a new user

        May raise:
        - SystemPermissionError if there are permission errors when accessing the DB
        or a directory in the user's filesystem
        - AuthenticationError if the given user does not exist, or if
        sqlcipher version problems are detected
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - DBSchemaError if database schema is malformed
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
                    f'Failed to create directory for user: {e!s}',
                ) from e

        else:
            try:
                if not user_data_dir.exists():
                    raise AuthenticationError(f'User {username} does not exist')

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
            sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            resume_from_backup=resume_from_backup,
        )
        self.user_data_dir = user_data_dir
        self.logged_in = True
        self.username = username
        return user_data_dir

    def add_ignored_assets(self, assets: list[Asset]) -> tuple[Optional[set[str]], str]:
        """Adds ignored assets to the DB.

        If any of the given assets is already in the DB the function does nothing
        and returns an error message.

        Returns the ignored asset identifiers after addition for success and `None`, msg for error
        """
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor)
            for asset in assets:
                if asset.identifier in ignored_asset_ids:
                    msg = f'{asset.identifier} is already in ignored assets'
                    return None, msg

            with self.db.user_write() as write_cursor:
                for asset in assets:
                    self.db.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)

            return self.db.get_ignored_asset_ids(cursor), ''

    def remove_ignored_assets(self, assets: list[Asset]) -> tuple[Optional[set[str]], str]:
        """Removes ignored assets from the DB.

        If any of the given assets is not in the DB the call function does nothing
        and returns an error message.

        Returns the ignored asset identifiers after removal for success and `None`, msg for error
        """
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor)
            for asset in assets:
                if asset.identifier not in ignored_asset_ids:
                    msg = f'{asset.identifier} is not in ignored assets'
                    return None, msg

            with self.db.user_write() as write_cursor:
                for asset in assets:
                    self.db.remove_from_ignored_assets(write_cursor=write_cursor, asset=asset)

            return self.db.get_ignored_asset_ids(cursor), ''

    def get_users(self) -> dict[str, str]:
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

    def compress_and_encrypt_db(self) -> tuple[B64EncodedBytes, str]:
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        compressor = zlib.compressobj(level=9)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
            tempdbpath = Path(tempdbfile.name)
            log.info(f'Compress and encrypt DB at temporary path: {tempdbpath}')
            tempdbfile.close()  # close the file to allow re-opening by export_unencrypted in windows https://github.com/rotki/rotki/issues/5051  # noqa: E501
            self.db.export_unencrypted(tempdbpath)
            source_data = bytearray()
            compressed_data = bytearray()
            with open(tempdbpath, 'rb') as src_f:
                block = src_f.read(BUFFERSIZE)
                while block:
                    source_data += block
                    compressed_data += compressor.compress(block)
                    block = src_f.read(BUFFERSIZE)

                compressed_data += compressor.flush()

        original_data_hash = base64.b64encode(
            hashlib.sha256(source_data).digest(),
        ).decode()
        encrypted_data = encrypt(self.db.password.encode(), bytes(compressed_data))
        # cleanup temp file to avoid windows problem (https://github.com/rotki/rotki/issues/5051)
        tempdbpath.unlink()
        return B64EncodedBytes(encrypted_data.encode()), original_data_hash

    def decompress_and_decrypt_db(self, encrypted_data: bytes) -> None:
        """Decrypt and decompress the encrypted data we receive from the server

        If successful then replace our local Database

        May Raise:
        - UnableToDecryptRemoteData due to decrypt()
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - SystemPermissionError if the DB file permissions are not correct
        """
        log.info('Decompress and decrypt DB')
        # First make a backup of the DB we are about to replace
        date = timestamp_to_date(ts=ts_now(), formatstr='%Y_%m_%d_%H_%M_%S', treat_as_local=True)
        shutil.copyfile(
            self.data_directory / self.username / 'rotkehlchen.db',
            self.data_directory / self.username / f'rotkehlchen_db_{date}.backup',
        )

        decrypted_data = decrypt(self.db.password.encode(), base64.b64encode(encrypted_data).decode())  # noqa: E501
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data)
