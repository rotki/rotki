from http import HTTPStatus
from typing import Any, Final
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import solana_address_to_identifier
from rotkehlchen.db.utils import table_exists
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import (
    SolanaAddress,
    Timestamp,
    TokenKind,
)

# Test constants
TEST_SOLANA_ADDRESS: Final = SolanaAddress('BENGEso6uSrcCYyRsanYgmDwLi34QSpihU2FX2xvpump')
TEST_OLD_ASSET_IDENTIFIER: Final = 'old_solana_token_id'


@pytest.fixture(name='setup_migration_table')
def _setup_migration_table():
    """Setup user_added_solana_tokens table"""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_added_solana_tokens (
            identifier TEXT NOT NULL UNIQUE,
            FOREIGN KEY (identifier) REFERENCES assets(identifier) ON DELETE CASCADE
        );
        """)


def test_migrate_solana_token_success(rotkehlchen_api_server: APIServer, setup_migration_table) -> None:  # noqa: E501
    """Test successful migration including database references and table cleanup"""
    db_handler = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    # Create old token in global and user db
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO assets (identifier, name, type) VALUES (?, ?, ?)',
            (TEST_OLD_ASSET_IDENTIFIER, (token_name := 'Token 1'), AssetType.OTHER.serialize_for_db()),  # noqa: E501
        )
        write_cursor.execute(
            'INSERT INTO common_asset_details (identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (TEST_OLD_ASSET_IDENTIFIER, (token_symbol := 'TOK1'), None, None, None, None, None),
        )
        write_cursor.execute(
            'INSERT INTO user_added_solana_tokens (identifier) VALUES (?)',
            (TEST_OLD_ASSET_IDENTIFIER,),
        )

    with db_handler.conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO assets(identifier) VALUES(?)', (TEST_OLD_ASSET_IDENTIFIER,))  # noqa: E501
        write_cursor.execute(
            'INSERT INTO timed_balances (category, timestamp, currency, amount, usd_value) VALUES (?, ?, ?, ?, ?)',  # noqa: E501
            (BalanceType.ASSET.serialize_for_db(), Timestamp(1640995200000), TEST_OLD_ASSET_IDENTIFIER, '100.5', '100.5'),  # noqa: E501
        )

    # Perform migration
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'solanatokenmigrationresource'),
        json={
            'old_asset': TEST_OLD_ASSET_IDENTIFIER,
            'address': TEST_SOLANA_ADDRESS,
            'decimals': 6,
            'token_kind': TokenKind.SPL_TOKEN.name.lower(),
            'async_query': False,
        },
    )
    assert_proper_sync_response_with_result(response)

    # Verify new token created correctly
    new_token = Asset(solana_address_to_identifier(
        address=TEST_SOLANA_ADDRESS,
        token_type=TokenKind.SPL_TOKEN,
    )).resolve_to_solana_token()
    assert new_token.name == token_name
    assert new_token.symbol == token_symbol

    # Verify database reference was updated
    with db_handler.conn.read_ctx() as cursor:
        balance_result = cursor.execute(
            'SELECT currency, amount, usd_value FROM timed_balances WHERE currency = ?',
            (new_token.identifier,),
        ).fetchone()
        assert balance_result == (new_token.identifier, '100.5', '100.5')

        # Verify old asset reference is gone
        old_balance_count = cursor.execute(
            'SELECT COUNT(*) FROM timed_balances WHERE currency = ?',
            (TEST_OLD_ASSET_IDENTIFIER,),
        ).fetchone()[0]
        assert old_balance_count == 0

    # Verify table is dropped when empty
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert table_exists(cursor, 'user_added_solana_tokens') is False

    with GlobalDBHandler().conn.read_ctx() as cursor:
        # check that the old asset is gone.
        assert cursor.execute('SELECT COUNT(*) FROM common_asset_details WHERE identifier = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 0  # noqa: E501
        # check that the new asset is present.
        assert cursor.execute('SELECT symbol FROM common_asset_details WHERE identifier = ?', (new_token.identifier,)).fetchall() == [(token_symbol,)]  # noqa: E501
        assert cursor.execute('SELECT name FROM assets WHERE identifier = ?', (new_token.identifier,)).fetchall() == [(token_name,)]  # noqa: E501


@pytest.mark.parametrize(('request_data', 'expected_status', 'expected_msg'), [
    ({  # Token not in migration table
         'old_asset': 'BTC',
         'address': TEST_SOLANA_ADDRESS,
         'decimals': 6,
         'token_kind': TokenKind.SPL_TOKEN.name.lower(),
         'async_query': False,
     }, HTTPStatus.CONFLICT, 'Token does not exist in user_added_solana_tokens table'),
    ({  # Invalid solana address
         'old_asset': TEST_OLD_ASSET_IDENTIFIER,
         'address': 'invalid_address',
         'decimals': 6,
         'token_kind': TokenKind.SPL_TOKEN.name.lower(),
         'async_query': False,
     }, HTTPStatus.BAD_REQUEST, 'Given value invalid_address is not a solana address'),
    ({  # Invalid token kind
         'old_asset': TEST_OLD_ASSET_IDENTIFIER,
         'address': TEST_SOLANA_ADDRESS,
         'decimals': 6,
         'token_kind': 'invalid_kind',
         'async_query': False,
     }, HTTPStatus.BAD_REQUEST, 'Failed to deserialize TokenKind value invalid_kind'),
    ({  # Negative decimals
         'old_asset': TEST_OLD_ASSET_IDENTIFIER,
         'address': TEST_SOLANA_ADDRESS,
         'decimals': -1,
         'token_kind': TokenKind.SPL_TOKEN.name.lower(),
         'async_query': False,
     }, HTTPStatus.BAD_REQUEST, 'Must be greater than or equal to 0.'),
    ({  # Missing required fields
         'address': TEST_SOLANA_ADDRESS,
         'decimals': 6,
         'token_kind': TokenKind.SPL_TOKEN.name.lower(),
         'async_query': False,
     }, HTTPStatus.BAD_REQUEST, 'Missing data for required field'),
])
def test_migrate_solana_token_failures(
        rotkehlchen_api_server: APIServer,
        setup_migration_table: None,
        request_data: dict[str, Any],
        expected_status: HTTPStatus,
        expected_msg: str | None,
) -> None:
    """Test various failure scenarios for solana token migration"""
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'solanatokenmigrationresource'),
        json=request_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=expected_status,
    )


def test_migrate_solana_token_rollback_on_replace_failure(
        rotkehlchen_api_server: APIServer,
        setup_migration_table: None,
) -> None:
    """Test that migrate_solana_token rolls back changes when replace_asset_identifier fails"""
    db_handler = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    # Create old token in global and user db
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO assets (identifier, name, type) VALUES (?, ?, ?)',
            (TEST_OLD_ASSET_IDENTIFIER, 'Token 1', AssetType.OTHER.serialize_for_db()),
        )
        write_cursor.execute(
            'INSERT INTO common_asset_details (identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (TEST_OLD_ASSET_IDENTIFIER, 'TOK1', None, None, None, None, None),
        )
        write_cursor.execute(
            'INSERT INTO user_added_solana_tokens (identifier) VALUES (?)',
            (TEST_OLD_ASSET_IDENTIFIER,),
        )

    with db_handler.conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO assets(identifier) VALUES(?)', (TEST_OLD_ASSET_IDENTIFIER,))  # noqa: E501
        write_cursor.execute(
            'INSERT INTO timed_balances (category, timestamp, currency, amount, usd_value) VALUES (?, ?, ?, ?, ?)',  # noqa: E501
            (BalanceType.ASSET.serialize_for_db(), Timestamp(1640995200000), TEST_OLD_ASSET_IDENTIFIER, '100.5', '100.5'),  # noqa: E501
        )

    with patch.object(db_handler, 'replace_asset_identifier', side_effect=InputError('Mocked replace failure')):  # noqa: E501
        response = requests.post(
            url=api_url_for(rotkehlchen_api_server, 'solanatokenmigrationresource'),
            json={
                'old_asset': TEST_OLD_ASSET_IDENTIFIER,
                'address': TEST_SOLANA_ADDRESS,
                'decimals': 6,
                'token_kind': TokenKind.SPL_TOKEN.name.lower(),
                'async_query': False,
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg='Mocked replace failure',
            status_code=HTTPStatus.CONFLICT,
        )

    # verify rollback: new solana token should be deleted from global database
    new_token_identifier = solana_address_to_identifier(
        address=TEST_SOLANA_ADDRESS,
        token_type=TokenKind.SPL_TOKEN,
    )
    with GlobalDBHandler().conn.read_ctx() as cursor:
        # New token should not exist in global database (rolled back)
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', (new_token_identifier,)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM common_asset_details WHERE identifier = ?', (new_token_identifier,)).fetchone()[0] == 0  # noqa: E501
        # Original token should still exist in global database
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM common_asset_details WHERE identifier = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 1  # noqa: E501
        # Migration table should still contain the old token
        assert cursor.execute('SELECT COUNT(*) FROM user_added_solana_tokens WHERE identifier = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 1  # noqa: E501

    # Verify user database unchanged: old references should still exist
    with db_handler.conn.read_ctx() as cursor:
        for table, column in [('timed_balances', 'currency'), ('assets', 'identifier')]:
            # Old asset should still exist
            assert cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} = ?', (TEST_OLD_ASSET_IDENTIFIER,)).fetchone()[0] == 1  # noqa: E501
            # New asset should not exist
            assert cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} = ?', (new_token_identifier,)).fetchone()[0] == 0  # noqa: E501
