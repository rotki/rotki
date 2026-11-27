"""Accounting rule lookup shared by cost basis processing and realized PnL reads."""
from typing import TYPE_CHECKING

from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType


class CostBasisRules:
    """The accounting rules of the user, as the PnL report resolves them for an event."""

    def __init__(self, database: DBHandler, cursor: DBCursor | None = None) -> None:
        self._by_event: dict[int, BaseEventSettings] = {}
        self._by_type: dict[
            tuple[HistoryEventType, HistoryEventSubType, str | None],
            BaseEventSettings,
        ] = {}
        for rule_info in DBAccountingRules(database).query_rules(
            filter_query=AccountingRulesFilterQuery.make(),
            cursor=cursor,
        )[0]:
            if not rule_info.is_event_specific:
                self._by_type[rule_info.event_key] = rule_info.rule
            elif rule_info.event_ids is not None:
                self._by_event.update(dict.fromkeys(rule_info.event_ids, rule_info.rule))

    def get(self, event: HistoryBaseEntry) -> BaseEventSettings | None:
        """The rule of the event itself, else of its type and counterparty, else of its type."""
        return self.get_for_fields(
            event_identifier=event.identifier,
            event_type=event.event_type,
            event_subtype=event.event_subtype,
            counterparty=event.counterparty if isinstance(event, OnchainEvent) else None,
        )

    def get_for_fields(
            self,
            event_identifier: int | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None = None,
    ) -> BaseEventSettings | None:
        """Resolve the rule directly from DB columns without deserializing an event."""
        if event_identifier is not None and (rule := self._by_event.get(event_identifier)) is not None:  # noqa: E501
            return rule

        if counterparty is not None and (
            rule := self._by_type.get((event_type, event_subtype, counterparty))
        ) is not None:
            return rule

        return self._by_type.get((event_type, event_subtype, None))
