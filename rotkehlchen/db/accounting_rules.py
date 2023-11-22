import logging
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.eth2 import EthStakingEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import (
    BaseEventSettings,
    EventsAccountantCallback,
    TxAccountingTreatment,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.filtering import AccountingRulesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DEFAULT_INCLUDE_CRYPTO2CRYPTO, DEFAULT_INCLUDE_GAS_COSTS
from rotkehlchen.errors.misc import InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RuleInformation(NamedTuple):
    """
    Represent a rule that matches a tuple (event_type, event_subtype, counterparty)
    to the accounting rule that should be considered.

    links contains the properties in rule that have been linked to an accounting setting.
    """
    identifier: int
    event_key: tuple[HistoryEventType, HistoryEventSubType, Union[str, None]]
    rule: BaseEventSettings
    links: dict[str, str]


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
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> int:
        """
        Add a single accounting rule to the database. It returns the identifier
        of the created rule.
        May raise:
        - InputError: If the combination of type, subtype and counterparty already exists.
        """
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    'INSERT INTO accounting_rules(type, subtype, counterparty, taxable, '
                    'count_entire_amount_spend, count_cost_basis_pnl, '
                    'accounting_treatment) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING identifier',
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

            inserted_rule_id = write_cursor.fetchone()[0]
            for property_name, setting_name in links.items():
                self.add_linked_setting(
                    write_cursor=write_cursor,
                    rule_identifier=inserted_rule_id,
                    rule_property=property_name,
                    setting_name=setting_name,
                )

            return inserted_rule_id

    def remove_accounting_rule(self, rule_id: int) -> None:
        """
        Delete an accounting using its identifier
        May raise:
        - InputError if the rule doesn't exist
        """
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM linked_rules_properties WHERE accounting_rule=?',
                (rule_id,))
            write_cursor.execute(
                'DELETE FROM unresolved_remote_conflicts WHERE local_id=?',
                (rule_id,),
            )
            write_cursor.execute(
                'DELETE FROM accounting_rules WHERE identifier=?',
                (rule_id,),
            )
            if write_cursor.rowcount != 1:
                # we know that at max there is one due to the primary key in the table
                raise InputError(f'Rule with id {rule_id} does not exist')

    def update_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: Optional[str],
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            identifier: int,
    ) -> None:
        """
        Edit accounting rule properties (type, subtype, counterparty) for the rule with the
        provided identifier
        May raise:
        - InputError: if no event gets updated
        """
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE accounting_rules SET type=?, subtype=?, counterparty=?, taxable=?, '
                    'count_entire_amount_spend=?, count_cost_basis_pnl=?, '
                    'accounting_treatment=? WHERE identifier=?',
                    (
                        event_type.serialize(),
                        event_subtype.serialize(),
                        counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY,
                        *rule.serialize_for_db(),
                        identifier,
                    ),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'Accounting rule for {self._rule_for_string(event_type=event_type, event_subtype=event_subtype, counterparty=counterparty)}'  # noqa: E501
                    ' already exists in the database',
                ) from e

            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Tried to update accounting {self._rule_for_string(event_type=event_type, event_subtype=event_subtype, counterparty=counterparty)}'  # noqa: E501
                    ' but it was not found',
                )

            # update links. First delete them for this rule and re-add them
            write_cursor.execute(
                'DELETE FROM linked_rules_properties WHERE accounting_rule=?',
                (identifier,),
            )
            for rule_property, setting_name in links.items():
                self.add_linked_setting(
                    write_cursor=write_cursor,
                    rule_identifier=identifier,
                    rule_property=rule_property,
                    setting_name=setting_name,
                )

    def add_linked_setting(
            self,
            write_cursor: 'DBCursor',
            rule_identifier: int,
            rule_property: LINKABLE_ACCOUNTING_PROPERTIES,
            setting_name: LINKABLE_ACCOUNTING_SETTINGS_NAME,
    ) -> None:
        """
        Store in the database a rule linked property that links it to a setting in the
        settings table.
        May raise: InputError
        """
        try:
            # when a setting has not been modified by the user it takes a default value that is
            # not persisted in the settings table. To avoid issues in the foreign key relations
            # we do a insert or ignore of the default value. Another option that might be reviewed
            # in the future would be to create a db upgrade inserting the missing settings and
            # add the settings related to accounting for new users in the database.
            if setting_name == 'include_crypto2crypto':
                default_value = DEFAULT_INCLUDE_CRYPTO2CRYPTO
            else:
                default_value = DEFAULT_INCLUDE_GAS_COSTS
            write_cursor.execute(
                'INSERT OR IGNORE INTO settings(name, value) VALUES (?, ?)',
                (setting_name, str(default_value)),
            )

            write_cursor.execute(
                'INSERT INTO linked_rules_properties(accounting_rule, property_name, '
                'setting_name) VALUES (?, ?, ?)',
                (rule_identifier, rule_property, setting_name),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Link of rule for {rule_property} to setting {setting_name} already exists',
            ) from e

    def query_rules(
            self,
            filter_query: AccountingRulesFilterQuery,
    ) -> tuple[list[RuleInformation], int]:
        """
        Query rules in the database using the provided filter. It returns the list of rules and
        the total amount of rules matching the filter without pagination.
        """
        query = (
            'SELECT identifier, type, subtype, counterparty, taxable, count_entire_amount_spend, '
            'count_cost_basis_pnl, accounting_treatment FROM accounting_rules '
        )
        filter_query_str, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query + filter_query_str, bindings)
            rules = {
                entry[0]: RuleInformation(
                    identifier=entry[0],
                    event_key=(
                        HistoryEventType.deserialize(entry[1]),
                        HistoryEventSubType.deserialize(entry[2]),
                        None if entry[3] == NO_ACCOUNTING_COUNTERPARTY else entry[3],
                    ),
                    rule=BaseEventSettings.deserialize_from_db(entry[4:]),
                    links={},
                )
                for entry in cursor
            }
            query, bindings = filter_query.prepare(with_pagination=False)
            query = 'SELECT COUNT(*) from accounting_rules ' + query
            total_found_result = cursor.execute(query, bindings).fetchone()[0]

            # check the settings linked to the rule using the defined filter
            settings = self.db.get_settings(cursor)
            cursor.execute(
                'SELECT accounting_rule, property_name, setting_name FROM '
                'linked_rules_properties WHERE accounting_rule IN (SELECT identifier FROM '
                f'accounting_rules {filter_query_str})',
                bindings,
            )
            for (accountint_rule_id, property_name, setting_name) in cursor:
                setting_value = getattr(settings, setting_name, None)
                if setting_value is None:
                    log.error(
                        f'Failed to read setting value for {setting_name} in '
                        'links for accounting rules',
                    )
                    continue

                if property_name == 'count_entire_amount_spend':
                    rules[accountint_rule_id].rule.count_entire_amount_spend = setting_value
                elif property_name == 'count_cost_basis_pnl':
                    rules[accountint_rule_id].rule.count_cost_basis_pnl = setting_value
                elif property_name == 'taxable':
                    rules[accountint_rule_id].rule.taxable = setting_value
                else:
                    log.error(f'Unknown accounting rule property {property_name}')
                    continue

                rules[accountint_rule_id].links[property_name] = setting_name

        return list(rules.values()), total_found_result

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
            data = entry.rule.serialize()
            data['identifier'] = entry.identifier
            data['event_type'] = entry.event_key[0].serialize()
            data['event_subtype'] = entry.event_key[1].serialize()
            data['counterparty'] = entry.event_key[2] if entry.event_key[2] != NO_ACCOUNTING_COUNTERPARTY else None  # noqa: E501
            for linked_property, setting_name in entry.links.items():
                data[linked_property]['linked_setting'] = setting_name
            entries.append(data)
        return entries, total_found_result


