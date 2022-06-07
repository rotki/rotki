import pytest

from rotkehlchen.accounting.cost_basis import AssetAcquisitionEvent
from rotkehlchen.accounting.types import MissingAcquisition
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.types import CostBasisMethod


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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467378404,  # bit after previous sell
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1480683954,  # bit after previous sell
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1467478304,  # bit after 31/06/2016
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
    cinfo = cost_basis.calculate_spend_cost_basis(
        spending_amount=spending_amount,
        spending_asset=asset,
        timestamp=1523399409,  # 10/04/2018
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
    assert cost_basis.calculate_spend_cost_basis(
        spending_amount=3,
        spending_asset=A_ETH,
        timestamp=1,
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
    assert cost_basis.calculate_spend_cost_basis(
        spending_amount=4,
        spending_asset=A_ETH,
        timestamp=2,
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
    assert cost_basis.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=A_ETH,
        timestamp=3,
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
    assert cost_basis.calculate_spend_cost_basis(
        spending_amount=2,
        spending_asset=A_ETH,
        timestamp=4,
    ).is_complete is False
    assert cost_basis.missing_acquisitions == [
        MissingAcquisition(
            asset=A_ETH,
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
    cost_basis.calculate_spend_cost_basis(
        spending_asset=A_ETH,
        spending_amount=1,
        timestamp=1,
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
    cost_basis.calculate_spend_cost_basis(
        spending_asset=A_ETH,
        spending_amount=3,
        timestamp=4,
    )
    expected_missing_acquisitions.append(MissingAcquisition(
        asset=A_ETH,
        missing_amount=1,
        found_amount=2,
        time=4,
    ))
    assert cost_basis.missing_acquisitions == expected_missing_acquisitions
