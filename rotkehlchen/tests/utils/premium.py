import os
import tempfile
from http import HTTPStatus
from typing import Literal
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.misc import USERDB_NAME, USERSDIR_NAME
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_GBP, DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.database import mock_db_schema_sanity_check
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Timestamp
from rotkehlchen.user_messages import MessagesAggregator

# Valid format but not "real" premium api key and secret
VALID_PREMIUM_KEY = (
    'kWT/MaPHwM2W1KUEl2aXtkKG6wJfMW9KxI7SSerI6/QzchC45/GebPV9xYZy7f+VKBeh5nDRBJBCYn7WofMO4Q=='
)
VALID_PREMIUM_SECRET = (
    'TEF5dFFrOFcwSXNrM2p1aDdHZmlndFRoMTZQRWJhU2dacTdscUZSeHZTRmJLRm5ZaVRlV2NYU'
    'llYR1lxMjlEdUtRdFptelpCYmlXSUZGRTVDNWx3NDNYbjIx'
)


def mock_query_last_metadata(last_modify_ts, data_hash, data_size):
    def do_mock_query_last_metadata(url, data, timeout):  # pylint: disable=unused-argument
        assert len(data) == 1
        assert 'nonce' in data
        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        payload = (
            f'{{"upload_ts": 1337, '
            f'"last_modify_ts": {last_modify_ts}, '
            f'"data_hash": "{data_hash}",'
            f'"data_size": {data_size}}}'
        )
        return MockResponse(200, payload)

    return do_mock_query_last_metadata


def mock_get_backup(saved_data: bytes | None):
    def do_mock_get_backup(url, timeout, params, data=None):  # pylint: disable=unused-argument
        if data is not None:
            assert len(data) == 1
            assert 'nonce' in data
        assert timeout % ROTKEHLCHEN_SERVER_TIMEOUT == 0
        decoded_data = None if saved_data is None else saved_data
        status_code = HTTPStatus.OK if decoded_data is not None else HTTPStatus.NOT_FOUND
        return MockResponse(status_code, text='', content=decoded_data)

    return do_mock_get_backup


def create_patched_requests_get_for_premium(
        session,
        metadata_last_modify_ts=None,
        metadata_data_hash=None,
        metadata_data_size=None,
        saved_data: bytes | None = None,
        consider_authentication_invalid: bool = False,
):
    def mocked_get(url, *args, **kwargs):
        if consider_authentication_invalid:
            return MockResponse(
                HTTPStatus.UNAUTHORIZED,
                {'error': 'API KEY signature mismatch'},
            )

        if 'last_data_metadata' in url:
            assert metadata_last_modify_ts is not None
            assert metadata_data_hash is not None
            assert metadata_data_size is not None

            implementation = mock_query_last_metadata(
                last_modify_ts=metadata_last_modify_ts,
                data_hash=metadata_data_hash,
                data_size=metadata_data_size,
            )
        elif 'backup' in url:
            implementation = mock_get_backup(saved_data=saved_data)
        else:
            raise ValueError('Unmocked url in session get for premium')

        return implementation(url, *args, **kwargs)

    return patch.object(session, 'get', side_effect=mocked_get)


def create_patched_premium(
        premium_credentials: PremiumCredentials,
        username: str,
        patch_get: bool,
        database: DBHandler,
        metadata_last_modify_ts: Timestamp | None = None,
        metadata_data_hash: str | None = None,
        metadata_data_size: int | None = None,
        saved_data: bytes | None = None,
        consider_authentication_invalid: bool = False,
):
    premium = Premium(
        credentials=premium_credentials,
        username=username,
        msg_aggregator=MessagesAggregator(),
        db=database,
    )
    patched_get = None
    if patch_get:
        patched_get = create_patched_requests_get_for_premium(
            session=premium.session,
            metadata_last_modify_ts=metadata_last_modify_ts,
            metadata_data_hash=metadata_data_hash,
            metadata_data_size=metadata_data_size,
            saved_data=saved_data,
            consider_authentication_invalid=consider_authentication_invalid,
        )
    patched_premium_at_start = patch(
        # note the patch location is in premium/sync.py
        'rotkehlchen.premium.sync.premium_create_and_verify',
        return_value=premium,
    )
    patched_premium_at_set = patch(
        # note the patch location is in rotkehlchen/rotkehlchen.py
        'rotkehlchen.rotkehlchen.premium_create_and_verify',
        return_value=premium,
    )

    def mock_perform_userdb_upgrade_steps(db, progress_handler):
        """The remote encrypted DB in the tests has a remnant combined_trades_view. It's not
        deleted since that normally gets removed in 34->35 and the remove DB starts from 35 which
        I assume was a mistake on our side when testing it. I thought it faster to do a mock in
        the 37->38 upgrade rather than reencrypting it and putting it in the test. And chose
        37->38 since it's the easier to mock the main changes of.
        """
        with db.user_write() as write_cursor:
            write_cursor.execute('DROP VIEW IF EXISTS combined_trades_view;')  # this we add
            write_cursor.execute('DROP TABLE IF EXISTS amm_events;')
            write_cursor.execute('DROP TABLE IF EXISTS aave_events;')
            write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('h', 40);")
            update_table_schema(
                write_cursor=write_cursor,
                table_name='evm_internal_transactions',
                schema="""parent_tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                trace_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT,
                value TEXT NOT NULL,
                FOREIGN KEY(parent_tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
                PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)""",  # noqa: E501
                insert_columns='parent_tx_hash, chain_id, trace_id, from_address, to_address, value',  # noqa: E501
            )

    patched_upgrade_37_38 = patch(
        'rotkehlchen.db.upgrades.v37_v38.perform_userdb_upgrade_steps',
        wraps=mock_perform_userdb_upgrade_steps,
    )
    return patched_premium_at_start, patched_premium_at_set, patched_get, patched_upgrade_37_38


