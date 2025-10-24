import csv
import tempfile
from itertools import zip_longest
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis import AssetAcquisitionEvent
from rotkehlchen.accounting.export.csv import FILENAME_ALL_CSV, CSVExporter
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.types import MissingAcquisition
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_3CRV, A_BTC, A_ETH, A_EUR, A_WETH
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import accounting_history_process
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    AssetAmount,
    CostBasisMethod,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.accounting.cost_basis.base import AverageCostBasisMethod
    from rotkehlchen.db.dbhandler import DBHandler


EXAMPLE_TIMESTAMP = Timestamp(1675483017)
ONE_PRICE = Price(ONE)


def add_in_event(
        pot: AccountingPot,
        amount: FVal,
        asset: Asset = A_ETH,
        price: Price = ONE_PRICE,
        taxable: bool = False,
):
    """
    Util function to add an acquisition to an accounting pot.
    Timestamp doesn't matter here since we provide `given_price`, but has to be big enough so that
    `handle_prefork_acquisitions` is not called.
    """
    pot.add_in_event(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Test',
        location=Location.BLOCKCHAIN,
        timestamp=EXAMPLE_TIMESTAMP,
        asset=asset,
        amount=amount,
        taxable=taxable,
        given_price=price,
    )


def add_out_event(
        pot: AccountingPot,
        amount: FVal,
        asset: Asset = A_ETH,
        price: Price = ONE_PRICE,
        taxable: bool = True,
):
    """
    Util function to add a spend event to an accounting pot.
    Timestamp doesn't matter here since we provide `given_price`, but has to be big enough so that
    `handle_prefork_acquisitions` is not called.
    """
    pot.add_out_event(
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
def test_calculate_spend_cost_basis_after_year(accountant: Accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(15),
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(3),  # 25/10/2016
            timestamp=Timestamp(1477378304),
            rate=Price(FVal(603.415)),
            index=3,
        ),
    )

    spending_amount = FVal(8)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1480683904),  # 02/12/2016
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


