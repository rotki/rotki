import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.constants.assets import A_CUSDC, A_ETH, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.accounting_rules import DBAccountingRules, query_missing_accounting_rules
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history_base_entry import add_entries, store_and_retrieve_events
from rotkehlchen.types import Location, TimestampMS


def test_managing_accounting_rules(database: DBHandler) -> None:
    """Test common operations in accounting rules"""
    db = DBAccountingRules(database)
    rule = BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    query_all_rules = 'SELECT * FROM accounting_rules'

    # first try to store the rule in the db
    accounting_rule_id = db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty='uniswap',
        rule=rule,
        links={},
    )
    assert accounting_rule_id == 1
    # add another rule without counterparty to test that we respect the primary key
    # and the edit/delete
    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=None,
        rule=rule,
        links={},
    )
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db(), 0),  # noqa: E501
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db(), 0),  # noqa: E501
        ]

    # try to edit it
    rule.count_cost_basis_pnl = False
    rule.accounting_treatment = None
    db.update_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty='uniswap',
        rule=rule,
        identifier=1,
        links={},
    )
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 0, None, 0),
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db(), 0),  # noqa: E501
        ]

    # try to delete first the general rule
    db.remove_accounting_rule(rule_id=2)
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [(1, 'trade', 'receive', 'uniswap', 1, 1, 0, None, 0)]

    # and now delete all the rules
    db.remove_accounting_rule(rule_id=1)
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert len(entries) == 0


def test_errors_with_rules(database: DBHandler) -> None:
    """Test different situations that can lead to errors when managing accounting rules"""
    db = DBAccountingRules(database)
    rule = BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )

    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=None,
        rule=rule,
        links={},
    )
    # Try adding a rule that already exists
    with pytest.raises(InputError):
        db.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=None,
            rule=rule,
            links={},
        )

    # now delete a non existing rule
    with pytest.raises(InputError):
        db.remove_accounting_rule(rule_id=99)


@pytest.mark.parametrize('db_settings', [{'include_crypto2crypto': True}])
@pytest.mark.parametrize('counterparty', ['yabir'])
def test_accounting_rules_linking(database: 'DBHandler', counterparty: str) -> None:
    """Test that creating a link for a rule property works as expected"""
    db = DBAccountingRules(database)
    db.add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        counterparty=counterparty,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=False,
        ),
        links={'count_cost_basis_pnl': 'include_crypto2crypto'},
    )
    rules, _ = db.query_rules_and_serialize(
        filter_query=AccountingRulesFilterQuery.make(
            counterparties=[counterparty],
        ),
    )

    assert len(rules) == 1
    assert rules[0] == {
        'identifier': 1,
        'event_ids': None,
        'event_type': HistoryEventType.SPEND.serialize(),
        'event_subtype': HistoryEventSubType.FEE.serialize(),
        'counterparty': counterparty,
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': True},
        'count_cost_basis_pnl': {'value': True, 'linked_setting': 'include_crypto2crypto'},
        'accounting_treatment': None,
    }


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_missing_accounting_rules_accounting_treatment(
        database: 'DBHandler',
        accountant: Accountant,
) -> None:
    """
    Test that if a rule has a special accounting treatment then the events
    that can be affected by it are not marked as missing the accounting rule.
    """
    db = DBAccountingRules(database)
    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_COWSWAP,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    swap_event_spend = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_USDC,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    swap_event_receive = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_ETH,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    swap_event_fee = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_ETH,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    events = store_and_retrieve_events([swap_event_spend, swap_event_receive, swap_event_fee], database)  # noqa: E501
    assert EventAccountingRuleStatus.NOT_PROCESSED not in query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    )


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affected_by_others_accounting_treatment(
        database: 'DBHandler',
        accountant: Accountant,
) -> None:
    """
    Test that if a rule has a special accounting treatment then the events
    that can be affected by it are not marked as missing the accounting rule.
    """
    db = DBAccountingRules(database)
    db.add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_COMPOUND,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        amount=ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        amount=ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )

    events = store_and_retrieve_events([return_wrapped, remove_asset], database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    ) == [
        EventAccountingRuleStatus.HAS_RULE,
        EventAccountingRuleStatus.PROCESSED,
    ]


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affected_by_others_accounting_treatment_with_fee(
        database: 'DBHandler',
        accountant: Accountant,
) -> None:
    """
    Test that if a rule has an accounting treatment with fee then the events
    that can be affected by it are not marked as missing the accounting rule.
    """
    db = DBAccountingRules(database)
    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_COWSWAP,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    fee_event = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        amount=ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )

    events = store_and_retrieve_events([return_wrapped, fee_event, remove_asset], database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    ) == [
        EventAccountingRuleStatus.HAS_RULE,
        EventAccountingRuleStatus.PROCESSED,
        EventAccountingRuleStatus.PROCESSED,
    ]


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_correct_accounting_treatment_is_selected(
        database: 'DBHandler',
        accountant: Accountant,
) -> None:
    """
    Test that if an event is affected by both a rule with counterparty and a generic rule
    then the accounting treatment from the one with counterparty is used
    """
    db = DBAccountingRules(database)
    db.add_accounting_rule(  # this rule shouldn't affect the event
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        counterparty=NO_ACCOUNTING_COUNTERPARTY,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=None,
        ),
        links={},
    )
    db.add_accounting_rule(
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        counterparty=CPT_COMPOUND,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
    )

    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        amount=ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        amount=ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )

    events = store_and_retrieve_events([return_wrapped, remove_asset], database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    ) == [EventAccountingRuleStatus.HAS_RULE, EventAccountingRuleStatus.PROCESSED]


