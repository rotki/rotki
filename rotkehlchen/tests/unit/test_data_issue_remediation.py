from typing import TYPE_CHECKING

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import RemediationPipeline
from rotkehlchen.history.data_issues.remediation.owned_account import (
    OwnedAccountCounterpartyStrategy,
)
from rotkehlchen.history.data_issues.types import (
    CurrentBalanceMismatchIssuePayload,
    DataIssuePayload,
    NegativeBalanceIssuePayload,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
    TimestampMS,
    TuplesOfBlockchainAddresses,
)

pytestmark = pytest.mark.accounting_update

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.data_issues.types import DataIssue
    from rotkehlchen.user_messages import MessagesAggregator


class MockChainsAggregator:
    def __init__(
            self,
            active_addresses: dict[SupportedBlockchain, TuplesOfBlockchainAddresses],
    ) -> None:
        self.active_addresses = active_addresses

    def get_active_addresses(
            self,
            blockchain: SupportedBlockchain,
    ) -> TuplesOfBlockchainAddresses:
        return self.active_addresses.get(blockchain, ())


def _add_evm_spend_event(
        database: 'DBHandler',
        address: ChecksumEvmAddress | None = TEST_ADDR2,
        event_type: HistoryEventType = HistoryEventType.SPEND,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
) -> int:
    with database.user_write() as write_cursor:
        event_identifier = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=A_ETH,
                amount=ONE,
                location_label=TEST_ADDR1,
                address=address,
            ),
        )
    assert event_identifier is not None
    return event_identifier


def _write_issue(
        database: 'DBHandler',
        event_identifier: int,
        kind: IssueKind = IssueKind.NEGATIVE_BALANCE,
        location: Location = Location.ETHEREUM,
) -> 'DataIssue':
    manager = DataIssuesManager(database)
    payload: DataIssuePayload
    if kind == IssueKind.NEGATIVE_BALANCE:
        payload = NegativeBalanceIssuePayload(
            event_identifier=event_identifier,
            in_memory_negative_amount='-1',
            derived_balance_before_event='0',
        )
    else:
        payload = CurrentBalanceMismatchIssuePayload(
            derived_balance='1',
            observed_balance='2',
            delta='1',
            queried_at_ts=1000,
            latest_event_identifier=event_identifier,
        )
    issue_id = manager.write_issue(
        kind=kind,
        location=location.serialize_for_db(),
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload=payload,
        ts_start=1000,
        ts_end=1000,
    )
    return manager.get_issue(issue_id)


def _strategy(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        active_addresses: dict[SupportedBlockchain, TuplesOfBlockchainAddresses],
) -> OwnedAccountCounterpartyStrategy:
    return OwnedAccountCounterpartyStrategy(
        database=database,
        chains_aggregator=MockChainsAggregator(active_addresses),
        msg_aggregator=msg_aggregator,
    )


def test_owned_account_counterparty_strategy_resolves(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
) -> None:
    event_id = _add_evm_spend_event(database)
    issue = _write_issue(database, event_id)
    issue.payload['event_identifier'] = str(event_id)
    manager = DataIssuesManager(database)

    RemediationPipeline(
        manager=manager,
        strategies=(_strategy(
            database=database,
            msg_aggregator=msg_aggregator,
            active_addresses={SupportedBlockchain.ETHEREUM: (TEST_ADDR2,)},
        ),),
    ).run(issue)

    resolved_issue = manager.get_issue(issue.id)
    assert resolved_issue.state == IssueState.RESOLVED
    assert (
        resolved_issue.payload['resolution']['attribution'] ==
        'reclassified_as_internal_transfer'
    )
    assert resolved_issue.auto_remediation_attempts[0]['resolved'] is True
    with database.conn.read_ctx() as cursor:
        event = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[event_id]),
        )[0]
    assert event.event_type == HistoryEventType.TRANSACTION_TO_SELF
    assert event.event_subtype == HistoryEventSubType.NONE


def test_owned_account_counterparty_strategy_skips_different_chain(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
) -> None:
    strategy = _strategy(
        database=database,
        msg_aggregator=msg_aggregator,
        active_addresses={SupportedBlockchain.OPTIMISM: (TEST_ADDR2,)},
    )

    outcome = strategy.attempt(_write_issue(database, _add_evm_spend_event(database)))

    assert outcome.resolved is False
    assert outcome.attribution == 'counterparty_not_owned'


def test_owned_account_counterparty_strategy_skips_unknown_counterparty(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
) -> None:
    issue = _write_issue(database, _add_evm_spend_event(database, address=None))

    assert _strategy(
        database=database,
        msg_aggregator=msg_aggregator,
        active_addresses={SupportedBlockchain.ETHEREUM: (TEST_ADDR2,)},
    ).applies_to(issue) is False


def test_owned_account_counterparty_strategy_skips_current_balance_mismatch(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
) -> None:
    issue = _write_issue(
        database=database,
        event_identifier=_add_evm_spend_event(database),
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
    )

    assert _strategy(
        database=database,
        msg_aggregator=msg_aggregator,
        active_addresses={SupportedBlockchain.ETHEREUM: (TEST_ADDR2,)},
    ).applies_to(issue) is False


def test_owned_account_counterparty_strategy_skips_internal_transfer(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
) -> None:
    issue = _write_issue(database, _add_evm_spend_event(
        database=database,
        event_type=HistoryEventType.TRANSACTION_TO_SELF,
    ))

    assert _strategy(
        database=database,
        msg_aggregator=msg_aggregator,
        active_addresses={SupportedBlockchain.ETHEREUM: (TEST_ADDR2,)},
    ).applies_to(issue) is False
