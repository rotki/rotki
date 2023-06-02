import csv
import tempfile
from itertools import zip_longest
from pathlib import Path

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis import AssetAcquisitionEvent
from rotkehlchen.accounting.export.csv import FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.types import MissingAcquisition
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.constants.assets import A_3CRV, A_BTC, A_ETH, A_EUR, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    AssetAmount,
    CostBasisMethod,
    Fee,
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
)

EXAMPLE_TIMESTAMP = Timestamp(1675483017)


def add_acquisition(pot, amount, asset=A_ETH, price=ONE, taxable=False):
    """
    Util function to add an acquisition to an accounting pot.
    Timestamp doesn't matter here since we provide `given_price`, but has to be big enough so that
    `handle_prefork_acquisitions` is not called.
    """
    pot.add_acquisition(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Test',
        location=Location.BLOCKCHAIN,
        timestamp=EXAMPLE_TIMESTAMP,
        asset=asset,
        amount=amount,
        taxable=taxable,
        given_price=price,
    )


def add_spend(pot, amount, asset=A_ETH, price=ONE, taxable=True):
    """
    Util function to add a spend event to an accounting pot.
    Timestamp doesn't matter here since we provide `given_price`, but has to be big enough so that
    `handle_prefork_acquisitions` is not called.
    """
    pot.add_spend(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Test',
        location=Location.BLOCKCHAIN,
        timestamp=EXAMPLE_TIMESTAMP,
        asset=asset,
        amount=amount,
        taxable=taxable,
        given_price=price,
        count_entire_amount_spend=False,
    )


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_after_year(accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(15),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(3),  # 25/10/2016
            timestamp=1477378304,
            rate=FVal(603.415),
            index=3,
        ),
    )

    spending_amount = FVal(8)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )

    assert cinfo.taxable_amount == 3, '3 out of 8 should be taxable (within a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('1340.5'))
    assert cinfo.taxable_bought_cost.is_close(FVal('1837.35'))
    assert len(cinfo.matched_acquisitions) == 2
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO
    assert cinfo.matched_acquisitions[1].amount == FVal(3)
    assert cinfo.matched_acquisitions[1].event.amount == FVal(15)
    assert cinfo.matched_acquisitions[1].event.remaining_amount == FVal(12)

    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    acquisitions_num = len(acquisitions)
    assert acquisitions_num == 2, 'first buy should have been used'
    remaining_amount = acquisitions[0].remaining_amount
    assert remaining_amount == FVal(12), '3 of 15 should have been consumed'


