import json
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.filtering import DBFilterQuery
from rotkehlchen.errors.misc import InputError

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ConflictType(Enum):
    ACCOUNTING_RULE = auto()


def _serialize_accounting_dict_to_rule(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Transform remote data to a common format respecting what we return in the
    accounting rules endpoint
    """
    rule = BaseEventSettings(
        taxable=bool(raw_data['taxable']),
        count_entire_amount_spend=bool(raw_data['count_entire_amount_spend']),
        count_cost_basis_pnl=bool(raw_data['count_cost_basis_pnl']),
        accounting_treatment=TxAccountingTreatment.deserialize(raw_data['accounting_treatment']) if raw_data['accounting_treatment'] else None,  # noqa: E501
    )
    output = rule.serialize()
    output['event_type'] = HistoryEventType.deserialize(raw_data['event_type'])
    output['event_subtype'] = HistoryEventSubType.deserialize(raw_data['event_subtype'])
    output['counterparty'] = raw_data['counterparty']
    for linked_property, setting_name in raw_data.get('links', {}).items():
        output[linked_property]['linked_setting'] = setting_name

    return output


def build_rule_from_remote_data(remote_data: dict[str, Any]) -> BaseEventSettings:
    """build the event setting rule for accounting rules from the remote data dict"""
    return BaseEventSettings(
        taxable=remote_data['taxable'],
        count_entire_amount_spend=remote_data['count_entire_amount_spend'],
        count_cost_basis_pnl=remote_data['count_cost_basis_pnl'],
        accounting_treatment=TxAccountingTreatment.deserialize(remote_data['accounting_treatment']) if remote_data['accounting_treatment'] else None,  # noqa: E501
    )


class DBRemoteConflicts:
    """
    Resolve conflicts for information that the user might have already and we also
    publish remotely. At the moment this call list/saves/solves accounting rules
    conflicts.
    """

    def __init__(self, db_handler: 'DBHandler') -> None:
        self.db = db_handler

    def save_conflicts(self, conflicts: list[tuple[int, str, int]]) -> None:
        with self.db.user_write() as write_cursor:
            write_cursor.executemany(
                'INSERT INTO unresolved_remote_conflicts(local_id, remote_data, type) VALUES(?, ?, ?)',  # noqa: E501
                conflicts,
            )

    def list_accounting_conflicts(self, filter_query: DBFilterQuery) -> dict[str, Any]:
        """
        Retrieve the accounting rules conflicts paginated. May raise:
        - DeserializationError
        - json.JSONDecodeError
        - IndexError
        """
        base_query = (
            'SELECT accounting_rules.identifier, accounting_rules.type, subtype, counterparty, '
            'taxable, count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment, '
            'remote_data FROM unresolved_remote_conflicts JOIN accounting_rules ON '
            'unresolved_remote_conflicts.local_id=accounting_rules.identifier '
        )
        filter_str, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(base_query + filter_str, bindings)
            id_to_data = {}
            for entry in cursor:
                local_data = {
                    'event_type': entry[1],
                    'event_subtype': entry[2],
                    'counterparty': entry[3],
                    'taxable': entry[4],
                    'count_entire_amount_spend': entry[5],
                    'count_cost_basis_pnl': entry[6],
                    'accounting_treatment': entry[7],
                }
                id_to_data[entry[0]] = {
                    'local_data': local_data,
                    'remote_data': json.loads(entry[8]),
                }

            # also query the linked rules information
            cursor.execute(
                'SELECT accounting_rule, property_name, setting_name FROM '
                f'linked_rules_properties WHERE accounting_rule IN ({",".join("?" * len(id_to_data))})',  # noqa: E501
                list(id_to_data.keys()),
            )
            for entry in cursor:
                local_data = id_to_data[entry[0]]['local_data']
                if 'links' not in local_data:
                    local_data['links'] = {}
                local_data['links'][entry[1]] = entry[2]

        # transform data from dict to serialized rules
        for conflicts_cases in id_to_data.values():
            conflicts_cases['local_data'] = _serialize_accounting_dict_to_rule(conflicts_cases['local_data'])  # noqa: E501
            conflicts_cases['remote_data'] = _serialize_accounting_dict_to_rule(conflicts_cases['remote_data'])  # noqa: E501

        return id_to_data

    def solve_accounting_rule_conflicts(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
    ) -> None:
        """
        Solve multiple conflicts for accounting rules
        It may raise:
        - InputError: if a conflict couldn't be found
        - KeyError: if the remote data doesn't have the expected format
        """
        use_remote_updates, use_local_updates = {}, []
        # extract ids that will keep local version of rules and remote information for
        # remote resolution rules.
        with self.db.conn.read_ctx() as cursor:
            for local_id, solve_using in conflicts:
                if solve_using == 'local':
                    use_local_updates.append(local_id)
                else:
                    cursor.execute(
                        'SELECT remote_data FROM unresolved_remote_conflicts WHERE '
                        'type=? AND local_id=?',
                        (ConflictType.ACCOUNTING_RULE.value, local_id),
                    )
                    if (raw_remote_data := cursor.fetchone()) is None:
                        raise InputError(f'Conflict not found for local id {local_id}')
                    use_remote_updates[local_id] = json.loads(raw_remote_data[0])

        accounting_db = DBAccountingRules(self.db)
        for local_id, remote_data in use_remote_updates.items():
            accounting_db.update_accounting_rule(
                event_type=HistoryEventType.deserialize(remote_data['event_type']),
                event_subtype=HistoryEventSubType.deserialize(remote_data['event_subtype']),
                counterparty=remote_data['counterparty'],
                rule=build_rule_from_remote_data(remote_data),
                links=remote_data.get('links', {}),
                identifier=local_id,
            )

        # delete the conflicts for the rules that have been updated
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'DELETE FROM unresolved_remote_conflicts WHERE type=? AND local_id=?',
                [(ConflictType.ACCOUNTING_RULE.value, local_id) for local_id in use_remote_updates] +  # noqa: E501
                [(ConflictType.ACCOUNTING_RULE.value, local_id) for local_id in use_local_updates],
            )

    def solve_all_conflicts(self, solve_all_using: Literal['remote', 'local']) -> None:
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT local_id FROM unresolved_remote_conflicts WHERE type=?',
                (ConflictType.ACCOUNTING_RULE.value,),
            )
            self.solve_accounting_rule_conflicts(
                conflicts=[(row[0], solve_all_using) for row in cursor],
            )
