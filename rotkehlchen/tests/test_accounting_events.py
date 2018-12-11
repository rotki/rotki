from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import BuyEvent, Events


def test_search_buys_calculate_profit_after_year(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(5),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=FVal(15),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(8),
        selling_asset=asset,
        timestamp=1480683904,  # 02/12/2016
    )

    assert taxable_amount == 3, '3 out of 8 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('1340.5005'))
    assert taxable_bought_cost.is_close(FVal('1837.3557'))

    assert (len(accountant.events.events[asset].buys)) == 2, 'first buy should have been used'
    remaining_amount = accountant.events.events[asset].buys[0].amount
    assert remaining_amount == FVal(12), '3 of 15 should have been consumed'


def test_search_buys_calculate_profit_1_buy_consumed_by_1_sell(accountant):
    """ Assert bought_cost is correct when 1 buy is completely consumed by 1 sell

    Regression test for part of https://github.com/rotkehlchenio/rotkehlchen/issues/223
    """
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(5),
        selling_asset=asset,
        timestamp=1467378304,  # 31/06/2016
    )
    assert taxable_amount == 5, '5 out of 5 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('1340.5005'))

    assert (len(accountant.events.events[asset].buys)) == 0, 'only buy should have been used'


def test_search_buys_calculate_profit_1_buy_used_by_2_sells_taxable(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxable part of:
    https://github.com/rotkehlchenio/rotkehlchen/issues/223
    """
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(3),
        selling_asset=asset,
        timestamp=1467378304,  # 31/06/2016
    )
    assert taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('804.3003'))

    assert (len(accountant.events.events[asset].buys)) == 1, 'whole buy was not used'
    remaining_amount = accountant.events.events[asset].buys[0].amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    # now eat up all the rest
    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(2),
        selling_asset=asset,
        timestamp=1467378404,  # bit after previous sell
    )
    assert taxable_amount == 2, '2 out of 2 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('536.2002'))

    assert (len(accountant.events.events[asset].buys)) == 0, 'the buy should have been used'


def test_search_buys_calculate_profit_1_buy_used_by_2_sells_taxfree(accountant):
    """ Make sure that when 1 buy is used by 2 sells bought cost is correct

    Regression test for taxfree part of:
    https://github.com/rotkehlchenio/rotkehlchen/issues/223
    """
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(3),
        selling_asset=asset,
        timestamp=1480683904,  # 02/12/2016
    )
    assert taxable_amount == 0, '0 out of 3 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('804.3003'))
    assert taxable_bought_cost.is_close(FVal('0'))

    assert (len(accountant.events.events[asset].buys)) == 1, 'whole buy was not used'
    remaining_amount = accountant.events.events[asset].buys[0].amount
    assert remaining_amount == FVal(2), '3 of 5 should have been consumed'

    # now eat up all the rest
    (
        taxable_amount,
        taxable_bought_cost,
        taxfree_bought_cost,
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(2),
        selling_asset=asset,
        timestamp=1480683954,  # bit after previous sell
    )
    assert taxable_amount == 0, '0 out of 2 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('536.2002'))
    assert taxable_bought_cost.is_close(FVal('0'))

    assert (len(accountant.events.events[asset].buys)) == 0, 'the buy should have been used'


def test_search_buys_calculate_profit_sell_more_than_bought_within_year(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(3),
        selling_asset=asset,
        timestamp=1467478304,  # bit after 31/06/2016
    )

    assert taxable_amount == 3, '3 out of 3 should be taxable (within a year)'
    assert taxfree_bought_cost.is_close(FVal('0'))
    assert taxable_bought_cost.is_close(FVal('880.552'))

    assert (len(accountant.events.events[asset].buys)) == 0, 'only buy should have been used'


def test_search_buys_calculate_profit_sell_more_than_bought_after_year(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
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
    ) = accountant.events.search_buys_calculate_profit(
        selling_amount=FVal(3),
        selling_asset=asset,
        timestamp=1523399409,  # 10/04/2018
    )

    assert taxable_amount == 1, '1 out of 3 should be taxable (after a year)'
    assert taxfree_bought_cost.is_close(FVal('880.552'))
    assert taxable_bought_cost.is_close(FVal('0'))

    assert (len(accountant.events.events[asset].buys)) == 0, 'only buy should have been used'


def test_reduce_asset_amount(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=FVal(3),  # 25/10/2016
            timestamp=1477378304,
            rate=FVal(603.415),
            fee_rate=FVal(0.0017),
        ),
    )

    assert accountant.events.reduce_asset_amount(asset, FVal(1.5))
    assert (len(accountant.events.events[asset].buys)) == 2, '1 buy should be used'
    remaining_amount = accountant.events.events[asset].buys[0].amount
    assert remaining_amount == FVal(0.5), '0.5 of 2nd buy should remain'


def test_reduce_asset_amount_exact(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    assert accountant.events.reduce_asset_amount(asset, FVal(2))
    assert (len(accountant.events.events[asset].buys)) == 0, 'all buys should be used'


def test_reduce_asset_amount_not_bought(accountant):
    asset = 'BTC'
    assert not accountant.events.reduce_asset_amount(asset, FVal(3))


def test_reduce_asset_amount_more_that_bought(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=FVal(1),
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
        ),
    )

    assert not accountant.events.reduce_asset_amount(asset, FVal(3))
    assert (len(accountant.events.events[asset].buys)) == 0, 'all buys should be used'
