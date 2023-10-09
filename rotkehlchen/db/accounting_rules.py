from typing import TYPE_CHECKING, Any, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.errors.misc import InputError

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBAccountingRules:

    def __init__(self, db_handler: 'DBHandler') -> None:
        self.db = db_handler

    @classmethod
    def _rule_for_string(
            cls,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: Optional[str],
    ) -> str:
        return f'Rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty})'

    def add_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: Optional[str],
            rule: 'BaseEventSettings',
    ) -> None:
        """
        Add a single accounting rule to the database.
        May raise:
        - InputError: If the combination of type, subtype and counterparty already exists.
        """
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    'INSERT INTO accounting_rules(type, subtype, counterparty, taxable, '
                    'count_entire_amount_spend, count_cost_basis_pnl, method, '
                    'accounting_treatment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (

                        event_type.serialize(),
                        event_subtype.serialize(),
                        counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY,
                        *rule.serialize_for_db(),
                    ),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'{self._rule_for_string(event_type=event_type, event_subtype=event_subtype, counterparty=counterparty)} already exists',  # noqa: E501
                ) from e

    def remove_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: Optional[str],
    ) -> None:
        """
        Delete an accounting rule by (type, subtype, counterparty).
        May raise:
        - InputError if the rule doesn't exist
        """
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM accounting_rules WHERE type=? AND subtype=? AND counterparty IS ?',
                (
                    event_type.serialize(),
                    event_subtype.serialize(),
                    counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY,
                ),
            )
            if write_cursor.rowcount != 1:
                # we know that at max there is one due to the primary key in the table
                raise InputError(
                    f'{self._rule_for_string(event_type=event_type, event_subtype=event_subtype, counterparty=counterparty)}'  # noqa: E501
                    ' does not exist',
                )

    def update_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: Optional[str],
            rule: 'BaseEventSettings',
            identifier: int,
    ) -> None:
        """
        Edit accounting rule properties (type, subtype, counterparty) for the rule with the
        provided identifier
        May raise:
        - InputError: if no event gets updated
        """
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'UPDATE accounting_rules SET type=?, subtype=?, counterparty=?, taxable=?, '
                'count_entire_amount_spend=?, count_cost_basis_pnl=?, method=?, '
                'accounting_treatment=? WHERE identifier=?',
                (
                    event_type.serialize(),
                    event_subtype.serialize(),
                    counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY,
                    *rule.serialize_for_db(),
                    identifier,
                ),
            )
            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Tried to update accounting {self._rule_for_string(event_type=event_type, event_subtype=event_subtype, counterparty=counterparty)}'  # noqa: E501
                    ' but it was not found',
                )

    def query_rules(
            self,
            filter_query: AccountingRulesFilterQuery,
    ) -> tuple[
        list[tuple[tuple[int, HistoryEventType, HistoryEventSubType, Optional[str]], BaseEventSettings]],  # noqa: E501
        int,
    ]:
        """
        Query rules in the database using the provided filter. It returns the list of rules and
        the total amount of rules matching the filter without pagination.
        """
        query = 'SELECT * FROM accounting_rules '
        filter_query_str, bindings = filter_query.prepare()
        rules = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query + filter_query_str, bindings)
            rules = [
                (entry[:4], BaseEventSettings.deserialize_from_db(entry[4:]))
                for entry in cursor
            ]
            query, bindings = filter_query.prepare(with_pagination=False)
            query = 'SELECT COUNT(*) from accounting_rules ' + query
            total_found_result = cursor.execute(query, bindings).fetchone()[0]
        return rules, total_found_result

    def query_rules_and_serialize(
            self,
            filter_query: AccountingRulesFilterQuery,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query rules in the database using the provided filter. It returns the list of rules
        serialized and the total amount of rules matching the filter without pagination.
        """
        rules_raw, total_found_result = self.query_rules(filter_query=filter_query)
        entries = []
        for entry in rules_raw:
            # serialize the rule and add information about the key to what it applies
            data = entry[1].serialize()
            data['identifier'] = entry[0][0]
            data['event_type'] = entry[0][1]
            data['event_subtype'] = entry[0][2]
            data['counterparty'] = entry[0][3] if entry[0][3] != NO_ACCOUNTING_COUNTERPARTY else None  # noqa: E501
            entries.append(data)
        return entries, total_found_result
