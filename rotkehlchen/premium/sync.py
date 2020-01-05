import base64
import logging
import os
import shutil
from enum import Enum
from typing import NamedTuple, Optional

from typing_extensions import Literal

from rotkehlchen.data_handler import DataHandler
from rotkehlchen.errors import AuthenticationError, RemoteError, RotkehlchenPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

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


class PremiumSyncManager():

    def __init__(self, data: DataHandler, password: str) -> None:
        self.last_data_upload_ts = 0
        self.data = data
        self.password = password
        self.premium = None

    def _can_sync_data_from_server(self, new_account: bool) -> SyncCheckResult:
        """
        Checks if the remote data can be pulled from the server.

        Returns a SyncCheckResult denoting whether we can pull for sure,
        whether we can't pull or whether the user should be asked. If the user
        should be asked a message is also returned
        """
        log.debug('can sync data from server -- start')
        if not self.premium:
            return SyncCheckResult(can_sync=CanSync.NO, message='')

        b64_encoded_data, our_hash = self.data.compress_and_encrypt_db(self.password)

        try:
            metadata = self.premium.query_last_data_metadata()
        except RemoteError as e:
            log.debug('can sync data from server failed', error=str(e))
            return SyncCheckResult(can_sync=CanSync.NO, message='')

        if new_account:
            return SyncCheckResult(can_sync=CanSync.YES, message='')

        if not self.data.db.get_premium_sync():
            # If it's not a new account and the db setting for premium syncin is off stop
            return SyncCheckResult(can_sync=CanSync.NO, message='')

        log.debug(
            'CAN_PULL',
            ours=our_hash,
            theirs=metadata.data_hash,
        )
        if our_hash == metadata.data_hash:
            log.debug('sync from server stopped -- same hash')
            # same hash -- no need to get anything
            return SyncCheckResult(can_sync=CanSync.NO, message='')

        our_last_write_ts = self.data.db.get_last_write_ts()
        if our_last_write_ts >= metadata.last_modify_ts:
            # Local DB is newer than Server DB
            log.debug('sync from server stopped -- local DB more recent than remote')
            return SyncCheckResult(can_sync=CanSync.NO, message='')

        data_bytes_size = len(base64.b64decode(b64_encoded_data))
        if data_bytes_size > metadata.data_size:
            message_prefix = (
                'Detected newer remote database BUT with smaller size than the local one. '
            )

        else:
            message_prefix = 'Detected newer remote database. '

        message = (
            f'{message_prefix}'
            f'Local size: {data_bytes_size} Remote size: {metadata.data_size} '
            f'Local last modified time: {timestamp_to_date(our_last_write_ts)} '
            f'Remote last modified time: {timestamp_to_date(metadata.last_modify_ts)} '
            f'Would you like to replace the local DB with the remote one?'
        )
        return SyncCheckResult(
            can_sync=CanSync.ASK_USER,
            message=message,
        )

    def _sync_data_from_server_and_replace_local(self) -> bool:
        """
        Performs syncing of data from server and replaces local db

        Returns true for success and False for error/failure

        Can raise UnableToDecryptRemoteData due to decompress_and_decrypt_db.
        We let it bubble up so that it can be handled by the uper layer.
        """
        try:
            result = self.premium.pull_data()
        except RemoteError as e:
            log.debug('sync from server -- pulling failed.', error=str(e))
            return False

        self.data.decompress_and_decrypt_db(self.password, result['data'])
        return True

    def maybe_upload_data_to_server(self) -> None:
        # if user has no premium do nothing
        if not self.premium:
            return

        # upload only once per hour
        diff = ts_now() - self.last_data_upload_ts
        if diff < 3600:
            return

        b64_encoded_data, our_hash = self.data.compress_and_encrypt_db(self.password)
        try:
            metadata = self.premium.query_last_data_metadata()
        except RemoteError as e:
            log.debug(
                'upload to server stopped -- query last metadata failed',
                error=str(e),
            )
            return

        log.debug(
            'CAN_PUSH',
            ours=our_hash,
            theirs=metadata.data_hash,
        )
        if our_hash == metadata.data_hash:
            log.debug('upload to server stopped -- same hash')
            # same hash -- no need to upload anything
            return

        our_last_write_ts = self.data.db.get_last_write_ts()
        if our_last_write_ts <= metadata.last_modify_ts:
            # Server's DB was modified after our local DB
            log.debug('upload to server stopped -- remote db more recent than local')
            return

        data_bytes_size = len(base64.b64decode(b64_encoded_data))
        if data_bytes_size < metadata.data_size:
            # Let's be conservative.
            # TODO: Here perhaps prompt user in the future
            log.debug('upload to server stopped -- remote db bigger than local')
            return

        try:
            self.premium.upload_data(
                data_blob=b64_encoded_data,
                our_hash=our_hash,
                last_modify_ts=our_last_write_ts,
                compression_type='zlib',
            )
        except RemoteError as e:
            log.debug('upload to server -- upload error', error=str(e))
            return

        # update the last data upload value
        self.last_data_upload_ts = ts_now()
        self.data.db.update_last_data_upload_ts(self.last_data_upload_ts)
        log.debug('upload to server -- success')

    def try_premium_at_start(
            self,
            given_premium_credentials: Optional[PremiumCredentials],
            username: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
    ) -> Premium:
        """
        Check if new user provided api pair or we already got one in the DB

        Returns the created premium if user's premium credentials were fine.

        If not it will raise AuthenticationError.
        """

        if given_premium_credentials is not None:
            assert create_new, 'We should never get here for an already existing account'

            try:
                self.premium = premium_create_and_verify(given_premium_credentials)
            except AuthenticationError as e:
                log.error('Given API key is invalid')
                # At this point we are at a new user trying to create an account with
                # premium API keys and we failed. But a directory was created. Remove it.
                # But create a backup of it in case something went really wrong
                # and the directory contained data we did not want to lose
                shutil.move(
                    self.data.user_data_dir,
                    os.path.join(
                        self.data.data_directory,
                        f'auto_backup_{username}_{ts_now()}',
                    ),
                )
                raise AuthenticationError(
                    'Could not verify keys for the new account. '
                    '{}'.format(str(e)),
                )

        # else, if we got premium data in the DB initialize it and try to sync with the server
        db_credentials = self.data.db.get_rotkehlchen_premium()
        if db_credentials:
            assert not create_new, 'We should never get here for a new account'
            try:
                self.premium = premium_create_and_verify(db_credentials)
            except AuthenticationError as e:
                message = (
                    f'Could not authenticate with the rotkehlchen server with '
                    f'the API keys found in the Database. Error: {str(e)}'
                )
                log.error(message)
                raise AuthenticationError(message)

        # From this point on we should have a self.premium with valid credentials
        result = self._can_sync_data_from_server(new_account=create_new)
        if result.can_sync == CanSync.ASK_USER:
            if sync_approval == 'unknown':
                log.info('DB data at server newer than local')
                raise RotkehlchenPermissionError(result.message)
            elif sync_approval == 'yes':
                log.info('User approved data sync from server')
                if self._sync_data_from_server_and_replace_local():
                    if create_new:
                        # if we successfully synced data from the server and this is
                        # a new account, make sure the api keys are properly stored
                        # in the DB
                        self.data.db.set_rotkehlchen_premium(self.premium.credentials)
            else:
                log.debug('Could sync data from server but user refused')
        elif result.can_sync == CanSync.YES:
            log.info('User approved data sync from server')
            if self._sync_data_from_server_and_replace_local():
                if create_new:
                    # if we successfully synced data from the server and this is
                    # a new account, make sure the api keys are properly stored
                    # in the DB
                    self.data.db.set_rotkehlchen_premium(self.premium.credentials)

        # else result.can_sync was no, so we do nothing

        # Success, return premium
        return self.premium
