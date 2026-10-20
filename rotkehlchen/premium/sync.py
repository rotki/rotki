import logging
import shutil
import tempfile
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.constants.misc import USERSDIR_NAME
from rotkehlchen.crypto import is_backup_format
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.misc import plaintext_db_integrity_check
from rotkehlchen.errors.api import (
    PremiumAuthenticationError,
    PremiumPermissionError,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.misc import (
    BackupTooLargeError,
    DataIntegrityError,
    RemoteBackupDowngrade,
    RemoteBackupError,
    RemoteBackupMismatch,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    Premium,
    PremiumCredentials,
    RemoteMetadata,
    premium_create_and_verify,
)
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.data_handler import DataHandler
    from rotkehlchen.data_migrations.manager import DataMigrationManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CanSync(Enum):
    YES = 0
    NO = 1
    ASK_USER = 2


class SyncCheckResult(NamedTuple):
    # The result of the sync check
    can_sync: CanSync
    # If result is ASK_USER, what should the message be?
    message: str
    payload: dict[str, Any] | None
    # The metadata the decision was made on. Set whenever syncing is allowed, so that the
    # pulled backup can be checked against the same last_modify_ts.
    remote_metadata: RemoteMetadata | None = None


class PremiumSyncManager(LockableQueryMixIn):

    def __init__(self, migration_manager: DataMigrationManager, data: DataHandler) -> None:
        super().__init__()
        # Initialize this with the value saved in the DB
        with data.db.conn.read_ctx() as cursor:
            # These 2 vars contain the timestamp of our side. When did this DB try to upload
            self.last_data_upload_ts = data.db.get_static_cache(
                cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
            )
            self.last_data_upload_ts = Timestamp(0) if self.last_data_upload_ts is None else self.last_data_upload_ts  # noqa: E501
            self.last_upload_attempt_ts = self.last_data_upload_ts
        # This contains the last known successful DB upload timestamp in the remote.
        self.last_remote_data_upload_ts = 0  # gets populated only after the first API call
        self.data = data
        self.migration_manager = migration_manager
        self.premium: Premium | None = None

    def _query_last_data_metadata(self) -> RemoteMetadata:
        """Query remote metadata and keep up to date the last remote data upload ts"""
        assert self.premium is not None, 'caller should make sure premium exists'
        metadata = self.premium.query_last_data_metadata()
        self.last_remote_data_upload_ts = metadata.upload_ts
        return metadata

    def _can_sync_data_from_server(self, new_account: bool) -> SyncCheckResult:
        """
        Checks if the remote data can be pulled from the server.

        Returns a SyncCheckResult denoting whether we can pull for sure,
        whether we can't pull or whether the user should be asked. If the user
        should be asked a message is also returned
        """
        log.debug('can sync data from server -- start')
        if self.premium is None:
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        try:
            metadata = self._query_last_data_metadata()
        except (RemoteError, PremiumAuthenticationError) as e:
            log.debug('can sync data from server failed', error=str(e))
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        if new_account:
            return SyncCheckResult(
                can_sync=CanSync.YES,
                message='',
                payload=None,
                remote_metadata=metadata,
            )

        with self.data.db.conn.read_ctx() as cursor:
            if not self.data.db.get_setting(cursor, name='premium_should_sync'):
                # If it's not a new account and the db setting for premium syncing is off stop
                return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

            our_last_write_ts = self.data.db.get_setting(cursor, name='last_write_ts')

        local_more_recent = our_last_write_ts >= metadata.last_modify_ts
        if local_more_recent:
            log.debug('sync from server stopped -- local is newer')
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        return SyncCheckResult(
            can_sync=CanSync.ASK_USER,
            message='Detected remote database more recent than local. ',
            payload={
                'local_last_modified': our_last_write_ts,
                'remote_last_modified': metadata.last_modify_ts,
            },
            remote_metadata=metadata,
        )

    def _sync_data_from_server_and_replace_local(
            self,
            perform_migrations: bool,
            remote_metadata: RemoteMetadata | None,
    ) -> tuple[bool, str, Timestamp | None]:
        """
        Performs syncing of data from server and replaces local db. If perform_migrations
        is True then once pulled any needed migrations will be performed. Otherwise,
        they are not and are expected to be done later down the line where all related
        modules are initialized.

        remote_metadata is the metadata that justified the pull, and the backup must carry
        the same last_modify_ts. Only a pull the user forced passes None, and then the
        metadata is queried here.

        Returns true for success and False for error/failure, an error message and the
        authenticated last_modify_ts of the restored backup. That timestamp is None for a
        legacy backup, which has none, and on failure.

        May raise:
        - PremiumAuthenticationError due to an UnableToDecryptRemoteData
        coming from decrypt_db. This happens when the given password
        does not match the one on the saved DB.
        - RemoteBackupError if the backup is refused. It needs a newer rotki version, is in
        the legacy format after this device already synced the current one, or does not
        match remote_metadata.
        """
        if self.premium is None:
            return False, 'Pulling failed. User does not have active premium.', None

        try:
            if remote_metadata is None:
                remote_metadata = self._query_last_data_metadata()
            result = self.premium.pull_data()
        except (RemoteError, PremiumAuthenticationError) as e:
            log.debug('sync from server -- pulling failed.', error=str(e))
            return False, f'Pulling failed: {e!s}', None

        if result is None:
            return False, 'No data found', None

        if not is_backup_format(result):
            with self.data.db.conn.read_ctx() as cursor:
                v1_synced_ts = self.data.db.get_static_cache(
                    cursor=cursor,
                    name=DBCacheStatic.LAST_PREMIUM_BACKUP_V1_SYNC_TS,
                )
            if v1_synced_ts is not None:  # refuse before running the unauthenticated decryption
                raise RemoteBackupDowngrade

        try:
            backup = self.data.decrypt_db(result)
        except UnableToDecryptRemoteData as e:
            raise PremiumAuthenticationError(
                'The given password can not unlock the database that was retrieved  from '
                'the server. Make sure to use the same password as when the account was created.',
            ) from e

        if backup.legacy is False and backup.last_modify_ts != remote_metadata.last_modify_ts:
            # With the check that the remote is newer than local, this stops the server from
            # passing off an older backup as the newer one its metadata reports
            raise RemoteBackupMismatch

        try:
            self.data.restore_db(backup.user_db)
        except DataIntegrityError as e:
            log.error('sync from server -- downloaded db integrity check failed', error=str(e))
            return False, str(e), None

        if backup.legacy is False:  # after the restore, since it replaced the whole DB
            with self.data.db.conn.write_ctx() as write_cursor:  # don't bump last_write_ts
                self.data.db.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.LAST_PREMIUM_BACKUP_V1_SYNC_TS,
                    value=ts_now(),
                )

        # Need to run migrations in case the app was updated since last sync and in
        # case this is a request to sync from the API, where all modules are initialized
        # and can be used during the migration. Otherwise if this is happening at login
        # migrations are run later down the line of the unlock process
        if perform_migrations:
            self.migration_manager.maybe_migrate_data()

        return True, '', backup.last_modify_ts

    def check_if_should_sync(self, force_upload: bool) -> bool:
        # if user has no premium do nothing
        if self.premium is None:
            return False

        try:
            if self.premium.get_capabilities()['max_backup_size_mb'] == 0:
                log.debug('Skipping premium db backup because max size is zero')
                return False
        except (RemoteError, PremiumAuthenticationError) as e:
            log.error('Could not query premium capabilities during sync check due to %s', e)
            return False

        with self.data.db.conn.read_ctx() as cursor:
            if not self.data.db.get_setting(cursor, 'premium_should_sync') and not force_upload:
                return False

        # try an automatic upload only once per hour
        return ts_now() - self.last_upload_attempt_ts > 3600 or force_upload

    @protect_with_lock()
    def maybe_upload_data_to_server(
            self,
            force_upload: bool = False,
    ) -> tuple[bool, str | None]:
        """
        Returns a boolean value denoting whether we can upload the DB to the server.
        In case of error we also return a message to provide information to the user.

        We use a lock to prevent two greenlets from executing this logic at the
        same time since we want to export to plaintext only once to encrypt and that happens
        in a spawned thread inside this function.
        """
        assert self.premium is not None, 'caller should make sure premium exists'
        log.debug('Starting maybe_upload_data_to_server')
        ok, integrity_error = self.data.db.db_integrity_check()
        if not ok:
            message = f'Local database failed the integrity check: {integrity_error}'
            log.error('upload to server aborted -- %s', message)
            self.data.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                data={'uploaded': False, 'actionable': True, 'message': message},
            )
            self.last_upload_attempt_ts = ts_now()
            return False, message

        try:
            metadata = self._query_last_data_metadata()
        except (RemoteError, PremiumAuthenticationError) as e:
            message = 'Fetching metadata error'
            log.debug(f'upload to server -- {message}', error=str(e))
            self.data.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                data={'uploaded': False, 'actionable': False, 'message': message},
            )
            self.last_upload_attempt_ts = ts_now()
            return False, message

        with self.data.db.conn.read_ctx() as cursor:
            our_last_write_ts = self.data.db.get_setting(cursor=cursor, name='last_write_ts')
        if our_last_write_ts <= metadata.last_modify_ts and not force_upload:
            message = 'Remote database is more recent than local'
            log.debug(
                f'upload to server stopped -- remote db({metadata.last_modify_ts}) '
                f'more recent than local({our_last_write_ts})',
            )
            self.data.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                data={'uploaded': False, 'actionable': True, 'message': message},
            )
            self.last_upload_attempt_ts = ts_now()
            return False, message

        try:
            max_backup_size_mb = self.premium.get_capabilities()['max_backup_size_mb']
        except (RemoteError, PremiumAuthenticationError) as e:
            log.warning('Could not query the max backup size, skipping size check', error=str(e))
            max_backup_size_mb = None

        # 0 is the default when the server sent no limit, so we can't tell it from a real one.
        # In both cases we let the server decide.
        max_backup_size_mb = max_backup_size_mb or None

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
            tempdbpath = self.data.db.export_unencrypted(tempdbfile)
            exported_ok, exported_error = plaintext_db_integrity_check(tempdbpath)
            if not exported_ok:
                tempdbpath.unlink(missing_ok=True)
                message = f'Exported database failed the integrity check: {exported_error}'
                log.error('upload to server aborted -- %s', message)
                self.data.msg_aggregator.add_message(
                    message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                    data={'uploaded': False, 'actionable': True, 'message': message},
                )
                self.last_upload_attempt_ts = ts_now()
                return False, message
            try:
                data, our_hash = self.data.compress_and_encrypt_db(
                    tempdbpath=tempdbpath,
                    last_modify_ts=our_last_write_ts,
                    max_size_mb=max_backup_size_mb,
                )
            except BackupTooLargeError as e:
                message = str(e)
                log.error('upload to server aborted -- %s', message)
                self.data.msg_aggregator.add_message(
                    message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                    data={'uploaded': False, 'actionable': False, 'message': message},
                )
                self.last_upload_attempt_ts = ts_now()
                return False, message

        log.debug(
            'CAN_PUSH',
            ours=our_hash,
            theirs=metadata.data_hash,
        )
        if our_hash == metadata.data_hash and not force_upload:
            log.debug('upload to server stopped -- same hash')
            message = 'Remote database is up to date'
            self.data.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                data={'uploaded': False, 'actionable': True, 'message': message},
            )
            self.last_upload_attempt_ts = ts_now()
            return False, message

        data_bytes_size = len(data)
        if data_bytes_size < metadata.data_size and not force_upload:
            with self.data.db.conn.read_ctx() as cursor:
                ask_user_upon_size_discrepancy = self.data.db.get_setting(
                    cursor=cursor, name='ask_user_upon_size_discrepancy',
                )
            if ask_user_upon_size_discrepancy is True:
                message = 'Remote database bigger than the local one'
                log.debug(
                    f'upload to server stopped -- remote db({metadata.data_size}) '
                    f'bigger than local({data_bytes_size})',
                )
                self.data.msg_aggregator.add_message(
                    message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                    data={'uploaded': False, 'actionable': True, 'message': message},
                )
                self.last_upload_attempt_ts = ts_now()
                return False, message

        try:
            self.premium.upload_data(
                data_blob=data,
                our_hash=our_hash,
                last_modify_ts=our_last_write_ts,
            )
        except (RemoteError, PremiumAuthenticationError) as e:
            message = str(e)
            log.debug('upload to server -- upload error', error=message)
            self.data.msg_aggregator.add_message(
                message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
                data={'uploaded': False, 'actionable': False, 'message': message},
            )
            self.last_upload_attempt_ts = ts_now()
            return False, message

        # update the last data upload value
        self.last_data_upload_ts = ts_now()
        self.last_upload_attempt_ts = self.last_data_upload_ts
        self.last_remote_data_upload_ts = self.last_data_upload_ts
        with self.data.db.user_write() as cursor:
            self.data.db.set_static_cache(
                write_cursor=cursor,
                name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
                value=self.last_data_upload_ts,
            )
            self.data.db.set_static_cache(
                write_cursor=cursor,
                name=DBCacheStatic.LAST_PREMIUM_BACKUP_V1_SYNC_TS,
                value=self.last_data_upload_ts,
            )

        self.data.msg_aggregator.add_message(
            message_type=WSMessageType.DATABASE_UPLOAD_RESULT,
            data={'uploaded': True, 'actionable': False, 'message': None},
        )
        log.debug('upload to server -- success')
        return True, None

    def sync_data(
            self,
            action: Literal['upload', 'download'],
            perform_migrations: bool,
    ) -> tuple[bool, str, Timestamp | None]:
        """The timestamp is the authenticated last_modify_ts of a downloaded backup, always
        None for an upload. See _sync_data_from_server_and_replace_local."""
        msg = ''
        if action == 'upload':
            if self.check_if_should_sync(force_upload=True) is False:
                success, error_msg = False, None
            else:
                success, error_msg = self.maybe_upload_data_to_server(force_upload=True)

            if not success:
                msg = 'Upload failed.'
                if error_msg is not None:
                    msg += f' {error_msg}'
            return success, msg, None

        return self._sync_data_from_server_and_replace_local(
            perform_migrations=perform_migrations,
            remote_metadata=None,  # a forced pull, so query what the server has now
        )

    def _sync_if_allowed(
            self,
            sync_approval: Literal['yes', 'no', 'unknown'],
            result: SyncCheckResult,
            perform_migrations: bool,
    ) -> None:
        """May raise:
        - PremiumAuthenticationError if the password can't decrypt the remote backup
        - RemoteBackupError if the remote backup is refused
        """
        # Querying the metadata again here would let the server report one last_modify_ts
        # to pass the "remote is newer" check and another one that matches an older backup
        assert result.can_sync == CanSync.NO or result.remote_metadata is not None
        if result.can_sync == CanSync.ASK_USER:
            if sync_approval == 'unknown':
                log.info('Remote DB is possibly newer. Ask user.')
                raise RotkehlchenPermissionError(result.message, result.payload)

            if sync_approval == 'yes':
                log.info('User approved data sync from server')
                # this may raise due to password
                self._sync_data_from_server_and_replace_local(
                    perform_migrations=perform_migrations,
                    remote_metadata=result.remote_metadata,
                )

            else:
                log.debug('Could sync data from server but user refused')
        elif result.can_sync == CanSync.YES:
            log.info('User approved data sync from server')
            self._sync_data_from_server_and_replace_local(  # may raise due to password
                perform_migrations=perform_migrations,
                remote_metadata=result.remote_metadata,
            )

    @staticmethod
    def maybe_add_device_limit_link(exception: Exception, msg: str) -> str:
        """Adds a placeholder to the error message to be replaced with a link to the docs in
        the frontend if the exception is a PremiumPermissionError."""
        if isinstance(exception, PremiumPermissionError):
            msg += ' _DEVICE_LIMIT_LINK_'

        return msg

    def _abort_new_syncing_premium_user(
            self,
            username: str,
            original_exception: PremiumAuthenticationError | PremiumPermissionError | RemoteError | RemoteBackupError,  # noqa: E501
    ) -> None:
        """At this point we are at a new user trying to create an account with
        premium API keys and we failed. But a directory was created. Remove it.
        But create a backup of it in case something went really wrong
        and the directory contained data we did not want to lose"""
        user_data_dir = self.data.user_data_dir
        self.data.logout()  # wipes self.data.user_data_dir, so store it
        shutil.move(
            user_data_dir,  # type: ignore
            self.data.data_directory / USERSDIR_NAME / f'auto_backup_{username}_{ts_now()}',
        )
        if isinstance(original_exception, RemoteBackupError):  # its message is a full sentence
            raise PremiumAuthenticationError(
                f'Could not restore the backup from the rotki server. {original_exception!s}',
            ) from original_exception

        if isinstance(original_exception, PremiumPermissionError):
            error_prefix = 'Could not activate premium on this device.'
        elif isinstance(original_exception, RemoteError):
            error_prefix = 'Could not reach the rotki server to verify premium keys.'
        else:
            error_prefix = 'Could not verify keys for the new account.'

        raise PremiumAuthenticationError(self.maybe_add_device_limit_link(
            exception=original_exception,
            msg=f'{error_prefix} {original_exception!s}.',
        )) from original_exception

    def try_premium_at_start(
            self,
            given_premium_credentials: PremiumCredentials | None,
            username: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            sync_database: bool,
    ) -> Premium | None:
        """
        Check if new user provided api pair or we already got one in the DB

        Returns the created premium if user's premium credentials were fine.

        If not it will raise PremiumAuthenticationError.

        If no credentials were given it returns None
        """

        if given_premium_credentials is not None:
            assert create_new, 'We should never get here for an already existing account'

            try:
                self.premium = premium_create_and_verify(
                    credentials=given_premium_credentials,
                    username=username,
                    msg_aggregator=self.data.msg_aggregator,
                    db=self.data.db,
                )
            except (PremiumAuthenticationError, PremiumPermissionError, RemoteError) as e:
                self._abort_new_syncing_premium_user(username=username, original_exception=e)

        # else, if we got premium data in the DB initialize it and try to sync with the server
        with self.data.db.conn.read_ctx() as cursor:
            db_credentials = self.data.db.get_rotkehlchen_premium(cursor)
        if db_credentials:
            assert not create_new, 'We should never get here for a new account'
            try:
                self.premium = premium_create_and_verify(
                    credentials=db_credentials,
                    username=username,
                    msg_aggregator=self.data.msg_aggregator,
                    db=self.data.db,
                )
            except (PremiumAuthenticationError, PremiumPermissionError, RemoteError) as e:
                message = (
                    f'Could not authenticate with the rotkehlchen server with '
                    f'the API keys found in the Database. {e}'
                )
                log.error(message)
                raise PremiumAuthenticationError(message) from e

        if self.premium is None:
            return None

        result = self._can_sync_data_from_server(new_account=create_new)
        if create_new:
            # if this is a new account, make sure the api keys are properly stored
            # in the DB
            if sync_database:
                try:
                    self._sync_if_allowed(
                        sync_approval=sync_approval,
                        result=result,
                        perform_migrations=False,  # will be done later during unlock
                    )
                except (PremiumAuthenticationError, RemoteBackupError) as e:
                    self._abort_new_syncing_premium_user(username=username, original_exception=e)

            self.data.db.set_rotkehlchen_premium(self.premium.credentials)
        else:
            try:
                self._sync_if_allowed(
                    sync_approval=sync_approval,
                    result=result,
                    perform_migrations=False,  # will be done later during unlock
                )
            except RemoteBackupError as e:
                # Keep the local DB and premium active, and say why the backup was not used
                log.error('sync from server -- remote backup refused', error=str(e))
                self.data.msg_aggregator.add_error(str(e))

        # Success, return premium
        return self.premium
