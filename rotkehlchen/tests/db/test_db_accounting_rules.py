from collections.abc import Sequence
import pytest
from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_CUSDC, A_ETH, A_USDC, A_WETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.accounting_rules import DBAccountingRules, query_missing_accounting_rules
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import AccountingRulesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS


def _store_and_retrieve_events(
        events: Sequence[HistoryBaseEntry],
        db: DBHandler,
) -> Sequence[HistoryBaseEntry]:
    """Store events in database and retrieve them again fully populated with identifiers"""
    dbevents = DBHistoryEvents(db)
    with db.user_write() as write_cursor:
        for event in events:
            dbevents.add_history_event(
                write_cursor=write_cursor,
                event=event,
            )
        return dbevents.get_history_events(
            cursor=write_cursor,
            filter_query=HistoryEventFilterQuery.make(event_identifiers=[events[0].event_identifier]),
            has_premium=True,
        )  # query them from db to retrieve them with their identifier


def test_managing_accounting_rules(database: DBHandler) -> None:
    """Test common operations in accounting rules"""
    db = DBAccountingRules(database)
    rule = TxEventSettings(
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
            (1, 'trade', 'receive', 'uniswap', 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
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
            (1, 'trade', 'receive', 'uniswap', 1, 1, 0, None),
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
        ]

    # try to delete first the general rule
    db.remove_accounting_rule(rule_id=2)
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 0, None),
        ]

    # and now delete all the rules
    db.remove_accounting_rule(rule_id=1)
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert len(entries) == 0


def test_errors_with_rules(database: DBHandler) -> None:
    """Test different situations that can lead to errors when managing accounting rules"""
    db = DBAccountingRules(database)
    rule = TxEventSettings(
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
        rule=TxEventSettings(
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
        rule=TxEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP_WITH_FEE,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    swap_event_spend = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_USDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    swap_event_receive = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_ETH,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    swap_event_fee = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(16433333000),
        location=Location.GNOSIS,
        asset=A_ETH,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_COWSWAP,
        notes='my notes',
    )
    events = _store_and_retrieve_events([swap_event_spend, swap_event_receive, swap_event_fee], database)  # noqa: E501
    assert not all(
        query_missing_accounting_rules(
            db=database,
            accounting_pot=accountant.pots[0],
            evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
            events=events,
            accountant=accountant,
        ),
    )


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affeced_by_others_accounting_treatment(
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
        rule=TxEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )

    events = _store_and_retrieve_events([return_wrapped, remove_asset], database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    ) == [False, False]


@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affeced_by_others_accounting_treatment_with_fee(
        database: 'DBHandler',
        accountant: Accountant,
) -> None:
    """
    Test that if a rule has an accounting treatment with fee then the events
    that can be affected by it are not marked as missing the accounting rule.
    """
    db = DBAccountingRules(database)
    db.add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_COMPOUND,
        rule=TxEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP_WITH_FEE,
        ),
        links={},
    )
    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    fee_event = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )

    events = _store_and_retrieve_events([return_wrapped, fee_event, remove_asset], database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=events,
        accountant=accountant,
    ) == [False, False, False]


@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])
@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affected_by_others_callbacks(
        database: 'DBHandler',
        accountant: Accountant,
        ethereum_accounts,
) -> None:
    """
    Test that if a rule has a special accounting treatment then the events
    that can be affected by it are not marked as missing the accounting rule.
    """
    tx_hash = make_evm_tx_hash()
    user_address = ethereum_accounts[0]
    events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_USDC,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label=user_address,
            notes='Return 0.042569019597126949 BPT to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data={'withdrawal_events_num': 2},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            location_label=user_address,
            balance=Balance(amount=FVal('0.744372160905819159')),
            notes='Receive 0.744372160905819159 BAL after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            location_label=user_address,
            balance=Balance(amount=FVal('0.010687148200906598')),
            notes='Receive 0.010687148200906598 WETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data=None,
        ),
    ]
    db_events = _store_and_retrieve_events(events, database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=db_events,
        accountant=accountant,
    ) == [False, False, False]


@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])
@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('use_dummy_pot', [True])
def test_events_affected_by_others_callbacks_with_fitlers(
        database: 'DBHandler',
        accountant: Accountant,
        ethereum_accounts,
) -> None:
    """
    Test that a callback with a filtered list of events is correctly accounted even if the
    event with the callback is not in the processed set.
    """
    tx_hash = make_evm_tx_hash()
    user_address = ethereum_accounts[0]
    events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_USDC,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label=user_address,
            notes='Return 0.042569019597126949 BPT to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data={'withdrawal_events_num': 2},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            location_label=user_address,
            balance=Balance(amount=FVal('0.744372160905819159')),
            notes='Receive 0.744372160905819159 BAL after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            location_label=user_address,
            balance=Balance(amount=FVal('0.010687148200906598')),
            notes='Receive 0.010687148200906598 WETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            extra_data=None,
        ),
    ]
    db_events = _store_and_retrieve_events(events, database)
    assert query_missing_accounting_rules(
        db=database,
        accounting_pot=accountant.pots[0],
        evm_accounting_aggregator=accountant.pots[0].events_accountant.evm_accounting_aggregators,
        events=db_events[1:],
        accountant=accountant,
    ) == [False, False]
