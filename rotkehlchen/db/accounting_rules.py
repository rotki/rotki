import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NamedTuple

from more_itertools import peekable
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.types import EventAccountingRuleStatus
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
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.eth2 import EthStakingEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
    event_key: tuple[HistoryEventType, HistoryEventSubType, str | None]
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
            counterparty: str | None,
    ) -> str:
        return f'Rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty})'

    def add_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            force_update: bool = False,
    ) -> int:
        """
        Add a single accounting rule to the database. It returns the identifier
        of the created rule.
        May raise:
        - InputError: If the combination of type, subtype and counterparty already exists
        and we are not force updating.
        """
        verb = 'INSERT OR REPLACE' if force_update else 'INSERT'
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    f'{verb} INTO accounting_rules(type, subtype, counterparty, taxable, '
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

    def remove_accounting_rule(self, rule_id: int) -> tuple[HistoryEventType, HistoryEventSubType, str | None]:  # noqa: E501
        """
        Delete an accounting using its identifier. Returns the type identifier for the rule.
        May raise:
        - InputError if the rule doesn't exist
        """
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'SELECT type, subtype, counterparty FROM accounting_rules WHERE identifier=?',
                (rule_id,),
            )
            if (entry := write_cursor.fetchone()) is None:
                raise InputError(f'Rule with id {rule_id} does not exist')

            event_type = HistoryEventType.deserialize(entry[0])
            event_subtype = HistoryEventSubType.deserialize(entry[1])
            counterparty = None if entry[2] == NO_ACCOUNTING_COUNTERPARTY else entry[2]

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

            return event_type, event_subtype, counterparty

    def update_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
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

    def fetch_accounting_rules_from_db(
            self,
            filter_query_str: str,
            bindings: Sequence[Any],
    ) -> dict[int, RuleInformation]:
        """Query the accounting rules from the database using the provided filter. Returns
        the dict of identifier -> accounting rules."""
        query = (
            'SELECT identifier, type, subtype, counterparty, taxable, count_entire_amount_spend, '
            'count_cost_basis_pnl, accounting_treatment FROM accounting_rules '
        )
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query + filter_query_str, bindings)
            return {
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

    def query_rules(
            self,
            filter_query: AccountingRulesFilterQuery,
    ) -> tuple[list[RuleInformation], int]:
        """
        Query rules in the database using the provided filter along with their property settings.
        It returns the list of rules and the total amount of rules matching the filter
        without pagination."""
        filter_query_str, bindings = filter_query.prepare()
        rules = self.fetch_accounting_rules_from_db(filter_query_str, bindings)

        with self.db.conn.read_ctx() as cursor:
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

    def get_accounting_rules_and_properties(self) -> dict[str, dict]:
        """Returns all the accounting rules and linked properties from the database."""
        accounting_rules = {
            identifier: {
                'event_type': rule_info.event_key[0].serialize(),
                'event_subtype': rule_info.event_key[1].serialize(),
                'counterparty': rule_info.event_key[2] if rule_info.event_key[2] != NO_ACCOUNTING_COUNTERPARTY else None,  # noqa: E501
                'rule': rule_info.rule.serialize(),
            }
            for identifier, rule_info in self.fetch_accounting_rules_from_db('', []).items()
        }

        with self.db.conn.read_ctx() as cursor:
            linked_properties = {
                entry[0]: {
                    'accounting_rule': entry[1],
                    'property_name': entry[2],
                    'setting_name': entry[3],
                }
                for entry in cursor.execute(
                    'SELECT identifier, accounting_rule, property_name, setting_name FROM '
                    'linked_rules_properties;',
                )
            }

        return {
            'accounting_rules': accounting_rules,
            'linked_properties': linked_properties,
        }

    def import_accounting_rules(
            self,
            accounting_rules: dict,
            linked_properties: dict,
    ) -> tuple[bool, str]:
        """Import the given accounting rules and linked properties into the database. It overwrites
        the existing rules if the same rule already exists. Returns a tuple with a boolean
        indicating success or failure and an error message."""
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO accounting_rules(identifier, type, subtype, '
                    'counterparty, taxable, count_entire_amount_spend, count_cost_basis_pnl, '
                    'accounting_treatment) VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
                    [
                        (
                            identifier,
                            rule_info['event_type'],
                            rule_info['event_subtype'],
                            rule_info['counterparty'] if rule_info['counterparty'] is not None else NO_ACCOUNTING_COUNTERPARTY,  # noqa: E501
                            *BaseEventSettings.deserialize(rule_info['rule']).serialize_for_db(),
                        )
                        for identifier, rule_info in accounting_rules.items()
                    ],
                )
            except (sqlcipher.IntegrityError, DeserializationError) as e:  # pylint: disable=no-member
                return False, f'Failed to import accounting rules due to: {e!s}'

            try:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO linked_rules_properties(identifier, accounting_rule, '
                    'property_name, setting_name) VALUES (?, ?, ?, ?)',
                    [
                        (
                            identifier,
                            linked_property['accounting_rule'],
                            linked_property['property_name'],
                            linked_property['setting_name'],
                        )
                        for identifier, linked_property in linked_properties.items()
                    ],
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                return False, f'Failed to import linked properties due to: {e!s}'

        return True, ''


def _events_to_consume(
        cursor: 'DBCursor',
        callbacks: dict[int, tuple[int, EventsAccountantCallback]],
        events_iterator: "peekable[tuple[tuple[Any, ...], 'HistoryBaseEntry']]",
        next_events: Sequence[HistoryBaseEntry],
        event: HistoryBaseEntry,
        pot: 'AccountingPot',
) -> list[tuple[int, int]]:
    """
    Returns a list of event identifiers processed after checking possible accounting
    treatments and callbacks.
    """
    ids_processed: list[tuple[int, int]] = []
    counterparty = getattr(event, 'counterparty', None)
    if counterparty == CPT_GAS:  # avoid checking the case of gas in evm events
        return ids_processed

    # query the accounting rule for the related event. First check using the counterparty
    # and if it doesn't exist then check for a generic rule
    query = 'SELECT accounting_treatment FROM accounting_rules WHERE type=? AND subtype=? AND counterparty=?'  # noqa: E501
    event_type = event.event_type.serialize()
    event_subtype = event.event_subtype.serialize()
    event_type_identifier = event.get_type_identifier()

    raw_treatment = cursor.execute(
        query,
        (event_type, event_subtype, NO_ACCOUNTING_COUNTERPARTY if counterparty is None else counterparty),  # noqa: E501
    ).fetchone()

    if raw_treatment is None and counterparty is not None:
        raw_treatment = cursor.execute(
            query,
            (event_type, event_subtype, NO_ACCOUNTING_COUNTERPARTY),
        ).fetchone()

    if raw_treatment is not None and raw_treatment[0] is not None:
        accounting_treatment = TxAccountingTreatment.deserialize_from_db(raw_treatment[0])
        if accounting_treatment == TxAccountingTreatment.SWAP:
            _, peeked_event = events_iterator.peek((None, None))
            if peeked_event is None or peeked_event.event_identifier != event.event_identifier:
                log.error(f'Event with {event.event_identifier=} should have a SWAP IN event')
                return ids_processed
            _, next_event = next(events_iterator)
            ids_processed.append((next_event.identifier, event_type_identifier))  # type: ignore[arg-type]

            _, peeked_event = events_iterator.peek((None, None))
            if peeked_event and peeked_event.event_identifier == event.event_identifier and peeked_event.event_subtype == HistoryEventSubType.FEE:  # noqa: E501
                # consume the related fee if it exists
                _, next_event = next(events_iterator)
                ids_processed.append((next_event.identifier, event_type_identifier))  # type: ignore[arg-type]

        return ids_processed

    if isinstance(event, EvmEvent) is False:
        return ids_processed  # only evm events have callbacks

    # if there is no accounting treatment check for callbacks
    if (callback_data := callbacks.get(event_type_identifier)) is None:
        return ids_processed

    processed_events_num, callback = callback_data
    if processed_events_num == 1:  # we know that this callback only processes the current event
        return ids_processed

    # count the number of events that will be processed if accounting ran
    processed_events_num = callback(
        pot=pot,
        event=event,  # type: ignore[arg-type] # mypy doesn't recognize that this is an evm event
        other_events=peekable(next_events),  # type: ignore[arg-type]  # mypy doesn't recognize that this is an evm event
    )

    for _ in range(processed_events_num - 1):  # -1 because we exclude the current event here
        try:
            _, next_event = next(events_iterator)
        except StopIteration:
            log.error('Failed to get an expected event from iterator during missing accounting rules check')  # noqa: E501
            return ids_processed

        ids_processed.append((next_event.identifier, event_type_identifier))  # type: ignore

    return ids_processed


def query_missing_accounting_rules(
        db: 'DBHandler',
        accountant: 'Accountant',
        accounting_pot: 'AccountingPot',
        evm_accounting_aggregator: 'EVMAccountingAggregators',
        events: Sequence[HistoryBaseEntry],
) -> list[EventAccountingRuleStatus]:
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
    bindings_and_events_iterator = peekable(zip(bindings, related_events, strict=True))
    with db.conn.read_ctx() as cursor:
        # index to keep the current event in the list of related events. It is used in the
        # callbacks since we need to process events but we don't want to consume the current
        # iterator
        current_event_index = 0
        for event_binding, event in bindings_and_events_iterator:
            if accountant.processable_events_cache.get(event.identifier) is not None:
                current_event_index += 1
                continue

            if (
                    event.event_type == HistoryEventType.INFORMATIONAL or
                    # staking events all have a process() function for accounting
                    isinstance(event, EthStakingEvent) or
                    (isinstance(event, EvmEvent) and event.event_identifier.startswith('BP1_'))
            ):

                accountant.processable_events_cache.add(event.identifier, EventAccountingRuleStatus.PROCESSED)  # type: ignore  # noqa: E501
                current_event_index += 1
                continue

            # check the rule in the database
            row = cursor.execute(query, event_binding).fetchone()
            accounting_outcome = EventAccountingRuleStatus.NOT_PROCESSED if row[0] == 0 else EventAccountingRuleStatus.HAS_RULE  # noqa: E501
            accountant.processable_events_cache.add(event.identifier, accounting_outcome)  # type: ignore
            accountant.processable_events_cache_signatures.get(event.get_type_identifier()).append(event.identifier)  # type: ignore

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
                if accounting_outcome is EventAccountingRuleStatus.NOT_PROCESSED:  # we processed it in the callback so is not missing  # noqa: E501
                    accountant.processable_events_cache[event.identifier] = EventAccountingRuleStatus.PROCESSED

                # update information about the new events
                for processed_event_id, event_type_identifier in new_missing_accounting_rule:
                    accountant.processable_events_cache[processed_event_id] = EventAccountingRuleStatus.PROCESSED
                    if event_type_identifier not in accountant.processable_events_cache_signatures:
                        accountant.processable_events_cache_signatures[event_type_identifier] = []
                    accountant.processable_events_cache_signatures[event_type_identifier].append(processed_event_id)

    result = []
    for event in events:
        if (processable_status := accountant.processable_events_cache.get(event.identifier)) is None:
            result.append(EventAccountingRuleStatus.NOT_PROCESSED)
        else:
            result.append(processable_status)

    return result
