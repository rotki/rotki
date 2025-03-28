from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.constants import EVENT_CATEGORY_MAPPINGS
from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.chain.evm.decoding.eas.constants import CPT_EAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.base import (
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.tests.utils.factories import (
    make_ethereum_transaction,
    make_evm_address,
)
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def test_serialize_with_invalid_type_subtype():
    """Test that serialize an event with invalid type/subtype does not raise exception"""
    event_type = HistoryEventType.TRANSFER
    event_subtype = HistoryEventSubType.SPEND
    assert event_subtype not in EVENT_CATEGORY_MAPPINGS[event_type]
    event = HistoryEvent(
        event_identifier='1',
        sequence_index=1,
        timestamp=TimestampMS(1),
        location=Location.KRAKEN,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
    )
    event.event_subtype = event_subtype  # do here cause ctor will raise for invalid subtype
    assert event.serialize_for_api(
        customized_event_ids=[],
        ignored_ids_mapping={},
        hidden_event_ids=[],
        event_accounting_rule_status=EventAccountingRuleStatus.NOT_PROCESSED,  # needed to recreate the error this tests for  # noqa: E501
        grouped_events_num=None,
    ) == {
        'entry': {
            'asset': 'ETH',
            'amount': '1',
            'entry_type': 'history event',
            'event_identifier': '1',
            'event_subtype': 'spend',
            'event_type': 'transfer',
            'extra_data': None,
            'identifier': None,
            'location': 'kraken',
            'location_label': None,
            'sequence_index': 1,
            'timestamp': 1,
        },
        'event_accounting_rule_status': 'not processed',
    }


@pytest.mark.parametrize('base_accounts', [[make_evm_address()]])
def test_informational_events(database: 'DBHandler', base_accounts: list[ChecksumEvmAddress]):
    """Test that informational events don't trigger price queries"""
    dbevents = DBHistoryEvents(database)
    tx = make_ethereum_transaction()
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [tx], relevant_address=base_accounts[0])

    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, [
            EvmEvent(
                tx_hash=tx.tx_hash,
                sequence_index=174,
                timestamp=TimestampMS(0),
                location=Location.BASE,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                asset=A_ETH,
                amount=ONE,
                location_label=base_accounts[0],
                notes='HOP-LP-ETH spending approval of by 0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d',  # noqa: E501
                address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
            ), EvmEvent(
                tx_hash=tx.tx_hash,
                sequence_index=10,
                timestamp=TimestampMS(0),
                location=Location.BASE,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.ATTEST,
                asset=A_ETH,
                amount=ONE,
                location_label=base_accounts[0],
                notes='Attest to https://optimism.easscan.org/attestation/view/0x3045bf8797f8e528219d48b23d28b661be5be17d13c28f61f4f6cced1b349c65',
                counterparty=CPT_EAS,
                address=string_to_evm_address('0x4200000000000000000000000000000000000021'),
            ),
        ])
