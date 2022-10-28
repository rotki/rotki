import base64
import logging
import shutil
from enum import Enum
from typing import Any, Dict, Literal, NamedTuple, Optional, Tuple, Union

from rotkehlchen.data_handler import DataHandler
from rotkehlchen.errors.api import PremiumAuthenticationError, RotkehlchenPermissionError
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.utils.misc import ts_now

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
    payload: Optional[Dict[str, Any]]


class PremiumSyncManager():

    def __init__(self, data: DataHandler, password: str) -> None:
        # Initialize this with the value saved in the DB
        with data.db.conn.read_ctx() as cursor:
            self.last_data_upload_ts = data.db.get_setting(cursor, name='last_data_upload_ts')
        self.data = data
        self.password = password
        self.premium: Optional[Premium] = None

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
            metadata = self.premium.query_last_data_metadata()
        except (RemoteError, PremiumAuthenticationError) as e:
            log.debug('can sync data from server failed', error=str(e))
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        if new_account:
            return SyncCheckResult(can_sync=CanSync.YES, message='', payload=None)

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
        )

    def _sync_data_from_server_and_replace_local(self) -> Tuple[bool, str]:
        """
        Performs syncing of data from server and replaces local db

        Returns true for success and False for error/failure

        May raise:
        - PremiumAuthenticationError due to an UnableToDecryptRemoteData
        coming from  decompress_and_decrypt_db. This happens when the given password
        does not match the one on the saved DB.
        """
        if self.premium is None:
            return False, 'Pulling failed. User does not have active premium.'

        try:
            result = self.premium.pull_data()
        except (RemoteError, PremiumAuthenticationError) as e:
            log.debug('sync from server -- pulling failed.', error=str(e))
            return False, f'Pulling failed: {str(e)}'

        if result['data'] is None:
            log.debug('sync from server -- no data found.')
            return False, 'No data found'

        try:
            self.data.decompress_and_decrypt_db(self.password, result['data'])
        except UnableToDecryptRemoteData as e:
            raise PremiumAuthenticationError(
                'The given password can not unlock the database that was retrieved  from '
                'the server. Make sure to use the same password as when the account was created.',
            ) from e

        return True, ''

    def check_if_should_sync(self, force_upload: bool) -> bool:
        # if user has no premium do nothing
        if self.premium is None:
            return False

        with self.data.db.conn.read_ctx() as cursor:
            if not self.data.db.get_setting(cursor, 'premium_should_sync') and not force_upload:
                return False

        # upload only once per hour
        diff = ts_now() - self.last_data_upload_ts
        if diff < 3600 and not force_upload:
            return False

        return True

    def maybe_upload_data_to_server(self, force_upload: bool = False) -> bool:
        assert self.premium is not None, 'caller should make sure premium exists'
        log.debug('Starting maybe_upload_data_to_server')
        with self.data.db.user_write() as cursor:
            try:
                metadata = self.premium.query_last_data_metadata()
            except (RemoteError, PremiumAuthenticationError) as e:
                log.debug('upload to server -- fetching metadata error', error=str(e))
                return False
            b64_encoded_data, our_hash = self.data.compress_and_encrypt_db(self.password)

            log.debug(
                'CAN_PUSH',
                ours=our_hash,
                theirs=metadata.data_hash,
            )
            if our_hash == metadata.data_hash and not force_upload:
                log.debug('upload to server stopped -- same hash')
                # same hash -- no need to upload anything
                return False

            our_last_write_ts = self.data.db.get_setting(cursor=cursor, name='last_write_ts')
            if our_last_write_ts <= metadata.last_modify_ts and not force_upload:
                # Server's DB was modified after our local DB
                log.debug(
                    f'upload to server stopped -- remote db({metadata.last_modify_ts}) '
                    f'more recent than local({our_last_write_ts})',
                )
                return False

            data_bytes_size = len(base64.b64decode(b64_encoded_data))
            if data_bytes_size < metadata.data_size and not force_upload:
                # Let's be conservative.
                # TODO: Here perhaps prompt user in the future
                log.debug(
                    f'upload to server stopped -- remote db({metadata.data_size}) '
                    f'bigger than local({data_bytes_size})',
                )
                return False

            try:
                self.premium.upload_data(
                    data_blob=b64_encoded_data,
                    our_hash=our_hash,
                    last_modify_ts=our_last_write_ts,
                    compression_type='zlib',
                )
            except (RemoteError, PremiumAuthenticationError) as e:
                log.debug('upload to server -- upload error', error=str(e))
                return False

            # update the last data upload value
            self.last_data_upload_ts = ts_now()
            self.data.db.set_setting(cursor, name='last_data_upload_ts', value=self.last_data_upload_ts)  # noqa: E501

        log.debug('upload to server -- success')
        return True

    def sync_data(self, action: Literal['upload', 'download']) -> Tuple[bool, str]:
        msg = ''
        if action == 'upload':
            if self.check_if_should_sync(force_upload=True) is False:
                success = False
            else:
                success = self.maybe_upload_data_to_server(force_upload=True)

            if not success:
                msg = 'Upload failed'
            return success, msg

        return self._sync_data_from_server_and_replace_local()

    def _sync_if_allowed(
        self,
        sync_approval: Literal['yes', 'no', 'unknown'],
        result: SyncCheckResult,
    ) -> None:
        if result.can_sync == CanSync.ASK_USER:
            if sync_approval == 'unknown':
                log.info('Remote DB is possibly newer. Ask user.')
                raise RotkehlchenPermissionError(result.message, result.payload)

            if sync_approval == 'yes':
                log.info('User approved data sync from server')
                # this may raise due to password
                self._sync_data_from_server_and_replace_local()

            else:
                log.debug('Could sync data from server but user refused')
        elif result.can_sync == CanSync.YES:
            log.info('User approved data sync from server')
            self._sync_data_from_server_and_replace_local()  # this may raise due to password

    def _abort_new_syncing_premium_user(
            self,
            username: str,
            original_exception: Union[PremiumAuthenticationError, RemoteError],
    ) -> None:
        """At this point we are at a new user trying to create an account with
        premium API keys and we failed. But a directory was created. Remove it.
        But create a backup of it in case something went really wrong
        and the directory contained data we did not want to lose"""
        shutil.move(
            self.data.user_data_dir,  # type: ignore
            self.data.data_directory / f'auto_backup_{username}_{ts_now()}',
        )
        raise PremiumAuthenticationError(
            f'Could not verify keys for the new account. {str(original_exception)}',  # noqa: E501
        ) from original_exception

    def try_premium_at_start(
            self,
            given_premium_credentials: Optional[PremiumCredentials],
            username: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            sync_database: bool,
    ) -> Optional[Premium]:
        """
        Check if new user provided api pair or we already got one in the DB

        Returns the created premium if user's premium credentials were fine.

        If not it will raise PremiumAuthenticationError.

        If no credentials were given it returns None
        """

        if given_premium_credentials is not None:
            assert create_new, 'We should never get here for an already existing account'

            try:
                self.premium = premium_create_and_verify(given_premium_credentials)
            except (PremiumAuthenticationError, RemoteError) as e:
                self._abort_new_syncing_premium_user(username=username, original_exception=e)

        # else, if we got premium data in the DB initialize it and try to sync with the server
        with self.data.db.conn.read_ctx() as cursor:
            db_credentials = self.data.db.get_rotkehlchen_premium(cursor)
        if db_credentials:
            assert not create_new, 'We should never get here for a new account'
            try:
                self.premium = premium_create_and_verify(db_credentials)
            except (PremiumAuthenticationError, RemoteError) as e:
                message = (
                    f'Could not authenticate with the rotkehlchen server with '
                    f'the API keys found in the Database. Error: {str(e)}'
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
                    self._sync_if_allowed(sync_approval, result)
                except PremiumAuthenticationError as e:
                    self._abort_new_syncing_premium_user(username=username, original_exception=e)

            self.data.db.set_rotkehlchen_premium(self.premium.credentials)
        else:
            self._sync_if_allowed(sync_approval, result)

        # Success, return premium
        return self.premium
