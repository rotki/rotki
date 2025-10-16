from http import HTTPStatus

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
]])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
]])
def test_basic_calendar_operations(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    crv_event = (2, 'CRV unlock', 'Unlock date for CRV', CPT_CURVE, ethereum_accounts[1], 1851422011)  # noqa: E501

    # save 2 entries in the db
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'counterparty': CPT_ENS,
            'address': ethereum_accounts[0],
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
            'color': 'ffffff',
            'auto_delete': False,
        },
    )

    data = assert_proper_sync_response_with_result(response)
    assert data['entry_id'] == 1

    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'name': crv_event[1],
            'description': crv_event[2],
            'counterparty': crv_event[3],
            'address': crv_event[4],
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
            'timestamp': crv_event[5],
            'auto_delete': False,
        },
    )
    data = assert_proper_sync_response_with_result(response)
    assert data['entry_id'] == 2

    with database.conn.read_ctx() as cursor:
        db_rows = cursor.execute(
            'SELECT identifier, name, description, counterparty, address, timestamp, '
            'color FROM calendar',
        ).fetchall()
        assert db_rows == [
            (1, 'ENS renewal', 'Renew yabir.eth', CPT_ENS, ethereum_accounts[0], 1869737344, 'ffffff'),  # noqa: E501
            crv_event + (None,),
        ]

    # update the ens entry
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'identifier': 1,
            'timestamp': 1977652411,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth extended',
            'counterparty': CPT_ENS,
            'address': ethereum_accounts[0],
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
            'color': '3a70a6',
            'auto_delete': True,
        },
    )
    with database.conn.read_ctx() as cursor:
        db_rows = cursor.execute(
            'SELECT identifier, name, description, counterparty, address, timestamp FROM calendar',
        ).fetchall()
        assert db_rows == [
            (1, 'ENS renewal', 'Renew yabir.eth extended', CPT_ENS, ethereum_accounts[0], 1977652411),  # noqa: E501
            crv_event,
        ]

    # query calendar events
    ens_json_event = {
        'identifier': 1,
        'name': 'ENS renewal',
        'description':
        'Renew yabir.eth extended',
        'counterparty': CPT_ENS,
        'timestamp': 1977652411,
        'address': ethereum_accounts[0],
        'blockchain': 'eth',
        'color': '3a70a6',
        'auto_delete': True,
    }
    curve_json_event = {
        'identifier': 2,
        'name': 'CRV unlock',
        'description': 'Unlock date for CRV',
        'counterparty': CPT_CURVE,
        'timestamp': 1851422011,
        'address': ethereum_accounts[1],
        'blockchain': 'eth',
        'auto_delete': False,
    }
    future_ts = {'to_timestamp': 3479391239}  # timestamp enough in the future to return all the events  # noqa: E501
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json=future_ts,
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [ens_json_event, curve_json_event],
        'entries_found': 2,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # query with filter on timestamp
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'from_timestamp': 1977652400, 'to_timestamp': 1977652511},
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [ens_json_event],
        'entries_found': 1,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # query with addresses
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'accounts': [{'address': ethereum_accounts[0], 'blockchain': 'eth'}],
        } | future_ts,
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [ens_json_event],
        'entries_found': 1,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # query with counterparty
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'counterparty': CPT_CURVE} | future_ts,
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [curve_json_event],
        'entries_found': 1,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # query with exact name match
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'name': 'ENS renewal'} | future_ts,
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [ens_json_event],
        'entries_found': 1,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # query with exact name match (should find CRV unlock)
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'name': 'CRV unlock'} | future_ts,
    )
    assert assert_proper_sync_response_with_result(response) == {
        'entries': [curve_json_event],
        'entries_found': 1,
        'entries_total': 2,
        'entries_limit': -1,
    }

    # delete the ens entry. The crv entry should be kept
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'identifier': 1},
    )
    assert_proper_response(response)
    with database.conn.read_ctx() as cursor:
        db_rows = cursor.execute(
            'SELECT identifier, name, description, counterparty, '
            'address, timestamp FROM calendar',
        ).fetchall()
        assert db_rows == [crv_event]

    # add an event to gnosis and filter only by address and not chain
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'name': 'gnosis event',
            'description': crv_event[2],
            'counterparty': crv_event[3],
            'address': crv_event[4],
            'blockchain': SupportedBlockchain.GNOSIS.serialize(),
            'timestamp': crv_event[5],
            'auto_delete': False,
        },
    )
    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={'accounts': [{'address': crv_event[4]}]} | future_ts,
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    assert result[0]['blockchain'] == SupportedBlockchain.ETHEREUM.serialize()
    assert result[1]['blockchain'] == SupportedBlockchain.GNOSIS.serialize()

    # Test query with None to_timestamp (should not cause TypeError)
    assert_proper_response(requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'from_timestamp': 1760652000,
            'limit': 5,
            'offset': 0,
            'ascending': [True],
            'order_by_attributes': ['timestamp'],
        },
    ))

    # Test validation still works when to_timestamp is provided and invalid
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'from_timestamp': 1977652500,  # after the ens event timestamp
            'to_timestamp': 1977652300,    # before the ens event timestamp
            'limit': 5,
            'offset': 0,
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='from_timestamp must be less than or equal to to_timestamp',
    )


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('zksync_lite_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_validation_calendar(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    # test creating event without address
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'counterparty': CPT_ENS,
            'auto_delete': False,
        },
    )
    assert_proper_response(response)
    with database.conn.read_ctx() as cursor:
        assert database.get_entries_count(cursor=cursor, entries_table='calendar') == 1

    # test creating event without a valid counterparty
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'counterparty': 'BAD COUNTERPARTY',
            'auto_delete': False,
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Unknown counterparty',
    )

    # test providing only address
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'address': ethereum_accounts[0],
            'auto_delete': False,
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='If any of address or blockchain is provided both need to be provided',
    )

    # provide invalid bitcoin address
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'address': ethereum_accounts[0],
            'blockchain': SupportedBlockchain.BITCOIN.serialize(),
            'auto_delete': False,
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='is not a bitcoin address',
    )

    # create duplicate entry
    duplicated_entry_body = {
        'timestamp': 1869737344,
        'name': 'ENS renewal',
        'description': 'Renew yabir.eth',
        'counterparty': CPT_ENS,
        'address': ethereum_accounts[0],
        'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
        'auto_delete': False,
    }
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json=duplicated_entry_body,
    )
    assert_proper_response(response)

    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json=duplicated_entry_body,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Could not add the calendar entry because an event with the same name',
    )

    # test missing counterparty
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1969737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'auto_delete': False,
        },
    )
    assert_proper_response(response)

    # test creating a valid zksync event
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'Withdraw funds',
            'description': 'Withdraw stolen funds. Prescribed',
            'address': ethereum_accounts[0],
            'blockchain': SupportedBlockchain.ZKSYNC_LITE.serialize(),
            'color': 'ffffff',
            'auto_delete': True,
        },
    )
    assert_proper_response(response)


