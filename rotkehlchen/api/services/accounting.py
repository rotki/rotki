from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, get_args

from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.unresolved_conflicts import DBRemoteConflicts
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.base import get_event_type_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.db.filtering import AccountingRulesFilterQuery, DBFilterQuery
    from rotkehlchen.rotkehlchen import Rotkehlchen


class AccountingService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def export_accounting_rules(self, directory_path: Path | None) -> dict[str, Any]:
        db_accounting = DBAccountingRules(self.rotkehlchen.data.db)
        rules_and_properties = db_accounting.get_accounting_rules_and_properties()

        if directory_path is None:
            return {'result': rules_and_properties, 'message': '', 'status_code': HTTPStatus.OK}

        directory_path.mkdir(parents=True, exist_ok=True)
        try:
            with open(
                directory_path / 'accounting_rules.json',
                mode='w',
                encoding='utf-8',
            ) as file:
                json.dump(rules_and_properties, file)
        except (PermissionError, json.JSONDecodeError) as e:
            return {
                'result': None,
                'message': f'Failed to export accounting rules due to: {e!s}',
                'status_code': HTTPStatus.BAD_REQUEST,
            }

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def import_accounting_rules(self, filepath: Path) -> dict[str, Any]:
        try:
            with open(filepath, encoding='utf-8') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                'result': None,
                'message': f'Failed to import accounting rules due to: {e!s}',
                'status_code': HTTPStatus.BAD_REQUEST,
            }
        except PermissionError as e:
            return {
                'result': None,
                'message': f'Failed to import accounting rules due to: {e!s}',
                'status_code': HTTPStatus.CONFLICT,
            }

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
            return {
                'result': None,
                'message': error_msg,
                'status_code': HTTPStatus.CONFLICT,
            }

        for rule_info in json_data['accounting_rules'].values():
            self._invalidate_cache_for_accounting_rule(
                event_ids=rule_info['event_ids'],
                event_type=HistoryEventType.deserialize(rule_info['event_type']),
                event_subtype=HistoryEventSubType.deserialize(rule_info['event_subtype']),
                counterparty=rule_info['counterparty'],
            )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def add_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: BaseEventSettings,
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> dict[str, Any]:
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
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        self._invalidate_cache_for_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def update_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: BaseEventSettings,
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            identifier: int,
    ) -> dict[str, Any]:
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
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        self._invalidate_cache_for_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_accounting_rule(self, rule_id: int) -> dict[str, Any]:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            event_ids, event_type, event_subtype, counterparty = db.remove_accounting_rule(
                rule_id=rule_id,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        self._invalidate_cache_for_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def query_accounting_rules(self, filter_query: AccountingRulesFilterQuery) -> dict[str, Any]:
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

        return {
            'result': process_result(result),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def linkable_accounting_properties(self) -> dict[str, Any]:
        possible_accounting_setting_names = get_args(LINKABLE_ACCOUNTING_SETTINGS_NAME)
        result = {
            'count_entire_amount_spend': possible_accounting_setting_names,
            'count_cost_basis_pnl': possible_accounting_setting_names,
            'taxable': possible_accounting_setting_names,
        }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def solve_multiple_accounting_rule_conflicts(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
            solve_all_using: Literal['remote', 'local'] | None,
    ) -> dict[str, Any]:
        conflict_db = DBRemoteConflicts(self.rotkehlchen.data.db)
        try:
            if solve_all_using is None:
                conflict_db.solve_accounting_rule_conflicts(conflicts=conflicts)
            else:
                conflict_db.solve_all_conflicts(solve_all_using=solve_all_using)
        except (InputError, KeyError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def list_accounting_rules_conflicts(self, filter_query: DBFilterQuery) -> dict[str, Any]:
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
        return {
            'result': process_result(result),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def _invalidate_cache_for_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            event_ids: list[int] | None = None,
    ) -> None:
        if event_ids is None:
            cache_keys = [get_event_type_identifier(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
            )]
        else:
            cache_keys = [get_event_type_identifier(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                event_id=event_id,
            ) for event_id in event_ids]

        accountant = self.rotkehlchen.accountant
        for cache_key in cache_keys:
            affected_events = accountant.processable_events_cache_signatures.get(cache_key)
            for event_idx in affected_events:
                accountant.processable_events_cache.remove(event_idx)
