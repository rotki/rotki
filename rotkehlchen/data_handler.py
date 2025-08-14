import base64
import hashlib
import logging
import shutil
import zlib
from collections.abc import Sequence
from pathlib import Path

from rotkehlchen.api.websockets.typedefs import DBUploadStatusStep, WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import USERDB_NAME, USERSDIR_NAME
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
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
            self.user_data_dir: Path | None = None
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
            initial_settings: ModifiableDBSettings | None = None,
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
        user_data_dir = self.data_directory / USERSDIR_NAME / username
        if create_new:
            try:
                if (user_data_dir / USERDB_NAME).exists():
                    raise AuthenticationError(
                        f'User {username} already exists. User data dir: {user_data_dir}',
                    )

                user_data_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise SystemPermissionError(
                    f'Failed to create directory for user: {e!s}',
                ) from e

        else:
            try:
                if not user_data_dir.exists():
                    raise AuthenticationError(f'User {username} does not exist')

                if not (user_data_dir / USERDB_NAME).exists():
                    raise PermissionError

            except PermissionError as e:
                # This is bad. User directory exists but database is missing.
                # Or either DB or user directory can't be accessed due to permissions
                # Make a backup of the directory that user should probably remove
                # on their own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    self.data_directory / USERSDIR_NAME / f'auto_backup_{username}_{ts_now()}',
                )

                raise SystemPermissionError(
                    f'User {username} exists but DB is missing. Somehow must have been manually '
                    'deleted or is corrupt or access permissions do not allow reading. '
                    'Please recreate the user account. '
                    'A backup of the user directory was created.',
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

    def add_ignored_assets(self, assets: Sequence[Asset]) -> tuple[set[Asset], set[Asset]]:
        """Adds ignored assets to the DB.

        Returns the set of assets that have been ignored and the set of assets that were already
        ignored.
        """
        already_ignored, to_ignore = set(), set()
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor)
            for asset in assets:
                if asset.identifier in ignored_asset_ids:
                    already_ignored.add(asset)
                else:
                    to_ignore.add(asset)

        with self.db.user_write() as write_cursor:
            for asset in to_ignore:
                self.db.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)

        return to_ignore, already_ignored

    def remove_ignored_assets(self, assets: list[Asset]) -> tuple[set[Asset], set[Asset]]:
        """Removes ignored assets from the DB.

        Returns the set of assets that have been unignored and the set of assets that weren't
        ignored.
        """
        not_ignored, to_unignore = set(), set()
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor)
            for asset in assets:
                if asset.identifier not in ignored_asset_ids:
                    not_ignored.add(asset)
                else:
                    to_unignore.add(asset)

        with self.db.user_write() as write_cursor:
            for asset in to_unignore:
                self.db.remove_from_ignored_assets(write_cursor=write_cursor, asset=asset)

        return to_unignore, not_ignored

    def get_users(self) -> dict[str, str]:
        """Returns a dict with all users in the system.

        Each key is a user's name and the value is denoting whether that
        particular user is logged in or not
        """
        users = {}
        users_dir = self.data_directory / USERSDIR_NAME
        if not users_dir.exists():
            return {}

        for x in users_dir.iterdir():
            try:
                if x.is_dir() and (x / USERDB_NAME).exists():
                    users[x.name] = 'loggedin' if x.name == self.username else 'loggedout'
            except PermissionError:
                # ignore directories that can't be accessed
                continue

        return users

    def compress_and_encrypt_db(self, tempdbpath: Path) -> tuple[bytes, str]:
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        self.msg_aggregator.add_message(
            message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS,
            data={'type': str(DBUploadStatusStep.COMPRESSING)},
        )
        compressor = zlib.compressobj(level=9)
        source_data = bytearray()
        compressed_data = bytearray()
        with open(tempdbpath, 'rb') as src_f:
            block = src_f.read(BUFFERSIZE)
            while block:
                source_data += block
                compressed_data += compressor.compress(block)
                block = src_f.read(BUFFERSIZE)

            compressed_data += compressor.flush()

        self.msg_aggregator.add_message(
            message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS,
            data={'type': str(DBUploadStatusStep.ENCRYPTING)},
        )
        encrypted_data = encrypt(self.db.password.encode(), bytes(compressed_data))
        # We rehash the data on the server side to check that it was uploaded correctly,
        # so the hash we send must be of the encrypted data that is actually uploaded.
        data_hash = base64.b64encode(
            hashlib.sha256(encrypted_data).digest(),
        ).decode()
        # cleanup temp file to avoid windows problem (https://github.com/rotki/rotki/issues/5051)
        tempdbpath.unlink()
        return encrypted_data, data_hash

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
        users_dir = self.data_directory / USERSDIR_NAME
        shutil.copyfile(
            users_dir / self.username / USERDB_NAME,
            users_dir / self.username / f'rotkehlchen_db_{date}.backup',
        )

        decrypted_data = decrypt(self.db.password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data)
