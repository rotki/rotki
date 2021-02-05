import pytest

from rotkehlchen.accounting.cost_basis import AssetAcquisitionEvent
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Location


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_after_year(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(15),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(3),  # 25/10/2016
            timestamp=1477378304,
            rate=FVal(603.415),
            fee_rate=FVal(0.0017),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(8),
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
    )

    assert taxable_amount == 3, '3 out of 8 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('1340.5005'))
    assert taxable_bought_cost.is_close(FVal('1837.3557'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 2, 'first buy should have been used'
    remaining_amount = accountant.events.cost_basis.events[asset].acquisitions[0].amount
    assert remaining_amount == FVal(12), '3 of 15 should have been consumed'


def test_calculate_spend_cost_basis_1_buy_consumed_by_1_sell(accountant):
    """ Assert bought_cost is correct when 1 buy is completely consumed by 1 sell

    Regression test for part of https://github.com/rotki/rotki/issues/223
    """
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(5),
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
    )
    assert taxable_amount == 5, '5 out of 5 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('1340.5005'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'only buy should have been used'


def test_calculate_spend_cost_basis1_buy_used_by_2_sells_taxable(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxable part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(3),
        spending_asset=asset,
        timestamp=1467378304,  # 31/06/2016
    )
    assert taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('804.3003'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 1, 'whole buy was not used'
    remaining_amount = accountant.events.cost_basis.events[asset].acquisitions[0].amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    # now eat up all the rest
    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=1467378404,  # bit after previous sell
    )
    assert taxable_amount == 2, '2 out of 2 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('536.2002'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'the buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_1_buy_used_by_2_sells_taxfree(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxfree part of:
    https://github.com/rotki/rotki/issues/223
    """
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(3),
        spending_asset=asset,
        timestamp=1480683904,  # 02/12/2016
    )
    assert taxable_amount == 0, '0 out of 3 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('804.3003'))
    assert taxable_bought_cost.is_close(FVal('0'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 1, 'whole buy was not used'
    remaining_amount = accountant.events.cost_basis.events[asset].acquisitions[0].amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    # now eat up all the rest
    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(2),
        spending_asset=asset,
        timestamp=1480683954,  # bit after previous sell
    )
    assert taxable_amount == 0, '0 out of 2 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('536.2002'))
    assert taxable_bought_cost.is_close(FVal('0'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'the buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_sell_more_than_bought_within_year(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(3),
        spending_asset=asset,
        timestamp=1467478304,  # bit after 31/06/2016
    )

    assert taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('880.552'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'only buy should have been used'


@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_calculate_spend_cost_basis_sell_more_than_bought_after_year(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.cost_basis.calculate_spend_cost_basis(
        spending_amount=FVal(3),
        spending_asset=asset,
        timestamp=1523399409,  # 10/04/2018
    )

    assert taxable_amount == 1, '1 out of 3 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('880.552'))
    assert taxable_bought_cost.is_close(FVal('0'))

    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'only buy should have been used'


def test_reduce_asset_amount(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(3),  # 25/10/2016
            timestamp=1477378304,
            rate=FVal(603.415),
            fee_rate=FVal(0.0017),
        ),
    )

    assert accountant.events.cost_basis.reduce_asset_amount(asset, FVal(1.5))
    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 2, '1 buy should be used'
    remaining_amount = accountant.events.cost_basis.events[asset].acquisitions[0].amount
    assert remaining_amount == FVal(0.5), '0.5 of 2nd buy should remain'


def test_reduce_asset_amount_exact(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    assert accountant.events.cost_basis.reduce_asset_amount(asset, FVal(2))
    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'all buys should be used'


def test_reduce_asset_amount_not_bought(accountant):
    asset = 'BTC'
    assert not accountant.events.cost_basis.reduce_asset_amount(asset, FVal(3))


def test_reduce_asset_amount_more_that_bought(accountant):
    asset = 'BTC'
    events = accountant.events.cost_basis.events
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events[asset].acquisitions.append(
        AssetAcquisitionEvent(
            location=Location.EXTERNAL,
            description='trade',
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    assert not accountant.events.cost_basis.reduce_asset_amount(asset, FVal(3))
    acquisitions_num = len(accountant.events.cost_basis.events[asset].acquisitions)
    assert acquisitions_num == 0, 'all buys should be used'
