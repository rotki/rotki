from rotkehlchen.chain.bitcoin import is_valid_btc_address
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    UNIT_BTC_ADDRESS3,
)


def test_is_valid_btc_address():
    """Test cases for Bech32 addresses taken from here:
    https://en.bitcoin.it/wiki/BIP_0173#Test_vectors
    Note that we do not support test net addresses (starting with 'tb1').
    """
    assert is_valid_btc_address(UNIT_BTC_ADDRESS1)
    assert is_valid_btc_address(UNIT_BTC_ADDRESS2)
    assert is_valid_btc_address(UNIT_BTC_ADDRESS3)
    assert is_valid_btc_address('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    assert is_valid_btc_address('bc1qhkje0xfvhmgk6mvanxwy09n45df03tj3h3jtnf')
    assert is_valid_btc_address('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4')
    assert is_valid_btc_address('bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3')
    assert is_valid_btc_address('BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4')
    assert is_valid_btc_address(
        'bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k7grplx')
    assert is_valid_btc_address('BC1SW50QA3JX3S')
    assert is_valid_btc_address('bc1zw508d6qejxtdg4y5r3zarvaryvg6kdaj')

    assert not is_valid_btc_address('foo')
    assert not is_valid_btc_address('18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1')
    assert not is_valid_btc_address(
        'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3')
    assert not is_valid_btc_address('bc1qr')
    assert not is_valid_btc_address(
        'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7')
    assert not is_valid_btc_address(
        'tb1qqqqqp399et2xygdj5xreqhjjvcmzhxw4aywxecjdzew6hylgvsesrxh6hy')
    assert not is_valid_btc_address('tc1qw508d6qejxtdg4y5r3zarvary0c5xw7kg3g4ty')
    assert not is_valid_btc_address('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5')
    assert not is_valid_btc_address('BC13W508D6QEJXTDG4Y5R3ZARVARY0C5XW7KN40WF2')
    assert not is_valid_btc_address('bc1rw5uspcuh')
    assert not is_valid_btc_address(
        'bc10w508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kw5rljs90')
    assert not is_valid_btc_address('BC1QR508D6QEJXTDG4Y5R3ZARVARYV98GJ9P')
    assert not is_valid_btc_address(
        'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sL5k7')
    assert not is_valid_btc_address('bc1zw508d6qejxtdg4y5r3zarvaryvqyzf3du')
    assert not is_valid_btc_address(
        'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3pjxtptv')
    assert not is_valid_btc_address('bc1gmk9yu')