def test_event_specific_rule_adds_to_existing_rule(database: DBHandler) -> None:
    """Test that event-specific rules remove events
    from existing rules and add to existing event-specific rule"""
    db = DBAccountingRules(database)
    rule = BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        accounting_treatment=None,
    )

    # Create test events using the utility function
    entries = add_entries(DBHistoryEvents(database))
    event_ids = [int(entry.identifier) for entry in entries[:3]]  # type: ignore[arg-type]  # id is present

    # Create initial event-specific rule for first two events
    rule_id_1 = db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty='uniswap',
        rule=rule,
        links={},
        event_ids=event_ids[:2],
    )

    # Verify the rule was created correctly
    with database.conn.read_ctx() as cursor:
        rule_events = cursor.execute(
            'SELECT event_id FROM accounting_rule_events WHERE rule_id=?',
            (rule_id_1,),
        ).fetchall()
        assert {row[0] for row in rule_events} == set(event_ids[:2])

    # Try to add third event to the existing rule (default event-specific behavior)
    rule_id_2 = db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty='uniswap',
        rule=rule,
        links={},
        event_ids=[event_ids[2]],
    )
    assert rule_id_1 == rule_id_2

    # Verify that third event was added to the existing rule
    with database.conn.read_ctx() as cursor:
        rule_events = cursor.execute(
            'SELECT event_id FROM accounting_rule_events WHERE rule_id=?',
            (rule_id_1,),
        ).fetchall()
        assert {row[0] for row in rule_events} == set(event_ids)
        assert cursor.execute('SELECT COUNT(*) FROM accounting_rules').fetchone()[0] == 1


def test_event_specific_rule_creates_new_rule(database: DBHandler) -> None:
    """Test that event-specific rules remove events
    from existing rules and create new event-specific rule"""
    db = DBAccountingRules(database)
    rule = BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        accounting_treatment=None,
    )

    # Create test events using the utility function
    entries = add_entries(DBHistoryEvents(database))
    event_ids = [int(entry.identifier) for entry in entries[:3]]  # type: ignore[arg-type]  # id is present

    # Create first event-specific rule for all three events
    rule_id_1 = db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty='uniswap',
        rule=rule,
        links={},
        event_ids=event_ids,
    )

    # Verify initial state
    with database.conn.read_ctx() as cursor:
        rule_1_events = cursor.execute(
            'SELECT event_id FROM accounting_rule_events WHERE rule_id=?',
            (rule_id_1,),
        ).fetchall()
        assert {row[0] for row in rule_1_events} == set(event_ids)
        assert cursor.execute('SELECT COUNT(*) FROM accounting_rules').fetchone()[0] == 1

    # Create new event-specific rule with different type/subtype/counterparty
    # This should create a separate rule since the combination is different
    rule_id_2 = db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty='uniswap',
        rule=BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=None,
        ),
        links={},
        event_ids=[event_ids[1]],
    )
    assert rule_id_1 != rule_id_2

    # Verify that second event was removed from rule_1 and a new rule was created
    with database.conn.read_ctx() as cursor:
        rule_1_events = cursor.execute(
            'SELECT event_id FROM accounting_rule_events WHERE rule_id=?',
            (rule_id_1,),
        ).fetchall()
        assert {row[0] for row in rule_1_events} == {event_ids[0], event_ids[2]}  # second event removed  # noqa: E501

        rule_2_events = cursor.execute(
            'SELECT event_id FROM accounting_rule_events WHERE rule_id=?',
            (rule_id_2,),
        ).fetchall()
        assert {row[0] for row in rule_2_events} == {event_ids[1]}  # second event in new rule
        assert cursor.execute('SELECT COUNT(*) FROM accounting_rules').fetchone()[0] == 2
