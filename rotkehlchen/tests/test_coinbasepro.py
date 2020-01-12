from rotkehlchen.exchanges.coinbasepro import Coinbasepro


def test_name():
    exchange = Coinbasepro('a', b'a', object(), object())
    assert exchange.name == 'coinbasepro'
