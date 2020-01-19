import warnings as test_warnings

from rotkehlchen.errors import UnknownAsset
from rotkehlchen.exchanges.coinbasepro import Coinbasepro, coinbasepro_to_worldpair


# Test fill report for the ETH-BAT product
"""
portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
default,204623,BAT-ETH,SELL,2020-01-13T09:15:06.311Z,1.00000000,BAT,0.00131511,0.00000657555,0.00130853445,ETH
"""

# Test account reports
"""
portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
default,match,2020-01-13T09:15:06.315Z,0.0013151100000000,0.0013151100000000,ETH,,204623,5abf20fe-2b79-2315-57d3-c143dd291654
default,fee,2020-01-13T09:15:06.315Z,-0.0000065755500000,0.0013085344500000,ETH,,204623,5abf20fe-2b79-2315-57d3-c143dd291654
default,withdrawal,2020-01-15T23:51:26.478Z,-0.0011085300000000,0.0002000044500000,ETH,fcc61b23-4b51-43f8-da1e-def2d5a217ad,,
"""

"""
portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
default,deposit,2020-01-12T23:26:44.073Z,14.2500000000000000,14.2500000000000000,BAT,dfdd574b-25ca-de01-asce-edc3c1f2e987,,
default,deposit,2020-01-12T23:38:29.433Z,160.8000000000000000,175.0500000000000000,BAT,489f76g2-4dda-4ab8-3eac-6dffadaa57ba7,,
default,deposit,2020-01-12T23:57:12.306Z,8.6500000000000000,183.7000000000000000,BAT,34c6d26c-d27d-4218-3d14-1493120543e9,,
default,match,2020-01-13T09:15:06.315Z,-1.0000000000000000,182.7000000000000000,BAT,,204623,5abf20fe-2b79-2315-57d3-c143dd291654
"""


def test_name():
    exchange = Coinbasepro('a', b'a', object(), object())
    assert exchange.name == 'coinbasepro'


def test_coverage_of_products():
    """Test that we can process all pairs and assets of the offered coinbasepro products"""
    exchange = Coinbasepro('a', b'a', object(), object())
    products = exchange._api_query('products', request_method='GET')
    for product in products:
        try:
            # Make sure all products can be processed
            coinbasepro_to_worldpair(product['id'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in Coinbase Pro. '
                f'Support for it has to be added',
            ))