def test_calculate_spend_cost_basis_1_buy_consumed_by_1_sell(accountant):
    """ Assert bought_cost is correct when 1 buy is completely consumed by 1 sell

    Regression test for part of https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )

    spending_amount = FVal(5)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 5, '5 out of 5 should be taxable (within a year)'
    assert cinfo.taxfree_bought_cost == ZERO
    assert cinfo.taxable_bought_cost.is_close(FVal('1340.5'))
    assert len(cinfo.matched_acquisitions) == 1
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO

    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'only buy should have been used'


def test_calculate_spend_cost_basis1_buy_used_by_2_sells_taxable(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxable part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('0'))
    assert cinfo.taxable_bought_cost.is_close(FVal('804.3'))
    assert len(cinfo.matched_acquisitions) == 1
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == spending_amount
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == FVal(2)

    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    acquisitions_num = len(acquisitions)
    assert acquisitions_num == 1, 'whole buy was not used'
    remaining_amount = acquisitions[0].remaining_amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    # now eat up all the rest
    spending_amount = FVal(2)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378404,  # bit after previous sell
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 2, '2 out of 2 should be taxable (within a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('0'))
    assert cinfo.taxable_bought_cost.is_close(FVal('536.2'))
    assert len(cinfo.matched_acquisitions) == 1
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == spending_amount
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO

    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'the buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_1_buy_used_by_2_sells_taxfree(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxfree part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 0, '0 out of 3 should be taxable (after a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('804.3'))
    assert cinfo.taxable_bought_cost.is_close(FVal('0'))
    assert len(cinfo.matched_acquisitions) == 1
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == spending_amount
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == FVal(2)

    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    acquisitions_num = len(acquisitions)
    assert acquisitions_num == 1, 'whole buy was not used'
    remaining_amount = acquisitions[0].remaining_amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    spending_amount = FVal(2)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683954,  # bit after previous sell
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 0, '0 out of 2 should be taxable (after a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('536.2'))
    assert cinfo.taxable_bought_cost.is_close(FVal('0'))
    assert len(cinfo.matched_acquisitions) == 1
    assert sum(x.amount for x in cinfo.matched_acquisitions) == spending_amount
    assert cinfo.is_complete is True
    assert cinfo.matched_acquisitions[0].amount == spending_amount
    assert cinfo.matched_acquisitions[0].event.amount == FVal(5)
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO

    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'the buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_sell_more_than_bought_within_year(accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467478304,  # bit after 31/06/2016
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('0'))
    assert cinfo.taxable_bought_cost.is_close(FVal('880.55'))
    assert len(cinfo.matched_acquisitions) == 2
    matched_sum = sum(x.amount for x in cinfo.matched_acquisitions)
    assert matched_sum < spending_amount
    assert cinfo.is_complete is False
    assert cinfo.matched_acquisitions[0].amount == ONE
    assert cinfo.matched_acquisitions[0].event.amount == ONE
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO
    assert cinfo.matched_acquisitions[1].amount == ONE
    assert cinfo.matched_acquisitions[1].event.amount == ONE
    assert cinfo.matched_acquisitions[1].event.remaining_amount == ZERO

    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'only buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_sell_more_than_bought_after_year(accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1523399409,  # 10/04/2018
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    assert cinfo.taxable_amount == 1, '1 out of 3 should be taxable (after a year)'
    assert cinfo.taxfree_bought_cost.is_close(FVal('880.55'))
    assert cinfo.taxable_bought_cost.is_close(FVal('0'))
    assert len(cinfo.matched_acquisitions) == 2
    matched_sum = sum(x.amount for x in cinfo.matched_acquisitions)
    assert matched_sum < spending_amount
    assert cinfo.is_complete is False
    assert cinfo.matched_acquisitions[0].amount == ONE
    assert cinfo.matched_acquisitions[0].event.amount == ONE
    assert cinfo.matched_acquisitions[0].event.remaining_amount == ZERO
    assert cinfo.matched_acquisitions[1].amount == ONE
    assert cinfo.matched_acquisitions[1].event.amount == ONE
    assert cinfo.matched_acquisitions[1].event.remaining_amount == ZERO

    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'only buy should have been used'


def test_reduce_asset_amount(accountant):
    asset = A_ETH
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=FVal(3),  # 25/10/2016
            timestamp=1477378304,
            rate=FVal(603.415),
            index=3,
        ),
    )

    assert cost_basis.reduce_asset_amount(asset=asset, amount=FVal(1.5), timestamp=0)
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    acquisitions_num = len(acquisitions)
    assert acquisitions_num == 2, '1 buy should be used'
    remaining_amount = acquisitions[0].remaining_amount
    assert remaining_amount == FVal(0.5), '0.5 of 2nd buy should remain'

    # make sure same thing works for WETH
    equivalent_events = cost_basis.get_events(A_WETH)
    assert equivalent_events.acquisitions_manager.get_acquisitions()[0].remaining_amount == FVal(0.5)  # noqa: E501


def test_reduce_asset_amount_exact(accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )

    assert cost_basis.reduce_asset_amount(asset, FVal(2), 0)
    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'all buys should be used'


def test_reduce_asset_amount_not_bought(accountant):
    asset = 'BTC'
    assert not accountant.pots[0].cost_basis.reduce_asset_amount(asset, FVal(3), 0)


def test_reduce_asset_amount_more_than_bought(accountant):
    asset = A_ETH
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_acquisition(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            index=2,
        ),
    )

    # Also reduce WETH, to make sure it's counted same as ETH
    assert not cost_basis.reduce_asset_amount(A_WETH, FVal(3), 0)
    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'all buys should be used'


def test_accounting_lifo_order(accountant):
    asset = A_ETH
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.LIFO))
    asset_events = cost_basis.get_events(asset)
    # first we do a simple test that from 2 events the second is used
    event1 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    event2 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=2,
        rate=ONE,
        index=2,
    )
    asset_events.acquisitions_manager.add_acquisition(event1)
    asset_events.acquisitions_manager.add_acquisition(event2)
    assert cost_basis.reduce_asset_amount(A_ETH, ONE, 0)
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 1 and acquisitions[0] == event1
    # then test to reset
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.LIFO))
    asset_events = cost_basis.get_events(asset)
    # checking what happens if one of the events has non-zero remaining_amount
    event3 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=1,
        rate=ONE,
        index=1,
    )
    event4 = AssetAcquisitionEvent(
        amount=FVal(5),
        timestamp=2,
        rate=ONE,
        index=2,
    )
    asset_events.acquisitions_manager.add_acquisition(event3)
    asset_events.acquisitions_manager.add_acquisition(event4)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=3,
        spending_asset=asset,
        timestamp=1,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert acquisitions[0].remaining_amount == FVal(2) and acquisitions[1] == event3
    # checking that new event after processing previous is added properly
    event5 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event5)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=4,
        spending_asset=asset,
        timestamp=2,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 1 and acquisitions[0].amount == FVal(2) and acquisitions[0].remaining_amount == ONE  # noqa: E501
    # check what happens if we use all remaining events
    event6 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event6)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=asset,
        timestamp=3,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 0
    # check what happens if we try to use more than available
    event7 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event7)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=asset,
        timestamp=4,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is False
    assert cost_basis.missing_acquisitions == [
        MissingAcquisition(
            asset=A_ETH,
            time=4,
            found_amount=ONE,
            missing_amount=ONE,
        ),
    ]


def test_accounting_simple_hifo_order(accountant):
    """A simple test that checks that from 2 events the one with the highest amount is used."""
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.HIFO))
    asset_events = cost_basis.get_events(asset)
    event1 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=1,
        rate=ONE,
        index=1,
    )
    event2 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=2,
        rate=FVal(1.5),
        index=2,
    )
    asset_events.acquisitions_manager.add_acquisition(event1)
    asset_events.acquisitions_manager.add_acquisition(event2)
    assert cost_basis.reduce_asset_amount(asset, FVal(0.5), 0) is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 2 and acquisitions[0] == event2 and acquisitions[1] == event1


def test_accounting_hifo_order(accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.HIFO))
    asset_events = cost_basis.get_events(asset)
    # checking that cost basis is correct if one of the events has non-zero remaining_amount
    event3 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=1,
        rate=FVal(3),
        index=1,
    )
    event4 = AssetAcquisitionEvent(
        amount=FVal(5),
        timestamp=2,
        rate=ONE,
        index=2,
    )
    asset_events.acquisitions_manager.add_acquisition(event3)
    asset_events.acquisitions_manager.add_acquisition(event4)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=1,
        spending_asset=asset,
        timestamp=1,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert acquisitions[0].remaining_amount == ONE and acquisitions[1] == event4
    # check that adding a new event after processing the previous one is added properly
    event5 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=FVal(2),
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event5)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=6,
        spending_asset=asset,
        timestamp=2,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 1 and acquisitions[0].amount == FVal(5) and acquisitions[0].remaining_amount == ONE  # noqa: E501
    # check that using all remaining events uses up all acquisitions
    event6 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event6)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=asset,
        timestamp=3,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 0
    # check that using more than available creates MissingAcquisition
    event7 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=1,
        rate=ONE,
        index=1,
    )
    asset_events.acquisitions_manager.add_acquisition(event7)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=asset,
        timestamp=4,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is False
    assert cost_basis.missing_acquisitions == [
        MissingAcquisition(
            asset=asset,
            time=4,
            found_amount=ONE,
            missing_amount=ONE,
        ),
    ]


def test_missing_acquisitions(accountant):
    """Test that missing acquisitions are added properly by
    reduce_asset_amount and calculate_spend_cost_basis
    """
    expected_missing_acquisitions = []
    cost_basis = accountant.pots[0].cost_basis
    all_events = cost_basis.get_events(A_ETH)
    # Test when there are no documented acquisitions
    cost_basis.reduce_asset_amount(
        asset=A_ETH,
        amount=1,
        timestamp=1,
    )
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    all_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=1,
        spending_asset=A_ETH,
        timestamp=1,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=all_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        asset=A_ETH,
        missing_amount=1,
        found_amount=0,
        time=1,
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    # Test when there are documented acquisitions (1 in this case)
    all_events.acquisitions_manager.add_acquisition(AssetAcquisitionEvent(
        amount=2,
        rate=1,
        index=1,
        timestamp=2,
    ))
    cost_basis.reduce_asset_amount(
        asset=A_ETH,
        amount=3,
        timestamp=3,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        asset=A_ETH,
        missing_amount=1,
        found_amount=2,
        time=3,
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    all_events.acquisitions_manager.add_acquisition(AssetAcquisitionEvent(
        amount=2,
        rate=1,
        index=2,
        timestamp=3,
    ))
    all_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=3,
        spending_asset=A_ETH,
        timestamp=4,
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=all_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        asset=A_ETH,
        missing_amount=1,
        found_amount=2,
        time=4,
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions


@pytest.mark.parametrize('db_settings', [
    {'cost_basis_method': CostBasisMethod.ACB},
])
def test_accounting_average_cost_basis(accountant):
    """Test various scenarios in average cost basis calculation"""
    pot = accountant.pots[0]
    events = pot.processed_events
    cost_basis = pot.cost_basis
    manager = cost_basis.get_events(A_ETH).acquisitions_manager

    # Step 1. Add an acquisition
    add_acquisition(pot, amount=FVal(2), price=FVal(10))  # Buy 2 ETH for $10  total acb: $20
    assert events[0].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb = events[0].price * events[0].free_amount
    current_amount = events[0].free_amount  # 2
    assert manager.current_total_acb == current_total_acb == FVal(20)
    assert manager.current_amount == current_amount == FVal(2)

    # Step 2. Add a spend with positive pnl
    add_spend(pot, amount=FVal(1), price=FVal(15))  # Sell 1 ETH for $15  pnl: 1 * (15 - 10) = $5
    assert events[1].pnl.taxable == events[1].taxable_amount * (events[1].price - current_total_acb / current_amount) == FVal(5)  # noqa: E501
    current_total_acb *= (current_amount - events[1].taxable_amount) / current_amount  # total acb: 20 * (2 - 1) / 2 = $10  # noqa: E501
    current_amount -= events[1].taxable_amount  # 1
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == FVal(1)

    # Step 3. Add another acquisition
    add_acquisition(pot, amount=FVal(1), price=FVal(30))  # Buy 1 ETH for $30  total acb: 10 + 1 * 30 = $40  # noqa: E501
    assert events[2].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[2].price * events[2].free_amount
    current_amount += events[2].free_amount  # 2
    assert manager.current_total_acb == current_total_acb == FVal(40)
    assert manager.current_amount == current_amount == FVal(2)

    # Step 4. Add a spend with negative pnl
    add_spend(pot, amount=FVal(1.5), price=FVal(10))  # Sell 1.5 ETH for $10  pnl: 1.5 * (10 - 20) = -$15  # noqa: E501
    assert events[3].pnl.taxable == events[3].taxable_amount * (events[3].price - current_total_acb / current_amount) == FVal(-15)  # noqa: E501
    current_total_acb *= (current_amount - events[3].taxable_amount) / current_amount  # total acb: 40 * (2 - 1.5) / 2 = $10  # noqa: E501
    current_amount -= events[3].taxable_amount  # 0.5
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == FVal(0.5)

    # Step 5. Add another acquisition
    add_acquisition(pot, amount=FVal(3), price=FVal(20))  # Buy 3 ETH for $20  total acb: 10 + 3 * 20 = $70  # noqa: E501
    assert events[4].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[4].price * events[4].free_amount
    current_amount += events[4].free_amount  # 3.5
    assert manager.current_total_acb == current_total_acb == FVal(70)
    assert manager.current_amount == current_amount == FVal(3.5)

    # Step 6. Add a spend after a sequence of acquisitions and spends
    add_spend(pot, amount=FVal(2), price=FVal(30))  # Sell 2 ETH for $30  pnl: 2 * (30 - 20) = $20
    assert events[5].pnl.taxable == events[5].taxable_amount * (events[5].price - current_total_acb / current_amount) == FVal(20)  # noqa: E501
    current_total_acb *= (current_amount - events[5].taxable_amount) / current_amount  # total acb: 70 * (3.5 - 2) / 3.5 = $30 # noqa: E501
    current_amount -= events[5].taxable_amount  # 1.5
    assert manager.current_total_acb == current_total_acb == FVal(30)
    assert manager.current_amount == current_amount == FVal(1.5)

    # Step 7. Check that spending up the entire remaining amount works.
    add_spend(pot, amount=FVal(1.5), price=FVal(10))  # Sell 1.5 ETH for $10 pnl: 1.5*10 - (30/1.5)*1.5 = -$15 # noqa: E501
    assert events[6].pnl.taxable == events[6].taxable_amount * (events[6].price - current_total_acb / current_amount) == FVal(-15)  # noqa: E501
    current_total_acb *= (current_amount - events[6].taxable_amount) / current_amount  # total acb: 30 * (1.5 - 1.5) / 1.5 = $0  # noqa: E501
    current_amount -= events[6].taxable_amount  # 0
    assert manager.current_total_acb == current_total_acb == ZERO
    assert manager.current_amount == current_amount == ZERO

    # Step 8. Add one more acquisition
    add_acquisition(pot, amount=FVal(1), price=FVal(10))  # Buy 1 ETH for $10  total acb: 0 + 1 * 10 = $10  # noqa: E501
    assert events[7].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[7].price * events[7].free_amount
    current_amount += events[7].free_amount  # 1
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == FVal(1)

    # Step 9. Check that negative pnl is correctly handled
    add_spend(pot, amount=FVal(0.5), price=FVal(5))  # Sell 0.5 ETH for $5  pnl: 0.5 * (5 - 10) = -$2.5  # noqa: E501
    assert events[8].pnl.taxable == events[8].taxable_amount * (events[8].price - current_total_acb / current_amount) == FVal(-2.5)  # noqa: E501
    current_total_acb *= (current_amount - events[8].taxable_amount) / current_amount  # total acb: 10 * (1 - 0.5) / 1 = $5  # noqa: E501
    current_amount -= events[8].taxable_amount  # 0.5
    assert manager.current_total_acb == current_total_acb == FVal(5)
    assert manager.current_amount == current_amount == FVal(0.5)

    # Step 10. Try to spend more than the remaining amount
    add_spend(pot, amount=FVal(0.6), price=FVal(5))  # Sell 0.6 ETH for $5
    # pnl -> pnl_for_known_acquisition + pnl_for_rest_uses_full_price_as_profit
    # pnl -> 0.5*5 - (5/0.5)*0.5 + 0.1 * 5 = -2$
    assert len(cost_basis.missing_acquisitions) == 1
    missing_acquisition = cost_basis.missing_acquisitions[0]
    assert missing_acquisition.found_amount == current_amount == FVal(0.5)
    assert missing_acquisition.missing_amount == events[9].taxable_amount - current_amount == FVal(0.1)  # 0.6 - 0.5  # noqa: E501
    assert events[9].pnl.taxable == missing_acquisition.found_amount * (events[9].price - current_total_acb / current_amount) + missing_acquisition.missing_amount * events[9].price == FVal(-2)  # noqa: E501
    assert manager.current_total_acb == ZERO
    assert manager.current_amount == ZERO

    # Step 11. Try to spend when remaining amount is 0 (missing acquisition counts all as profit)
    add_spend(pot, amount=FVal(0.5), price=FVal(5))  # Sell 0.5 ETH for $5  pnl: 0.5 * 5 = $2.5  # noqa: E501
    assert len(cost_basis.missing_acquisitions) == 2
    missing_acquisition = cost_basis.missing_acquisitions[1]
    assert missing_acquisition.found_amount == ZERO
    assert missing_acquisition.missing_amount == events[10].taxable_amount == FVal(0.5)
    assert events[10].pnl.taxable == missing_acquisition.missing_amount * events[10].price == FVal(2.5)  # noqa: E501
    assert manager.current_total_acb == ZERO
    assert manager.current_amount == ZERO

    # Also check that the values in the exported csv match the processed events list.
    # In case of ACB export cost basis values are pure numbers, with no formulas, so we can check
    # like this.
    with tempfile.TemporaryDirectory() as tmpdir:
        path_dir = Path(tmpdir)
        accountant.csvexporter.export(
            events=pot.processed_events,
            pnls=pot.pnls,
            directory=path_dir,
        )
        with open(path_dir / FILENAME_ALL_CSV) as f:
            for event, row in zip_longest(events, csv.DictReader(f)):
                if event.cost_basis is None:
                    assert row['cost_basis_taxable'] == ''
                else:
                    if row['cost_basis_taxable'] == '':
                        value = ZERO
                    else:
                        value = FVal(row['cost_basis_taxable'])

                    assert value == event.cost_basis.taxable_bought_cost


@pytest.mark.parametrize('mocked_price_queries', [{
    A_ETH: {A_EUR: {1469020840: ONE}},
    A_3CRV: {A_EUR: {1469020840: ONE}},
}])
@pytest.mark.parametrize('taxable', [True, False])
def test_swaps_taxability(accountant: Accountant, taxable: bool) -> None:
    """Check taxable parameter works and acquisition part of swaps doesn't count as taxable."""
    pot = accountant.pots[0]
    event_accountant = pot.events_accountant
    event_accountant._process_swap(
        timestamp=Timestamp(1469020840),
        out_event=EvmEvent(
            tx_hash=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=TimestampMS(146902084000),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_ETH,
            balance=Balance(amount=ONE, usd_value=ONE),
            notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=CPT_UNISWAP_V2,
        ),
        in_event=EvmEvent(
            tx_hash=make_evm_tx_hash(),
            sequence_index=2,
            timestamp=TimestampMS(1469020840),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_3CRV,
            balance=Balance(amount=ONE, usd_value=ONE),
            notes='Receive 462.967761432322996701 3CRV in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty=CPT_UNISWAP_V2,
        ),
        event_settings=TxEventSettings(
            taxable=taxable,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
            method='spend',
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        general_extra_data={},
    )
    if taxable is True:
        expected_pnl_taxable = ONE
        expected_pnl_totals = PnlTotals(
            totals={AccountingEventType.TRANSACTION_EVENT: PNL(taxable=ONE)},
        )
    else:
        expected_pnl_taxable = ZERO
        expected_pnl_totals = PnlTotals()

    assert pot.pnls == expected_pnl_totals
    assert len(pot.processed_events) == 2
    assert pot.processed_events[0].taxable_amount == ONE
    assert pot.processed_events[0].free_amount == ZERO
    # Check that dependping on whether is taxable or not, we see different values for spend event
    assert pot.processed_events[0].pnl.taxable == expected_pnl_taxable
    assert pot.processed_events[0].pnl.free == ZERO
    # Check that no matter whether taxable flag is True or not, acquisitions are never taxable
    assert pot.processed_events[1].taxable_amount == ZERO
    assert pot.processed_events[1].free_amount == ONE
    assert pot.processed_events[1].pnl.taxable == ZERO
    assert pot.processed_events[1].pnl.free == ZERO


@pytest.mark.parametrize('mocked_price_queries', [{A_ETH: {A_EUR: {1469020840: ONE}}}])
def test_taxable_acquisition(accountant: Accountant) -> None:
    """Make sure that taxable acquisitions are processed properly"""
    pot = accountant.pots[0]
    pot.add_acquisition(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
        location=Location.BLOCKCHAIN,
        timestamp=Timestamp(1469020840),
        asset=A_ETH,
        amount=ONE,
        taxable=True,
    )
    expected_pnl_totals = PnlTotals(
        totals={AccountingEventType.TRANSACTION_EVENT: PNL(taxable=ONE)},
    )
    assert pot.pnls == expected_pnl_totals
    assert len(pot.processed_events) == 1
    assert pot.processed_events[0].taxable_amount == ONE
    assert pot.processed_events[0].free_amount == ZERO
    assert pot.processed_events[0].pnl.taxable == ONE
    assert pot.processed_events[0].pnl.free == ZERO


@pytest.mark.parametrize('mocked_price_queries', [{
    A_ETH: {
        A_EUR: {
            1677593073: FVal(50),
            1677593074: FVal(120),
            1677593075: FVal(130),
            1677593076: FVal(90),
        },
    },
}])
@pytest.mark.parametrize(('db_settings', 'expected_pnls'), [
    (
        {'cost_basis_method': CostBasisMethod.FIFO, 'include_fees_in_cost_basis': False},
        [ZERO, ZERO, FVal(-10), FVal(3500), ZERO, FVal(-10), ZERO, ZERO, FVal(-10), FVal(1600), ZERO, FVal(-10)],  # noqa: E501
    ),
    (
        {'cost_basis_method': CostBasisMethod.ACB, 'include_fees_in_cost_basis': True},
        [ZERO, ZERO, ZERO, FVal(3485), ZERO, ZERO, ZERO, ZERO, ZERO, FVal(-16), ZERO, ZERO],
    ),
])
def test_fees(accountant: 'Accountant', expected_pnls: list[FVal]):
    """
    Tests that fees are properly either calculated as standalone events or included in the price.
    Values for the example are taken from the Canada example from this issue comment
    https://github.com/rotki/rotki/issues/5561#issuecomment-1423338938.
    """
    history = [
        Trade(
            timestamp=Timestamp(1677593073),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(100)),
            rate=Price(FVal(50)),
            fee=Fee(FVal(10)),
            fee_currency=A_EUR,
            notes='Trade 1',
        ), Trade(
            timestamp=Timestamp(1677593074),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(50)),
            rate=Price(FVal(120)),
            fee=Fee(FVal(10)),
            fee_currency=A_EUR,
            notes='Trade 2',
        ), Trade(
            timestamp=Timestamp(1677593075),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(50)),
            rate=Price(FVal(130)),
            fee=Fee(FVal(10)),
            fee_currency=A_EUR,
            notes='Trade 3',
        ), Trade(
            timestamp=Timestamp(1677593076),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(40)),
            rate=Price(FVal(90)),
            fee=Fee(FVal(10)),
            fee_currency=A_EUR,
            notes='Trade 4',
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1677593077),
        history_list=history,  # type: ignore[arg-type]  # invariant problem
    )
    for event, expected_pnl in zip(accountant.pots[0].processed_events, expected_pnls):
        assert event.pnl.taxable == expected_pnl