def get_different_hash(given_hash: str) -> str:
    """Given the string hash get one that's different but has same length"""
    new_hash = ''
    for x in given_hash:
        new_hash += chr(ord(x) + 1)

    return new_hash


def setup_starting_environment(
        rotkehlchen_instance: Rotkehlchen,
        username: str,
        first_time: bool,
        same_hash_with_remote: bool,
        newer_remote_db: bool,
        db_can_sync_setting: bool,
        premium_credentials: PremiumCredentials,
        remote_data: bytes | None,
        sync_approval: Literal['yes', 'no', 'unknown'] = 'yes',
        sync_database: bool = True,
):
    """
    Sets up the starting environment for premium testing when the user
    starts up his node either for the first time or logs in an already
    existing account
    """
    with rotkehlchen_instance.data.db.user_write() as cursor:
        if not first_time:
            # Emulate already having the api keys in the DB
            rotkehlchen_instance.data.db.set_rotkehlchen_premium(premium_credentials)

        rotkehlchen_instance.data.db.set_setting(cursor, name='premium_should_sync', value=db_can_sync_setting)  # noqa: E501
        our_last_write_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_write_ts')
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)

    if same_hash_with_remote:
        remote_hash = our_hash
    else:
        remote_hash = get_different_hash(our_hash)

    if newer_remote_db:
        metadata_last_modify_ts = our_last_write_ts + 10
    else:
        metadata_last_modify_ts = our_last_write_ts - 10

    patched_premium_at_start, _, patched_get, patched_upgrade = create_patched_premium(
        premium_credentials=premium_credentials,
        username=username,
        patch_get=True,
        database=rotkehlchen_instance.data.db,
        metadata_last_modify_ts=Timestamp(metadata_last_modify_ts),
        metadata_data_hash=remote_hash,
        metadata_data_size=len(remote_data) if remote_data else 0,
        saved_data=remote_data,
    )

    given_premium_credentials: PremiumCredentials | None
    if first_time:
        given_premium_credentials = premium_credentials
        create_new = True
    else:
        given_premium_credentials = None
        create_new = False

    with patched_premium_at_start, patched_get, mock_db_schema_sanity_check(), patched_upgrade:
        rotkehlchen_instance.premium_sync_manager.try_premium_at_start(
            given_premium_credentials=given_premium_credentials,
            username=username,
            create_new=create_new,
            sync_approval=sync_approval,
            sync_database=sync_database,
        )


def assert_db_got_replaced(rotkehlchen_instance: Rotkehlchen, username: str):
    """For environment setup with setup_starting_environment make sure DB is replaced
    """
    msg = 'Test default main currency should be different from the restored currency'
    assert DEFAULT_TESTS_MAIN_CURRENCY != A_GBP, msg
    # At this point pulling data from rotkehlchen server should have worked
    # and our database should have been replaced. The new data have different
    # main currency
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == A_GBP
    # Also check a copy of our old DB is kept around.
    directory = rotkehlchen_instance.data.data_directory / USERSDIR_NAME / username
    files = [
        os.path.join(directory, f) for f in os.listdir(directory)
        if (not f.endswith('backup') or f.startswith('rotkehlchen_db')) and not f.startswith('rotkehlchen_transient')  # noqa: E501
    ]
    msg = f'Expected 2 or 3 files in the directory but got {files}'
    assert 3 <= len(files) <= 4, msg  # 3rd file is the dbinfo.json and 4th is the wal file
    # The order of the files is not guaranteed
    main_db_exists = False
    backup_db_exists = False
    for file in files:
        if USERDB_NAME in file:
            main_db_exists = True
        elif 'backup' in file:
            backup_db_exists = True

    assert main_db_exists
    assert backup_db_exists
