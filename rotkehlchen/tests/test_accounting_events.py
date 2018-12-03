from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import BuyEvent, Events


def test_search_buys_calculate_profit_after_year(accountant):
    asset = 'BTC'
    events = accountant.events.events
    events[asset] = Events(list(), list())
    events[asset].buys.append(
        BuyEvent(
            amount=5,
            timestamp=1446979735,  # 08/11/2015
            rate=FVal(268.1),
            fee_rate=FVal(0.0001),
            cost=FVal(1340.5),
        ),
    )
    events['BTC'].buys.append(
        BuyEvent(
            amount=15,
            timestamp=1467378304,  # 31/06/2016
            rate=FVal(612.45),
            fee_rate=FVal(0.0019),
            cost=FVal(9186.75),
        ),
    )

    import pdb
    pdb.set_trace()
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
    assert taxfree_bought_cost.is_close(FVal('1340.5'))
    assert taxable_bought_cost.is_close(FVal('1837.3443'))

    assert (len(accountant.events.events[asset].buys)) == 1, 'first buy should have been used'
    remaining_amount = accountant.events.events[asset].buys[0].amount
    assert remaining_amount == FVal(12), '3 of 15 should have been consumed'
