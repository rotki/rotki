import pytest
from rotkehlchen.accounting.structures import LedgerActionType, LedgerAction
from rotkehlchen.typing import Location, AssetAmount
from rotkehlchen.fval import FVal
from rotkehlchen.constants.assets import A_ETH, A_BTC
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.tests.utils.accounting import accounting_history_process
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.serialization.deserialize import deserialize_ledger_action_type_from_db


def test_serialize_str():
    for entry in LedgerActionType:
        assert isinstance(str(entry), str)

    for entry in LedgerActionType:
        assert isinstance(entry.serialize(), str)


def test_serialize_deserialize_for_db():
    for entry in LedgerActionType:
        db_code = entry.serialize_for_db()
        assert deserialize_ledger_action_type_from_db(db_code) == entry


def test_all_action_types_writtable_in_db(database, function_scope_messages_aggregator):
    db = DBLedgerActions(database, function_scope_messages_aggregator)
    for entry in LedgerActionType:
        db.add_ledger_action(
            timestamp=1,
            action_type=entry,
            location=Location.EXTERNAL,
            amount=FVal(1),
            asset=A_ETH,
            link='',
            notes='',
        )
    assert len(db.get_ledger_actions(None, None, None)) == len(LedgerActionType)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected_pnl', [
    ({'taxable_ledger_actions': [
        LedgerActionType.INCOME,
        LedgerActionType.AIRDROP,
        LedgerActionType.LOSS]},
     FVal('706.275')),  # 578.505 + 478.65 - 350.88
    ({'taxable_ledger_actions': []}, 0),
])
def test_taxable_ledger_action_setting(accountant, expected_pnl):
    """Test that ledger actions respect the taxable setting"""
    ledger_actions_list = [
        LedgerAction(
            identifier=1,
            timestamp=1476979735,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            amount=FVal(1),  # 578.505 EUR from mocked prices
            asset=A_BTC,
            link='',
            notes='',
        ), LedgerAction(
            identifier=2,
            timestamp=1491062063,
            action_type=LedgerActionType.AIRDROP,
            location=Location.EXTERNAL,
            amount=FVal(10),  # 478.65 EUR from mocked prices
            asset=A_ETH,
            link='',
            notes='',
        ), LedgerAction(
            identifier=3,
            timestamp=1501062063,
            action_type=LedgerActionType.LOSS,
            location=Location.BLOCKCHAIN,
            amount=FVal(2),  # 350.88 EUR from mocked prices
            asset=A_ETH,
            link='',
            notes='',
        ),
    ]
    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history_list=[],
        ledger_actions_list=ledger_actions_list,
    )
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close(expected_pnl)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_ledger_actions_accounting(accountant):
    """Test for accounting for ledger actions

    Makes sure that Ledger actions are processed in accounting, range is respected
    and that they contribute to the "bought" amount per asset
    """
    ledger_actions_history = [LedgerAction(  # before range - read only for amount not profit
        identifier=1,
        timestamp=1435979735,  # 0.1 EUR per ETH
        action_type=LedgerActionType.INCOME,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(FVal(1)),
        link='',
        notes='',
    ), LedgerAction(
        identifier=2,
        timestamp=1437279735,  # 250 EUR per BTC
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKCHAIN,
        asset=A_BTC,
        amount=AssetAmount(FVal(1)),
        link='',
        notes='',
    ), LedgerAction(
        identifier=3,
        timestamp=1447279735,  # 0.4 EUR per XMR
        action_type=LedgerActionType.DIVIDENDS_INCOME,
        location=Location.KRAKEN,
        asset=A_XMR,
        amount=AssetAmount(FVal(10)),
        link='',
        notes='',
    ), LedgerAction(
        identifier=4,
        timestamp=1457279735,  # 1 EUR per ETH
        action_type=LedgerActionType.EXPENSE,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(FVal('0.1')),
        link='',
        notes='',
    ), LedgerAction(
        identifier=5,
        timestamp=1467279735,  # 420 EUR per BTC
        action_type=LedgerActionType.LOSS,
        location=Location.EXTERNAL,
        asset=A_BTC,
        amount=AssetAmount(FVal('0.1')),
        link='',
        notes='',
    ), LedgerAction(  # after range and should be completely ignored
        identifier=6,
        timestamp=1529693374,
        action_type=LedgerActionType.EXPENSE,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(FVal('0.5')),
        link='',
        notes='',
    )]

    result = accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=[],
        ledger_actions_list=ledger_actions_history,
    )
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BTC).is_close('0.9')
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_ETH).is_close('0.9')
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_XMR).is_close('10')
    # 250 * 1 + 0.4 * 10 - 1 * 0.1  - 420 * 0.1 = 211.9
    assert FVal(result['overview']['ledger_actions_profit_loss']).is_close('211.9')
    assert FVal(result['overview']['total_profit_loss']).is_close('211.9')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('211.9')
