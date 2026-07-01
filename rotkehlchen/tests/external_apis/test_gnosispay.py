from http import HTTPStatus
from json import dumps, loads
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests
from requests.models import Response

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.gnosispay import GNOSIS_PAY_SAFE_MIGRATION_ID, init_gnosis_pay
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.fixtures.messages import MockedWsMessage
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def mock_unauthorized_requests_get(url, params=None, **kwargs):
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    response._content = b'{"message": "No authorization token was found"}'
    return response


def test_gnosis_pay_skip_refund(database: 'DBHandler', gnosispay_credentials: None) -> None:
    """Test that gnosis pay skips refunds without error, since they are missing data linking
    them to onchain transactions.
    """
    gnosispay = init_gnosis_pay(database)
    assert gnosispay is not None

    def mocked_api(url, *args, **kwargs):
        if kwargs['params']['offset'] == 0:
            return MockResponse(200, """{"results": [{
                "createdAt": "XX",
                "clearedAt": "XX",
                "isPending": false,
                "transactionAmount": "2300",
                "transactionCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "billingAmount": "2300",
                "billingCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "transactionType": "20",
                "mcc": "5661",
                "merchant": {
                    "name": "I-RUN",
                    "city": "CASTELNAU D E",
                    "country": {"name": "France", "numeric": "250", "alpha2": "FR", "alpha3": "FRA"}
                },
                "country": {"name": "France", "numeric": "250", "alpha2": "FR", "alpha3": "FRA"},
                "transactions": [],
                "kind": "Refund",
                "refundCurrency": {"symbol": "EUR", "code": "978", "decimals": 2, "name": "Euro"},
                "refundAmount": "2300"
            }]}""")  # noqa: E501
        else:
            return MockResponse(200, """{"results": []}""")

    with (
        patch.object(gnosispay.session, 'get', mocked_api),
        patch.object(gnosispay, 'write_txdata_to_db') as mock_write_txdata_to_db,
    ):
        gnosispay.get_and_process_transactions(after_ts=Timestamp(0))

    assert mock_write_txdata_to_db.call_count == 0


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_gnosis_pay_unauthorized(database, gnosispay_credentials):
    """Test that gnosis pay sends the session expired message"""
    gnosispay = init_gnosis_pay(database)

    # Patch to avoid requests in the Gnosis pay api
    with patch.object(
        target=gnosispay.session,
        attribute='get',
        side_effect=mock_unauthorized_requests_get,
    ):
        gnosispay.query_remote_for_tx_and_update_events(start_ts=0, end_ts=1)

    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.GNOSISPAY_SESSIONKEY_EXPIRED,
        data={'error': 'Please sign in with GnosisPay again to refresh your data'},
    )


@pytest.mark.parametrize(('tracked_safe', 'missing_type'), [
    ('old', 'new'),
    ('new', 'old'),
    ('both', None),
    ('neither', None),
])
def test_gnosis_pay_safe_migration(
        database: 'DBHandler',
        gnosispay_credentials: None,
        tracked_safe: str,
        missing_type: str | None,
) -> None:
    """Test migration data is cached and only an untracked paired Safe is returned."""
    gnosispay = init_gnosis_pay(database)
    assert gnosispay is not None
    old_safe = deserialize_evm_address('0x1111111111111111111111111111111111111111')
    new_safe = deserialize_evm_address('0x2222222222222222222222222222222222222222')
    tracked_addresses = {
        'old': [old_safe],
        'new': [new_safe],
        'both': [old_safe, new_safe],
        'neither': [],
    }[tracked_safe]
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[
                BlockchainAccountData(
                    chain=SupportedBlockchain.GNOSIS,
                    address=address,
                )
                for address in tracked_addresses
            ],
        )

    response_data = {
        'migrationId': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'status': 'COMPLETED',
        'hasOldSafe': True,
        'newSafe': {'address': new_safe, 'chainId': '100', 'tokenSymbol': 'EURe'},
        'oldSafe': {
            'address': old_safe,
            'chainId': '100',
            'recordedAt': '2026-06-03T12:00:00.000Z',
        },
    }
    with patch.object(
        gnosispay.session,
        'get',
        return_value=MockResponse(HTTPStatus.OK, dumps(response_data)),
    ) as mock_get:
        result = gnosispay.get_safe_migration_data()
        assert gnosispay.get_safe_migration_data() == result

    assert mock_get.call_count == 1
    second_gnosispay = init_gnosis_pay(database)
    assert second_gnosispay is not None
    assert second_gnosispay.get_safe_migration_data() == result
    with database.conn.read_ctx() as cursor:
        cached_data = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheStatic.GNOSIS_PAY_SAFE_MIGRATION.value,),
        ).fetchone()
    assert cached_data is not None
    assert loads(cached_data[0]) == {
        'migration_id': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'old_safe': old_safe,
        'new_safe': new_safe,
    }

    if missing_type is None:
        assert result == {
            'migration_id': GNOSIS_PAY_SAFE_MIGRATION_ID,
            'untracked_addresses': [],
        }
        return

    old_is_tracked = tracked_safe == 'old'
    assert result == {
        'migration_id': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'untracked_addresses': [{
            'address': new_safe if old_is_tracked else old_safe,
            'type': missing_type,
        }],
    }


@pytest.mark.parametrize('response_data', [
    {
        'migrationId': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'status': 'COMPLETED',
        'hasOldSafe': False,
        'newSafe': {
            'address': '0x2222222222222222222222222222222222222222',
            'chainId': '100',
        },
    },
    {
        'migrationId': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'status': 'COMPLETED',
        'hasOldSafe': True,
        'newSafe': {'address': 'invalid', 'chainId': '100'},
        'oldSafe': {
            'address': '0x1111111111111111111111111111111111111111',
            'chainId': '100',
        },
    },
    {
        'migrationId': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'status': 'COMPLETED',
        'hasOldSafe': True,
        'newSafe': {
            'address': '0x2222222222222222222222222222222222222222',
            'chainId': '1',
        },
        'oldSafe': {
            'address': '0x1111111111111111111111111111111111111111',
            'chainId': '100',
        },
    },
])
def test_gnosis_pay_safe_migration_ignored_responses(
        database: 'DBHandler',
        gnosispay_credentials: None,
        response_data: dict,
) -> None:
    """Test absent old Safes, malformed addresses and unsupported chains are ignored."""
    gnosispay = init_gnosis_pay(database)
    assert gnosispay is not None
    with patch.object(
        gnosispay.session,
        'get',
        return_value=MockResponse(HTTPStatus.OK, dumps(response_data)),
    ):
        assert gnosispay.get_safe_migration_data() == {
            'migration_id': GNOSIS_PAY_SAFE_MIGRATION_ID,
            'untracked_addresses': [],
        }


def test_gnosis_pay_safe_migration_api_failure(
        database: 'DBHandler',
        gnosispay_credentials: None,
) -> None:
    """Test migration API failures do not escape into callers such as scheduled tasks."""
    gnosispay = init_gnosis_pay(database)
    assert gnosispay is not None
    with patch.object(
        gnosispay.session,
        'get',
        side_effect=requests.ConnectionError('test failure'),
    ), pytest.raises(RemoteError, match='test failure'):
        gnosispay.get_safe_migration_data()