@pytest.mark.parametrize('have_decoders', [True])
def test_reminder_operations(rotkehlchen_api_server: APIServer) -> None:
    # save 2 entries in the db
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarresource'),
        json={
            'timestamp': 1869737344,
            'name': 'ENS renewal',
            'description': 'Renew yabir.eth',
            'counterparty': CPT_ENS,
            'color': 'ffffff',
            'auto_delete': False,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    calendar_id = result['entry_id']
    assert calendar_id == 1

    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={'reminders': [{
            'event_id': calendar_id,
            'secs_before': DAY_IN_SECONDS * 3,
            'acknowledged': False,
        }, {
            'event_id': 100,  # must fail
            'secs_before': DAY_IN_SECONDS * 3,
            'acknowledged': False,
        }]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['success'] == [calendar_id]
    assert result['failed'] == [100]

    # query by event id
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={'identifier': calendar_id},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {
        'entries': [{
            'identifier': 1,
            'event_id': 1,
            'secs_before': DAY_IN_SECONDS * 3,
            'acknowledged': False,
        }],
    }

    # update by reminder id
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={
            'identifier': 1,
            'event_id': 1,
            'secs_before': DAY_IN_SECONDS,
        },
    )
    assert_proper_response(response)
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={'identifier': calendar_id},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {
        'entries': [{
            'identifier': 1,
            'event_id': 1,
            'secs_before': DAY_IN_SECONDS,
            'acknowledged': False,
        }],
    }

    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={'identifier': 1},
    )
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'calendarremindersresource'),
        json={'identifier': calendar_id},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': []}
