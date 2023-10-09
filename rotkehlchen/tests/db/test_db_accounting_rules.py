import pytest
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import InputError


def test_managing_accounting_rules(database: DBHandler) -> None:
    """Test common operations in accounting rules"""
    db = DBAccountingRules(database)
    rule = TxEventSettings(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='acquisition',
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    query_all_rules = 'SELECT * FROM accounting_rules'

    # first try to store the rule in the db
    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty='uniswap',
        rule=rule,
    )
    # add another rule without counterparty to test that we respect the primary key
    # and the edit/delete
    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=None,
        rule=rule,
    )
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 1, 'acquisition', TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, 'acquisition', TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
        ]

    # try to edit it
    rule.count_cost_basis_pnl = False
    rule.accounting_treatment = None
    rule.method = 'spend'
    db.update_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty='uniswap',
        rule=rule,
        identifier=1,
    )
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 0, 'spend', None),
            (2, 'trade', 'receive', NO_ACCOUNTING_COUNTERPARTY, 1, 1, 1, 'acquisition', TxAccountingTreatment.SWAP.serialize_for_db()),  # noqa: E501
        ]

    # try to delete first the general rule
    db.remove_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=None,
    )
    with database.conn.read_ctx() as cursor:
        entries = cursor.execute(query_all_rules).fetchall()
        assert entries == [
            (1, 'trade', 'receive', 'uniswap', 1, 1, 0, 'spend', None),
        ]

    # and now delete all the rules
    db.remove_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty='uniswap',
    )
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
        method='acquisition',
        accounting_treatment=TxAccountingTreatment.SWAP,
    )

    db.add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=None,
        rule=rule,
    )
    # Try adding a rule that already exists
    with pytest.raises(InputError):
        db.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=None,
            rule=rule,
        )

    # now delete a non existing rule
    with pytest.raises(InputError):
        db.remove_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty='uniswap',
        )

    # try to update a rule that doesn't exist
    with pytest.raises(InputError):
        db.remove_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty='uniswap',
        )
