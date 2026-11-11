from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, get_args

from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.unresolved_conflicts import DBRemoteConflicts
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import InputError, RemoteError

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.db.filtering import AccountingRulesFilterQuery, DBFilterQuery
    from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
    from rotkehlchen.rotkehlchen import Rotkehlchen


class AccountingService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def export_accounting_rules(self, directory_path: Path | None) -> ApiResult:
        db_accounting = DBAccountingRules(self.rotkehlchen.data.db)
        rules_and_properties = db_accounting.get_accounting_rules_and_properties()

        if directory_path is None:
            return OkResult(rules_and_properties)

        directory_path.mkdir(parents=True, exist_ok=True)
        try:
            with open(
                directory_path / 'accounting_rules.json',
                mode='w',
                encoding='utf-8',
            ) as file:
                json.dump(rules_and_properties, file)
        except (PermissionError, json.JSONDecodeError) as e:
            return FailResult(
                f'Failed to export accounting rules due to: {e!s}',
                HTTPStatus.BAD_REQUEST,
                FailureCause.LOCAL_DB,
            )

        return OkResult(True)

    def reset_accounting_rules(self) -> ApiResult:
        """Reset all accounting rules to rotki's current defaults, pulling them from the data
        repo. Destructive: removes all user customizations, event-specific rules and unresolved
        accounting rule conflicts. The user's rules are left untouched if the repo is unreachable.
        """
        try:
            self.rotkehlchen.data_updater.reset_accounting_rules()
        except RemoteError as e:
            return FailResult(
                f'Failed to reset accounting rules due to: {e!s}',
                HTTPStatus.BAD_GATEWAY,
                e.cause,
            )

        return OkResult(True)

    def import_accounting_rules(self, filepath: Path) -> ApiResult:
        try:
            with open(filepath, encoding='utf-8') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            return FailResult(
                f'Failed to import accounting rules due to: {e!s}',
                HTTPStatus.BAD_REQUEST,
                FailureCause.INVALID_INPUT,
            )
        except PermissionError as e:
            return FailResult(
                f'Failed to import accounting rules due to: {e!s}',
                HTTPStatus.CONFLICT,
                FailureCause.LOCAL_DB,
            )

        db_accounting_rules = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            success, error_msg = db_accounting_rules.import_accounting_rules(
                accounting_rules=json_data['accounting_rules'],
                linked_properties=json_data['linked_properties'],
            )
        except KeyError as e:
            success = False
            error_msg = f'Key {e!s} not found in the accounting rules json file'

        if success is False:
            return FailResult(error_msg, HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        self.rotkehlchen.accountant.clear_processable_events_cache()

        return OkResult(True)

    def add_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: BaseEventSettings,
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> ApiResult:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.add_accounting_rule(
                event_ids=event_ids,
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        self.rotkehlchen.accountant.clear_processable_events_cache()
        return OkResult(True)

    def update_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: BaseEventSettings,
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            identifier: int,
    ) -> ApiResult:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.update_accounting_rule(
                event_ids=event_ids,
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
                identifier=identifier,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        self.rotkehlchen.accountant.clear_processable_events_cache()
        return OkResult(True)

    def delete_accounting_rule(self, rule_id: int) -> ApiResult:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.remove_accounting_rule(rule_id=rule_id)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        self.rotkehlchen.accountant.clear_processable_events_cache()
        return OkResult(True)

    def query_accounting_rules(self, filter_query: AccountingRulesFilterQuery) -> ApiResult:
        db = self.rotkehlchen.data.db
        entries, total_filter_count = DBAccountingRules(db).query_rules_and_serialize(
            filter_query=filter_query,
        )
        with db.conn.read_ctx() as cursor:
            result = {
                'entries': entries,
                'entries_found': total_filter_count,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(
                    cursor=cursor,
                    entries_table='accounting_rules',
                ),
                'entries_limit': -1,
            }

        return OkResult(result)

    def linkable_accounting_properties(self) -> ApiResult:
        possible_accounting_setting_names = get_args(LINKABLE_ACCOUNTING_SETTINGS_NAME)
        result = {
            'count_entire_amount_spend': possible_accounting_setting_names,
            'count_cost_basis_pnl': possible_accounting_setting_names,
            'taxable': possible_accounting_setting_names,
        }
        return OkResult(result)

    def solve_multiple_accounting_rule_conflicts(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
            solve_all_using: Literal['remote', 'local'] | None,
    ) -> ApiResult:
        conflict_db = DBRemoteConflicts(self.rotkehlchen.data.db)
        try:
            if solve_all_using is None:
                conflict_db.solve_accounting_rule_conflicts(conflicts=conflicts)
            else:
                conflict_db.solve_all_conflicts(solve_all_using=solve_all_using)
        except (InputError, KeyError) as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        finally:  # earlier conflicts may already be committed when a later one fails
            self.rotkehlchen.accountant.clear_processable_events_cache()

        return OkResult(True)

    def list_accounting_rules_conflicts(self, filter_query: DBFilterQuery) -> ApiResult:
        conflict_db = DBRemoteConflicts(self.rotkehlchen.data.db)
        conflicts = conflict_db.list_accounting_conflicts(filter_query=filter_query)
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            total_entries = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='unresolved_remote_conflicts',
            )
        result = {
            'entries': conflicts,
            'entries_found': total_entries,
            'entries_total': total_entries,
            'entries_limit': -1,
        }
        return OkResult(result)
