import pytest
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.errors.misc import InputError


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
