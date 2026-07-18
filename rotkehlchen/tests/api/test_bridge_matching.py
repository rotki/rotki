from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _add_bridge_pair(
        rotkehlchen_api_server: APIServer,
        withdrawal_is_decoded_bridge: bool = True,
) -> tuple[EvmEvent, EvmEvent]:
    """Add an unmatched bridge deposit and a destination-leg candidate to the DB."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    user_address = make_evm_address()
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                identifier=1,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
                counterparty=CPT_ACROSS,
                notes='Bridge 1 ETH from Ethereum to Arbitrum One via Across',
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 42161,
                    'from_address': user_address,
                    'to_address': user_address,
                    'transfer_id': '12345',
                }},
            )), (withdrawal := EvmEvent(
                identifier=2,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000300000),
                location=Location.ARBITRUM_ONE,
                event_type=(
                    HistoryEventType.WITHDRAWAL
                    if withdrawal_is_decoded_bridge else HistoryEventType.RECEIVE
                ),
                event_subtype=(
                    HistoryEventSubType.BRIDGE
                    if withdrawal_is_decoded_bridge else HistoryEventSubType.NONE
                ),
                asset=A_ETH,
                amount=FVal('0.999'),
                location_label=user_address,
                counterparty=CPT_ACROSS if withdrawal_is_decoded_bridge else None,
            ))],
        )

    return deposit, withdrawal


def _get_bridge_link_rows(rotkehlchen_api_server: APIServer) -> list[tuple[int, int]]:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ).fetchall()


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_match_and_unlink_bridge_transactions(rotkehlchen_api_server: APIServer) -> None:
    """Match a deposit to a plain receive, check the rewrite and metadata, then unlink."""
    deposit, withdrawal = _add_bridge_pair(
        rotkehlchen_api_server,
        withdrawal_is_decoded_bridge=False,
    )
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        original_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        json={'bridge_event': 1, 'matched_events': [2]},
    ))
    assert _get_bridge_link_rows(rotkehlchen_api_server) == [(1, 2)]
    with rotki.data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    # the plain receive got rewritten into a proper bridge withdrawal
    matched = next(x for x in events if x.identifier == withdrawal.identifier)
    assert matched.event_type == HistoryEventType.WITHDRAWAL
    assert matched.event_subtype == HistoryEventSubType.BRIDGE
    assert isinstance(matched, EvmEvent)
    assert matched.counterparty == CPT_ACROSS
    assert matched.extra_data is not None
    assert matched.extra_data['matched_bridge'] == {
        'group_identifier': deposit.group_identifier,
        'location': Location.ETHEREUM.serialize(),
        'fee_amount': '0.001',
    }
    matched_deposit = next(x for x in events if x.identifier == deposit.identifier)
    assert matched_deposit.extra_data is not None
    assert matched_deposit.extra_data['matched_bridge'] == {
        'group_identifier': withdrawal.group_identifier,
        'location': Location.ARBITRUM_ONE.serialize(),
        'fee_amount': '0.001',
    }

    # now unlink and check full restoration
    assert_simple_ok_response(requests.delete(
        url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        json={'identifier': 1},
    ))
    assert _get_bridge_link_rows(rotkehlchen_api_server) == []
    with rotki.data.db.conn.read_ctx() as cursor:
        assert dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        ) == original_events


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_resolve_bridge_deposit_as_external(rotkehlchen_api_server: APIServer) -> None:
    """Resolving as an external payment stamps the event and ignores it; unlink restores."""
    deposit, _ = _add_bridge_pair(rotkehlchen_api_server)
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        json={'bridge_event': 1, 'matched_events': [], 'external': True},
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ).fetchall() == [(1,)]
        stamped = next(x for x in dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[1]),
        ))
        assert stamped.extra_data is not None
        assert stamped.extra_data['matched_bridge'] == {'resolution': 'external'}

    # unlinking clears the resolution and the ignore marker
    assert_simple_ok_response(requests.delete(
        url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        json={'identifier': 1},
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ).fetchone()[0] == 0
        restored = next(x for x in dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[1]),
        ))
        assert restored.extra_data == deposit.extra_data


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_unmatched_and_possible_bridge_matches(rotkehlchen_api_server: APIServer) -> None:
    deposit, withdrawal = _add_bridge_pair(rotkehlchen_api_server)
    result = assert_proper_response_with_result(
        response=requests.get(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result == [deposit.group_identifier, withdrawal.group_identifier]

    result = assert_proper_response_with_result(
        response=requests.post(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
            json={
                'bridge_event': deposit.group_identifier,
                'time_range': 3600,
                'tolerance': '0.01',
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result['close_matches'] == [withdrawal.identifier]

    # after matching, nothing is unmatched anymore
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        json={'bridge_event': 1, 'matched_events': [2]},
    ))
    result = assert_proper_response_with_result(
        response=requests.get(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result == []


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_match_bridge_transactions_errors(rotkehlchen_api_server: APIServer) -> None:
    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
            json={'bridge_event': 1, 'matched_events': [2], 'external': True},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='external cannot be combined with matched_events',
    )
    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
            json={'bridge_event': 1, 'matched_events': [2]},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='No bridge event found in the DB for identifier 1',
    )
    assert_error_response(
        response=requests.delete(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
            json={'identifier': 42},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='does not correspond to either side',
    )


def test_match_bridge_transactions_requires_premium(rotkehlchen_api_server: APIServer) -> None:
    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchbridgetransactionsresource'),
            json={'bridge_event': 1, 'matched_events': [2]},
        ),
        status_code=HTTPStatus.FORBIDDEN,
        contained_in_msg='does not have a premium subscription',
    )
