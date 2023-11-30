import pprint
from rotkehlchen.exchanges.bybit import Bybit
from rotkehlchen.utils.misc import ts_now


def test_balances(bybit_exchange: Bybit) -> None:
    response = bybit_exchange.query_online_deposits_withdrawals(start_ts=0, end_ts=ts_now())
    pprint.pprint(response)


    # response = bybit_exchange._api_query(
    #     verb='get',
    #     method_type='Private',
    #     path='market/tickers',
    #     options={'category': 'spot'}
    # )
    # pprint.pprint(response)
    assert False