def _events_to_consume(
        cursor: 'DBCursor',
        callbacks: dict[int, tuple[int, EventsAccountantCallback]],
        events_iterator: Iterator[tuple[tuple[Any, ...], 'HistoryBaseEntry']],
        next_events: Sequence[HistoryBaseEntry],
        event: HistoryBaseEntry,
        pot: 'AccountingPot',
) -> list[int]:
    """
    Returns a list of event identifiers processed after checking possible accounting
    treatments and callbacks.
    """
    ids_processed: list[int] = []
    counterparty = getattr(event, 'counterparty', None)
    if counterparty == CPT_GAS:  # avoid checking the case of gas in evm events
        return ids_processed

    # query the accounting rule for the related event
    cursor.execute(
        'SELECT accounting_treatment FROM accounting_rules WHERE (type=? AND subtype=? AND (counterparty=? OR counterparty=?))',  # noqa: E501
        (
            event.event_type.serialize(),
            event.event_subtype.serialize(),
            NO_ACCOUNTING_COUNTERPARTY if counterparty is None else counterparty,
            NO_ACCOUNTING_COUNTERPARTY,
        ),
    )

    if (raw_treatment := cursor.fetchone()) is not None and raw_treatment[0] is not None:
        accounting_treatment = TxAccountingTreatment.deserialize_from_db(raw_treatment[0])
        if accounting_treatment == TxAccountingTreatment.SWAP:
            _, next_event = next(events_iterator)
            ids_processed.append(next_event.identifier)  # type: ignore[arg-type]
        else:
            for _ in range(2):  # swap_with_fee consumes two events
                _, next_event = next(events_iterator)
                ids_processed.append(next_event.identifier)  # type: ignore[arg-type]

        return ids_processed

    if isinstance(event, EvmEvent) is False:
        return ids_processed  # only evm events have callbacks

    # if there is no accounting treatment check for callbacks
    if (callback_data := callbacks.get(event.get_type_identifier())) is None:
        return ids_processed

    processed_events_num, callback = callback_data
    if processed_events_num == 1:  # we know that this callback only processes the current event
        return ids_processed

    # count the number of events that will be processed if accounting ran
    processed_events_num = callback(
        pot=pot,
        event=event,  # type: ignore[arg-type] # mypy doesn't recognize that this is an evm event
        other_events=iter(next_events),  # type: ignore[arg-type]  # mypy doesn't recognize that this is an evm event
    )

    for _ in range(processed_events_num - 1):  # -1 because we exclude the current event here
        _, next_event = next(events_iterator)
        ids_processed.append(next_event.identifier)  # type: ignore

    return ids_processed


