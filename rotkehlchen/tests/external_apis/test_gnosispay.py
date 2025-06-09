from http import HTTPStatus
from unittest.mock import patch

import pytest
from requests.models import Response

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures.messages import MockedWsMessage
from rotkehlchen.tests.utils.constants import A_GNOSIS_EURE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ExternalService, Location, TimestampMS, deserialize_evm_tx_hash
from rotkehlchen.utils.gevent_compat import Timeout, sleep


@pytest.fixture(name='gnosispay_credentials')
def _fixture_gnosispay_credentials(database):
    """Input mock monerium credentials to the DB for testing"""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            (ExternalService.GNOSIS_PAY.name.lower(), 'token', None),
        )


def mock_gnosispay_and_run_periodic_task(task_manager, contents):
    def mock_gnosispay(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, contents)

    class MockPremium:
        def is_active(self):
            return True

    timeout = 4
    task_manager.chains_aggregator.premium = MockPremium()
    task_manager.potential_tasks = [task_manager._maybe_query_gnosispay]
    with Timeout(timeout), patch('requests.Session.get', side_effect=mock_gnosispay):
        try:
            task_manager.schedule()
            sleep(.5)
        except Timeout as e:
            raise AssertionError(f'gnosispay query was not scheduled within {timeout} seconds') from e  # noqa: E501


def mock_unauthorized_requests_get(url, params=None, **kwargs):
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    response._content = b'{"message": "No authorization token was found"}'
    return response


@pytest.mark.parametrize('max_tasks_num', [1])
def test_gnosispay_periodic_task(task_manager, database, gnosispay_credentials):  # pylint: disable=unused-argument
    """foo"""
    dbevents = DBHistoryEvents(database)
    tx_hash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    gnosis_user_address = '0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da'
    timestamp = TimestampMS(1718287227000)
    amount = '25.9'
    event = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=113,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYMENT,
        asset=A_GNOSIS_EURE,
        amount=FVal(amount),
        location_label=gnosis_user_address,
        notes=f'Spend {amount} via Gnosis Pay',
        counterparty=CPT_GNOSIS_PAY,
    )
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor=write_cursor, history=[event])

    mock_gnosispay_and_run_periodic_task(
        task_manager=task_manager,
        contents="""[{
        "createdAt": "2024-06-03T16:00:27.161Z",
        "transactionAmount": "350000",
        "transactionCurrency": {
            "symbol": "RSD",
            "code": "941",
            "decimals": 2,
            "name": "Serbian dinar"
        },
        "billingAmount": "2590",
        "billingCurrency": {
            "symbol": "EUR",
            "code": "978",
            "decimals": 2,
            "name": "Euro"
        },
        "mcc": "6011",
        "merchant": {
            "name": "ATM OTP TRG N PASICA 5   ",
            "city": "BEOGRAD      ",
            "country": {
                "name": "Serbia",
                "numeric": "688",
                "alpha2": "RS",
                "alpha3": "SRB"
            }
        },
        "country": {
            "name": "Serbia",
            "numeric": "688",
            "alpha2": "RS",
            "alpha3": "SRB"
        },
        "transactions": [
            {
                "status": "ExecSuccess",
                "to": "0xfooo",
                "value": "0",
                "data": "0xfoo",
                "hash": "0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354"
            }
        ],
        "kind": "Payment",
        "status": "Approved"
        }]""",
    )
    event.notes = 'Withdraw 3500 RSD (25.9 EUR) from ATM OTP TRG N PASICA 5 in BEOGRAD :country:RS:'  # noqa: E501
    event.identifier = 1
    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[tx_hash],
            ),
            has_premium=True,
        )
    assert new_events == [event]


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
        gnosispay.get_data_for_transaction(tx_hash='', tx_timestamp=0)

    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.GNOSISPAY_SESSIONKEY_EXPIRED,
        data={'error': 'No authorization token was found'},
    )