def test_calculate_spend_cost_basis_1_buy_consumed_by_1_sell(accountant: Accountant):
    """ Assert bought_cost is correct when 1 buy is completely consumed by 1 sell

    Regression test for part of https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )

    spending_amount = FVal(5)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1467378304),  # 31/06/2016
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


def test_calculate_spend_cost_basis1_buy_used_by_2_sells_taxable(accountant: Accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxable part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1467378304),  # 31/06/2016
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
        timestamp=Timestamp(1467378404),  # bit after previous sell
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
def test_calculate_spend_cost_basis_1_buy_used_by_2_sells_taxfree(accountant: Accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxfree part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(5),
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1480683904),  # 02/12/2016
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
        timestamp=Timestamp(1480683954),  # bit after previous sell
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
def test_calculate_spend_cost_basis_sell_more_than_bought_within_year(accountant: Accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1467478304),  # bit after 31/06/2016
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
def test_calculate_spend_cost_basis_sell_more_than_bought_after_year(accountant: Accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )

    spending_amount = FVal(3)
    cinfo = asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=Timestamp(1523399409),  # 10/04/2018
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


def test_reduce_asset_amount(accountant: Accountant):
    asset = A_ETH
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=FVal(3),  # 25/10/2016
            timestamp=Timestamp(1477378304),
            rate=Price(FVal(603.415)),
            index=3,
        ),
    )

    assert cost_basis.reduce_asset_amount(
        originating_event_id=None,  # not relevant
        asset=asset,
        amount=FVal(1.5),
        timestamp=Timestamp(0),
    )
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    acquisitions_num = len(acquisitions)
    assert acquisitions_num == 2, '1 buy should be used'
    remaining_amount = acquisitions[0].remaining_amount
    assert remaining_amount == FVal(0.5), '0.5 of 2nd buy should remain'

    # make sure same thing works for WETH
    equivalent_events = cost_basis.get_events(A_WETH)
    assert equivalent_events.acquisitions_manager.get_acquisitions()[0].remaining_amount == FVal(0.5)  # noqa: E501


def test_reduce_asset_amount_exact(accountant: Accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(asset)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )

    assert cost_basis.reduce_asset_amount(None, asset, FVal(2), Timestamp(0))
    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'all buys should be used'


def test_reduce_asset_amount_not_bought(accountant: Accountant):
    assert not accountant.pots[0].cost_basis.reduce_asset_amount(None, A_BTC, FVal(3), Timestamp(0))  # noqa: E501


def test_reduce_asset_amount_more_than_bought(accountant: Accountant):
    cost_basis = accountant.pots[0].cost_basis
    asset_events = cost_basis.get_events(A_ETH)
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1446979735),  # 08/11/2015
            rate=Price(FVal(268.1)),
            index=1,
        ),
    )
    asset_events.acquisitions_manager.add_in_event(
        AssetAcquisitionEvent(
            amount=ONE,
            timestamp=Timestamp(1467378304),  # 31/06/2016
            rate=Price(FVal(612.45)),
            index=2,
        ),
    )

    # Also reduce WETH, to make sure it's counted same as ETH
    assert not cost_basis.reduce_asset_amount(None, A_WETH, FVal(3), Timestamp(0))
    acquisitions_num = len(asset_events.acquisitions_manager)
    assert acquisitions_num == 0, 'all buys should be used'


def test_accounting_lifo_order(accountant: Accountant):
    asset = A_ETH
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.LIFO))
    asset_events = cost_basis.get_events(asset)
    base_ts = Timestamp(1614556800)  # 01/03/2021, changed from 1 for windows. See https://github.com/rotki/rotki/pull/6398#discussion_r1271323846 # noqa: E501
    # first we do a simple test that from 2 events the second is used
    event1 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    event2 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=Timestamp(base_ts + 10),
        rate=ONE_PRICE,
        index=2,
    )
    asset_events.acquisitions_manager.add_in_event(event1)
    asset_events.acquisitions_manager.add_in_event(event2)
    assert cost_basis.reduce_asset_amount(None, A_ETH, ONE, Timestamp(0))
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 1 and acquisitions[0] == event1
    # then test to reset
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.LIFO))
    asset_events = cost_basis.get_events(asset)
    # checking what happens if one of the events has non-zero remaining_amount
    event3 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    event4 = AssetAcquisitionEvent(
        amount=FVal(5),
        timestamp=Timestamp(base_ts + 10),
        rate=ONE_PRICE,
        index=2,
    )
    asset_events.acquisitions_manager.add_in_event(event3)
    asset_events.acquisitions_manager.add_in_event(event4)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=FVal(3),
        spending_asset=asset,
        timestamp=Timestamp(1),
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
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event5)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=FVal(4),
        spending_asset=asset,
        timestamp=Timestamp(2),
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
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event6)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=Timestamp(3),
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
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event7)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        originating_event_id=(originating_event_id := 424242),
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=Timestamp(4),
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is False
    assert cost_basis.missing_acquisitions == [
        MissingAcquisition(
            originating_event_id=originating_event_id,
            asset=A_ETH,
            time=Timestamp(4),
            found_amount=ONE,
            missing_amount=ONE,
        ),
    ]


def test_accounting_simple_hifo_order(accountant: Accountant):
    """A simple test that checks that from 2 events the one with the highest amount is used."""
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.HIFO))
    asset_events = cost_basis.get_events(asset)
    event1 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=Timestamp(1),
        rate=ONE_PRICE,
        index=1,
    )
    event2 = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=Timestamp(2),
        rate=Price(FVal(1.5)),
        index=2,
    )
    asset_events.acquisitions_manager.add_in_event(event1)
    asset_events.acquisitions_manager.add_in_event(event2)
    assert cost_basis.reduce_asset_amount(None, asset, FVal(0.5), Timestamp(0)) is True
    acquisitions = asset_events.acquisitions_manager.get_acquisitions()
    assert len(acquisitions) == 2 and acquisitions[0] == event2 and acquisitions[1] == event1


def test_accounting_hifo_order(accountant: Accountant):
    asset = A_BTC
    cost_basis = accountant.pots[0].cost_basis
    cost_basis.reset(DBSettings(cost_basis_method=CostBasisMethod.HIFO))
    asset_events = cost_basis.get_events(asset)
    base_ts = Timestamp(1614556800)  # 01/03/2021, changed from 1 for windows. See https://github.com/rotki/rotki/pull/6398#discussion_r1271323846 # noqa: E501
    # checking that cost basis is correct if one of the events has non-zero remaining_amount
    event3 = AssetAcquisitionEvent(
        amount=FVal(2),
        timestamp=base_ts,
        rate=Price(FVal(3)),
        index=1,
    )
    event4 = AssetAcquisitionEvent(
        amount=FVal(5),
        timestamp=Timestamp(base_ts + 10),
        rate=ONE_PRICE,
        index=2,
    )
    asset_events.acquisitions_manager.add_in_event(event3)
    asset_events.acquisitions_manager.add_in_event(event4)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=ONE,
        spending_asset=asset,
        timestamp=Timestamp(1),
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
        timestamp=base_ts,
        rate=Price(FVal(2)),
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event5)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=FVal(6),
        spending_asset=asset,
        timestamp=Timestamp(2),
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
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event6)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=Timestamp(3),
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
        timestamp=base_ts,
        rate=ONE_PRICE,
        index=1,
    )
    asset_events.acquisitions_manager.add_in_event(event7)
    assert asset_events.acquisitions_manager.calculate_spend_cost_basis(
        originating_event_id=(originating_event_id := 6464),
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=Timestamp(4),
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=asset_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    ).is_complete is False
    assert cost_basis.missing_acquisitions == [
        MissingAcquisition(
            originating_event_id=originating_event_id,
            asset=asset,
            time=Timestamp(4),
            found_amount=ONE,
            missing_amount=ONE,
        ),
    ]


def test_missing_acquisitions(accountant: Accountant):
    """Test that missing acquisitions are added properly by
    reduce_asset_amount and calculate_spend_cost_basis
    """
    expected_missing_acquisitions: list[MissingAcquisition] = []
    cost_basis = accountant.pots[0].cost_basis
    all_events = cost_basis.get_events(A_ETH)
    base_ts = 1614556800  # 01/03/2021, changed from 1 for windows. See https://github.com/rotki/rotki/pull/6398#discussion_r1271323846 # noqa: E501
    # Test when there are no documented acquisitions
    cost_basis.reduce_asset_amount(
        originating_event_id=None,
        asset=A_ETH,
        amount=ONE,
        timestamp=Timestamp(1),
    )
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    all_events.acquisitions_manager.calculate_spend_cost_basis(
        originating_event_id=(originating_event_id := 6969),
        spending_amount=ONE,
        spending_asset=A_ETH,
        timestamp=Timestamp(1),
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=all_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        originating_event_id=originating_event_id,
        asset=A_ETH,
        missing_amount=ONE,
        found_amount=ZERO,
        time=Timestamp(1),
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    # Test when there are documented acquisitions (1 in this case)
    all_events.acquisitions_manager.add_in_event(AssetAcquisitionEvent(
        amount=FVal(2),
        rate=ONE_PRICE,
        index=1,
        timestamp=Timestamp(base_ts + 10),
    ))
    cost_basis.reduce_asset_amount(
        None,
        asset=A_ETH,
        amount=FVal(3),
        timestamp=Timestamp(3),
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        originating_event_id=None,
        asset=A_ETH,
        missing_amount=ONE,
        found_amount=FVal(2),
        time=Timestamp(3),
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
    all_events.acquisitions_manager.add_in_event(AssetAcquisitionEvent(
        amount=FVal(2),
        rate=ONE_PRICE,
        index=2,
        timestamp=Timestamp(base_ts + 20),
    ))
    all_events.acquisitions_manager.calculate_spend_cost_basis(
        originating_event_id=(originating_event_id := 8989),
        spending_amount=FVal(3),
        spending_asset=A_ETH,
        timestamp=Timestamp(4),
        missing_acquisitions=cost_basis.missing_acquisitions,
        used_acquisitions=all_events.used_acquisitions,
        settings=cost_basis.settings,
        timestamp_to_date=cost_basis.timestamp_to_date,
        average_cost_basis=None,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        originating_event_id=originating_event_id,
        asset=A_ETH,
        missing_amount=ONE,
        found_amount=FVal(2),
        time=Timestamp(4),
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions


@pytest.mark.parametrize('db_settings', [
    {'cost_basis_method': CostBasisMethod.ACB},
])
def test_accounting_average_cost_basis(accountant: Accountant):
    """Test various scenarios in average cost basis calculation"""
    pot = accountant.pots[0]
    events = pot.processed_events
    cost_basis = pot.cost_basis
    manager = cast('AverageCostBasisMethod', cost_basis.get_events(A_ETH).acquisitions_manager)

    # Step 1. Add an acquisition
    add_in_event(pot, amount=FVal(2), price=Price(FVal(10)))  # Buy 2 ETH for $10  total acb: $20
    assert events[0].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb = events[0].price * events[0].free_amount
    current_amount = events[0].free_amount  # 2
    assert manager.current_total_acb == current_total_acb == FVal(20)
    assert manager.current_amount == current_amount == FVal(2)

    # Step 2. Add a spend with positive pnl
    add_out_event(pot, amount=ONE, price=Price(FVal(15)))  # Sell 1 ETH for $15  pnl: 1 * (15 - 10) = $5  # noqa: E501
    assert events[1].pnl.taxable == events[1].taxable_amount * (events[1].price - current_total_acb / current_amount) == FVal(5)  # noqa: E501
    current_total_acb *= (current_amount - events[1].taxable_amount) / current_amount  # total acb: 20 * (2 - 1) / 2 = $10  # noqa: E501
    current_amount -= events[1].taxable_amount  # 1
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == ONE

    # Step 3. Add another acquisition
    add_in_event(pot, amount=ONE, price=Price(FVal(30)))  # Buy 1 ETH for $30  total acb: 10 + 1 * 30 = $40  # noqa: E501
    assert events[2].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[2].price * events[2].free_amount
    current_amount += events[2].free_amount  # 2
    assert manager.current_total_acb == current_total_acb == FVal(40)
    assert manager.current_amount == current_amount == FVal(2)

    # Step 4. Add a spend with negative pnl
    add_out_event(pot, amount=FVal(1.5), price=Price(FVal(10)))  # Sell 1.5 ETH for $10  pnl: 1.5 * (10 - 20) = -$15  # noqa: E501
    assert events[3].pnl.taxable == events[3].taxable_amount * (events[3].price - current_total_acb / current_amount) == FVal(-15)  # noqa: E501
    current_total_acb *= (current_amount - events[3].taxable_amount) / current_amount  # total acb: 40 * (2 - 1.5) / 2 = $10  # noqa: E501
    current_amount -= events[3].taxable_amount  # 0.5
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == FVal(0.5)

    # Step 5. Add another acquisition
    add_in_event(pot, amount=FVal(3), price=Price(FVal(20)))  # Buy 3 ETH for $20  total acb: 10 + 3 * 20 = $70  # noqa: E501
    assert events[4].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[4].price * events[4].free_amount
    current_amount += events[4].free_amount  # 3.5
    assert manager.current_total_acb == current_total_acb == FVal(70)
    assert manager.current_amount == current_amount == FVal(3.5)

    # Step 6. Add a spend after a sequence of acquisitions and spends
    add_out_event(pot, amount=FVal(2), price=Price(FVal(30)))  # Sell 2 ETH for $30  pnl: 2 * (30 - 20) = $20  # noqa: E501
    assert events[5].pnl.taxable == events[5].taxable_amount * (events[5].price - current_total_acb / current_amount) == FVal(20)  # noqa: E501
    current_total_acb *= (current_amount - events[5].taxable_amount) / current_amount  # total acb: 70 * (3.5 - 2) / 3.5 = $30 # noqa: E501
    current_amount -= events[5].taxable_amount  # 1.5
    assert manager.current_total_acb == current_total_acb == FVal(30)
    assert manager.current_amount == current_amount == FVal(1.5)

    # Step 7. Check that spending up the entire remaining amount works.
    add_out_event(pot, amount=FVal(1.5), price=Price(FVal(10)))  # Sell 1.5 ETH for $10 pnl: 1.5*10 - (30/1.5)*1.5 = -$15 # noqa: E501
    assert events[6].pnl.taxable == events[6].taxable_amount * (events[6].price - current_total_acb / current_amount) == FVal(-15)  # noqa: E501
    current_total_acb *= (current_amount - events[6].taxable_amount) / current_amount  # total acb: 30 * (1.5 - 1.5) / 1.5 = $0  # noqa: E501
    current_amount -= events[6].taxable_amount  # 0
    assert manager.current_total_acb == current_total_acb == ZERO
    assert manager.current_amount == current_amount == ZERO

    # Step 8. Add one more acquisition
    add_in_event(pot, amount=ONE, price=Price(FVal(10)))  # Buy 1 ETH for $10  total acb: 0 + 1 * 10 = $10  # noqa: E501
    assert events[7].pnl.taxable == ZERO  # No profit for acquisitions
    current_total_acb += events[7].price * events[7].free_amount
    current_amount += events[7].free_amount  # 1
    assert manager.current_total_acb == current_total_acb == FVal(10)
    assert manager.current_amount == current_amount == ONE

    # Step 9. Check that negative pnl is correctly handled
    add_out_event(pot, amount=FVal(0.5), price=Price(FVal(5)))  # Sell 0.5 ETH for $5  pnl: 0.5 * (5 - 10) = -$2.5  # noqa: E501
    assert events[8].pnl.taxable == events[8].taxable_amount * (events[8].price - current_total_acb / current_amount) == FVal(-2.5)  # noqa: E501
    current_total_acb *= (current_amount - events[8].taxable_amount) / current_amount  # total acb: 10 * (1 - 0.5) / 1 = $5  # noqa: E501
    current_amount -= events[8].taxable_amount  # 0.5
    assert manager.current_total_acb == current_total_acb == FVal(5)
    assert manager.current_amount == current_amount == FVal(0.5)

    # Step 10. Try to spend more than the remaining amount
    add_out_event(pot, amount=FVal(0.6), price=Price(FVal(5)))  # Sell 0.6 ETH for $5
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
    add_out_event(pot, amount=FVal(0.5), price=Price(FVal(5)))  # Sell 0.5 ETH for $5  pnl: 0.5 * 5 = $2.5  # noqa: E501
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
        with open(path_dir / FILENAME_ALL_CSV, encoding='utf8') as f:
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
@pytest.mark.parametrize('include_crypto2crypto', [True, False])
def test_swaps_taxability(
        accountant: Accountant,
        taxable: bool,
        include_crypto2crypto: bool,
) -> None:
    """Check the complex taxability logic for swaps works correctly."""
    pot = accountant.pots[0]
    pot.settings.include_crypto2crypto = include_crypto2crypto
    event_accountant = pot.events_accountant
    event_accountant._process_swap(
        timestamp=Timestamp(1469020840),
        out_event=EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=TimestampMS(146902084000),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_ETH,
            amount=ONE,
            notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=CPT_UNISWAP_V2,
        ),
        in_event=EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=2,
            timestamp=TimestampMS(1469020840),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_3CRV,
            amount=ONE,
            notes='Receive 462.967761432322996701 3CRV in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty=CPT_UNISWAP_V2,
        ),
        fee_event=None,
        event_settings=BaseEventSettings(
            taxable=taxable,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        general_extra_data={},
    )
    if taxable and include_crypto2crypto:
        expected_taxable = ONE
        expected_free = ZERO
        expected_pnl_totals = PnlTotals(
            totals={AccountingEventType.TRANSACTION_EVENT: PNL(taxable=ONE)},
        )
    else:
        expected_taxable = ZERO
        expected_free = ONE
        expected_pnl_totals = PnlTotals()

    assert pot.pnls == expected_pnl_totals
    assert len(pot.processed_events) == 2

    # Check the spend event
    assert pot.processed_events[0].taxable_amount == expected_taxable
    assert pot.processed_events[0].free_amount == expected_free
    assert pot.processed_events[0].pnl.taxable == expected_taxable
    assert pot.processed_events[0].pnl.free == ZERO

    # Check the acquisition part - still never taxable regardless of settings
    assert pot.processed_events[1].taxable_amount == ZERO
    assert pot.processed_events[1].free_amount == ONE
    assert pot.processed_events[1].pnl.taxable == ZERO
    assert pot.processed_events[1].pnl.free == ZERO


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_event_specific_accounting_rules(accountant: Accountant) -> None:
    """Test that accounting rules tied to specific events override default rules."""
    pot = accountant.pots[0]
    pot.settings.include_crypto2crypto = True
    history, user = [], make_evm_address()
    for idx, (tx_hash, timestamp) in enumerate([
        (make_evm_tx_hash(), TimestampMS(1469020840000)),
        (make_evm_tx_hash(), TimestampMS(1569020840000)),
    ], start=1):
        history.extend([EvmSwapEvent(
            identifier=idx,
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            location_label=user,
            asset=A_ETH,
            amount=ONE,
            notes='Swap ETH in uniswap-v2',
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=CPT_UNISWAP_V2,
        ), EvmSwapEvent(
            identifier=idx + 1,
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            location_label=user,
            asset=A_3CRV,
            amount=ONE,
            notes='Receive 3CRV in uniswap-v2',
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty=CPT_UNISWAP_V2,
        )])
    with accountant.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(accountant.db).add_history_events(
            write_cursor=write_cursor,
            history=history,
        )
    DBAccountingRules(accountant.db).add_accounting_rule(
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=CPT_UNISWAP_V2,
        rule=BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
            accounting_treatment=TxAccountingTreatment.SWAP,
        ),
        links={},
        event_ids=[history[0].identifier],  # type: ignore[list-item]  # identifier is not None in this case
    )

    add_in_event(pot=pot, amount=FVal(50), price=Price(FVal(10)), taxable=True)
    accounting_history_process(
        accountant=accountant,
        start_ts=ts_ms_to_sec(history[0].timestamp),
        end_ts=ts_ms_to_sec(history[-1].timestamp),
        history_list=history,
    )

    # Only the second swap should be taxable (1 ETH gain)
    expected_pnl_totals = PnlTotals(
        totals={AccountingEventType.TRADE: PNL(taxable=ONE)},
    )

    assert pot.pnls == expected_pnl_totals
    assert len(pot.processed_events) == 4  # 2 swaps * 2 events each

    # First swap (non-taxable due to event-specific rule)
    assert pot.processed_events[0].pnl.taxable == ZERO
    assert pot.processed_events[0].pnl.free == ZERO
    assert pot.processed_events[1].pnl.taxable == ZERO
    assert pot.processed_events[1].pnl.free == ZERO

    # Second swap (taxable due to default rule)
    assert pot.processed_events[2].pnl.taxable == ONE
    assert pot.processed_events[2].pnl.free == ZERO
    assert pot.processed_events[3].pnl.taxable == ZERO
    assert pot.processed_events[3].pnl.free == ZERO


@pytest.mark.parametrize('mocked_price_queries', [{A_ETH: {A_EUR: {1469020840: ONE}}}])
def test_taxable_acquisition(accountant: Accountant) -> None:
    """Make sure that taxable acquisitions are processed properly"""
    pot = accountant.pots[0]
    pot.add_in_event(
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
        [ZERO, FVal(-10), ZERO, FVal(3500), ZERO, FVal(-10), ZERO, FVal(-10), ZERO, FVal(1600), ZERO, FVal(-10)],  # noqa: E501
    ),
    (
        {'cost_basis_method': CostBasisMethod.ACB, 'include_fees_in_cost_basis': True},
        [ZERO, ZERO, ZERO, FVal(3485), ZERO, ZERO, ZERO, ZERO, ZERO, FVal(-16), ZERO, ZERO],
    ),
])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_fees(accountant: 'Accountant', expected_pnls: list[FVal]):
    """
    Tests that fees are properly either calculated as standalone events or included in the price.
    Values for the example are taken from the Canada example from this issue comment
    https://github.com/rotki/rotki/issues/5561#issuecomment-1423338938.
    """
    history = [*create_swap_events(
        timestamp=TimestampMS(1677593073000),
        location=Location.EXTERNAL,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal(5000)),
        receive=AssetAmount(asset=A_ETH, amount=FVal(100)),
        fee=AssetAmount(asset=A_EUR, amount=FVal(10)),
    ), *create_swap_events(
        timestamp=TimestampMS(1677593074000),
        location=Location.EXTERNAL,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal(50)),
        receive=AssetAmount(asset=A_EUR, amount=FVal(6000)),
        fee=AssetAmount(asset=A_EUR, amount=FVal(10)),
    ), *create_swap_events(
        timestamp=TimestampMS(1677593075000),
        location=Location.EXTERNAL,
        event_identifier='3xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal(6500)),
        receive=AssetAmount(asset=A_ETH, amount=FVal(50)),
        fee=AssetAmount(asset=A_EUR, amount=FVal(10)),
    ), *create_swap_events(
        timestamp=TimestampMS(1677593076000),
        location=Location.EXTERNAL,
        event_identifier='4xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal(40)),
        receive=AssetAmount(asset=A_EUR, amount=FVal(3600)),
        fee=AssetAmount(asset=A_EUR, amount=FVal(10)),
    )]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1677593077),
        history_list=history,
    )
    for event, expected_pnl in zip(accountant.pots[0].processed_events, expected_pnls, strict=True):  # noqa: E501
        assert event.pnl.taxable == expected_pnl


@pytest.mark.parametrize('db_settings', [{'frontend_settings': '{"explorers":{"eth":{"transaction":"myexplorer.eth"}, "polygon_pos":{"transaction":"myexplorer.polygon"}}}'}])  # noqa: E501
def test_csv_exporter_settings(database: 'DBHandler') -> None:
    """
    Test that the user configuration for the tx explorer in CSV exporter
    is correctly picked
    """
    csv_exporter = CSVExporter(database)
    assert csv_exporter.transaction_explorers[SupportedBlockchain.ETHEREUM] == 'myexplorer.eth'
    assert csv_exporter.transaction_explorers[SupportedBlockchain.POLYGON_POS] == 'myexplorer.polygon'  # noqa: E501