def query_missing_accounting_rules(
        db: 'DBHandler',
        accountant: 'Accountant',
        accounting_pot: 'AccountingPot',
        evm_accounting_aggregator: 'EVMAccountingAggregators',
        events: Sequence[HistoryBaseEntry],
) -> list[bool]:
    """
    For a list of events returns a list of the same length with boolean values where True
    means that the event won't be affected by any accounting rule or processed in accounting
    """
    history_db = DBHistoryEvents(db)
    with db.conn.read_ctx() as cursor:
        # to know if an event will be processed or not in accounting we also need the related
        # events since they might use callbacks or special treatments
        related_events = history_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                event_identifiers=list({event.event_identifier for event in events}),
                order_by_rules=[('event_identifier', True), ('sequence_index', True)],
            ),
            has_premium=True,
        )

    query = 'SELECT COUNT(*) FROM accounting_rules WHERE (type=? AND subtype=? AND (counterparty=? OR counterparty=?))'  # noqa: E501
    bindings = [
        (
            event.event_type.serialize(),
            event.event_subtype.serialize(),
            NO_ACCOUNTING_COUNTERPARTY if (counterparty := getattr(event, 'counterparty', None)) is None else counterparty,  # noqa: E501
            NO_ACCOUNTING_COUNTERPARTY,  # account for rules based only on type/subtype
        ) for event in related_events
    ]

    callbacks = evm_accounting_aggregator.get_accounting_callbacks()
    bindings_and_events_iterator = zip(bindings, related_events)
    with db.conn.read_ctx() as cursor:
        # index to keep the current event in the list of related events. It is used in the
        # callbacks since we need to process events but we don't want to consume the current
        # iterator
        current_event_index = 0
        for event_binding, event in bindings_and_events_iterator:
            if accountant.processable_events_cache.get(event.identifier) is not None:  # type: ignore
                current_event_index += 1
                continue

            if (
                    isinstance(event, EthStakingEvent) or
                    (isinstance(event, EvmEvent) and event.event_identifier.startswith('BP1_'))
            ):
                # staking events all have a process() function for accounting
                accountant.processable_events_cache.add(event.identifier, False)  # type: ignore
                current_event_index += 1
                continue

            # check the rule in the database
            row = cursor.execute(query, event_binding).fetchone()
            is_missing_rule = row[0] == 0
            accountant.processable_events_cache.add(event.identifier, is_missing_rule)  # type: ignore

            # the current event in addition to have an accounting rule could have a callback that
            # affects events that come after and is not enough to check the accounting rule
            new_missing_accounting_rule = _events_to_consume(
                cursor=cursor,
                callbacks=callbacks,
                events_iterator=bindings_and_events_iterator,
                next_events=related_events[current_event_index + 1:],
                event=event,
                pot=accounting_pot,
            )
            if len(new_missing_accounting_rule) != 0:
                current_event_index += len(new_missing_accounting_rule)
                if is_missing_rule is True:  # we processed it in the callback so is not missing
                    accountant.processable_events_cache.add(event.identifier, False)  # type: ignore

                # update information about the new events
                for processed_event_id in new_missing_accounting_rule:
                    accountant.processable_events_cache.add(processed_event_id, False)

    # we use bool because the cache can return None and in order to cover this case we use
    # `None`'s Falsy value meaning that the event doesn't have an accounting rule
    return [bool(accountant.processable_events_cache.get(event.identifier)) for event in events]  # type: ignore[arg-type]
