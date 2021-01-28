import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import (
    is_valid_btc_address,
    is_valid_derivation_path,
    pubkey_to_base58_address,
    pubkey_to_bech32_address,
    scriptpubkey_to_bech32_address,
    scriptpubkey_to_p2pkh_address,
    scriptpubkey_to_p2sh_address,
)
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.errors import XPUBError
from rotkehlchen.tests.utils.ens import ENS_BRUNO_BTC_ADDR, ENS_BRUNO_BTC_BYTES
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

    assert not is_valid_btc_address('')
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


def test_pubkey_to_base58_address():
    """Test vectors from here: https://iancoleman.io/bip39/"""
    address = pubkey_to_base58_address(
        bytes.fromhex('03564213318d739994e4d9785bf40eac4edbfa21f0546040ce7e6859778dfce5d4'),
    )
    assert address == '127NVqnjf8gB9BFAW2dnQeM6wqmy1gbGtv'
    address = pubkey_to_base58_address(
        bytes.fromhex('0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2'),
    )
    assert address == '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma'
    address = pubkey_to_base58_address(
        bytes.fromhex('035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56'),
    )
    assert address == '19Q2WoS5hSS6T8GjhK8KZLMgmWaq4neXrh'
    address = pubkey_to_base58_address(
        bytes.fromhex('03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c'),
    )
    assert address == '1JQheacLPdM5ySCkrZkV66G2ApAXe1mqLj'
    address = pubkey_to_base58_address(
        bytes.fromhex('0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2'),
    )
    assert address == '1NjxqbA9aZWnh17q1UW3rB4EPu79wDXj7x'


def test_pubkey_to_bech32_address():
    """Test vectors from here: https://iancoleman.io/bip39/"""
    address = pubkey_to_bech32_address(
        bytes.fromhex('0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'),
        witver=0,
    )
    assert address == 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
    address = pubkey_to_bech32_address(
        bytes.fromhex('037ff51223cb6fddbfc2c90f0ce5bbb3ee1f846f319858940856b1724f7fa1e15c'),
        witver=0,
    )
    assert address == 'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5'
    address = pubkey_to_bech32_address(
        bytes.fromhex('02192dce4b382adecdcf74a366fc1f39dd1b88d0829eb058d746702c1d2626ab55'),
        witver=0,
    )
    assert address == 'bc1q96nd0va09tdalp7f232ukhj6lp4s5m2g3s2hdy'
    address = pubkey_to_bech32_address(
        bytes.fromhex('03ad84bf691e9d7ddb44d7e9311857af575b686e71506d2c9e8e1d2d11d4f115c1'),
        witver=0,
    )
    assert address == 'bc1q7zxvguxdazzjd4m7d7ahlt03nnakc9fhxhskd5'


def test_from_xpub_with_conversion():
    legacy_xpub = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa: E501
    legacy_xpub_hdkey = HDKey.from_xpub(xpub=legacy_xpub, path='m')

    converted_ypub_hdkey = HDKey.from_xpub(
        xpub=legacy_xpub,
        xpub_type=XpubType.P2SH_P2WPKH,
        path='m',
    )
    assert legacy_xpub_hdkey.network == converted_ypub_hdkey.network
    assert legacy_xpub_hdkey.depth == converted_ypub_hdkey.depth
    assert legacy_xpub_hdkey.parent_fingerprint == converted_ypub_hdkey.parent_fingerprint
    assert legacy_xpub_hdkey.chain_code == converted_ypub_hdkey.chain_code
    assert legacy_xpub_hdkey.fingerprint == converted_ypub_hdkey.fingerprint
    assert legacy_xpub_hdkey.pubkey == converted_ypub_hdkey.pubkey
    assert converted_ypub_hdkey.xpub == 'ypub6Xa42PMu934ALWV34BUZ5wttvRT6n6bMCR6Z4ZKB9Aj23zypTPvrSshYiXRCnhXY2jpyyLSKcqYrd5SWCCU3QeRVnfRzpUF6iRLxd55duzL'  # noqa: E501
    assert converted_ypub_hdkey.hint == 'ypub'

    converted_zpub_hdkey = HDKey.from_xpub(
        xpub=legacy_xpub,
        xpub_type=XpubType.WPKH,
        path='m',
    )
    assert legacy_xpub_hdkey.network == converted_zpub_hdkey.network
    assert legacy_xpub_hdkey.depth == converted_zpub_hdkey.depth
    assert legacy_xpub_hdkey.parent_fingerprint == converted_zpub_hdkey.parent_fingerprint
    assert legacy_xpub_hdkey.chain_code == converted_zpub_hdkey.chain_code
    assert legacy_xpub_hdkey.fingerprint == converted_zpub_hdkey.fingerprint
    assert legacy_xpub_hdkey.pubkey == converted_zpub_hdkey.pubkey
    assert converted_zpub_hdkey.xpub == 'zpub6rQKL42pHibeBog9tYGBJ2zQ6PbYiiar7XcmqxD4XB6u76o3i46R4wMgjjNnncBTSNwnip2t5VuQWN44utt4Ct76f18RQP4az9Qc1eUEkSY'  # noqa: E501
    assert converted_zpub_hdkey.hint == 'zpub'


def test_xpub_to_addresses():
    """Test vectors from here: https://iancoleman.io/bip39/"""
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    root = HDKey.from_xpub(xpub=xpub, path='m')

    expected_addresses = [
        '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r',
        '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe',
        '1DiF6JoLhsAekqps4HURHNd41ZofQSF1t',
        '1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT',
        '16Ny1KwjEB62XzDsjnS4new32nYXGBAkbt',
    ]

    for i in range(5):
        child = root.derive_path(f'm/{i}')
        assert child.address() == expected_addresses[i]

    expected_addresses = [
        '1K3WM7WNiyZCkH31eMoEDwEcmnGNvQfZVA',
        '1L5ic1V3bTJahEdwjufGJ28PjRcMcHWGka',
        '16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW',
        '1NyBphgGhb29kj8UGjixxJCK5XtKLwFj8A',
        '12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd',
    ]

    for i in range(5):
        child = root.derive_path(f'm/0/{i}')
        assert child.address() == expected_addresses[i]


def test_ypub_to_addresses():
    """Test vectors from here: https://iancoleman.io/bip39/"""
    xpub = 'ypub6WkRUvNhspMCJLiLgeP7oL1pzrJ6wA2tpwsKtXnbmpdAGmHHcC6FeZeF4VurGU14dSjGpF2xLavPhgvCQeXd6JxYgSfbaD1wSUi2XmEsx33'  # noqa: E501
    root = HDKey.from_xpub(xpub=xpub, path='m')

    expected_addresses = [
        '3C2NiJHhXKvHDkWp2rq8LyE7G1E7VTndst',
        '34SjMcbLquZ7HmFmQiAHqEHY4mBEbvGeVL',
        '3J7sT2fbDaF3XrjpWM5GsUyaDr7i7psi88',
        '36Z62MQfJHF11DWqMMzc3rqLiDFGiVF8CB',
        '33k4CdyQJFwXQD9giSKyo36mTvE9Y6C9cP',
    ]

    for i in range(5):
        child = root.derive_path(f'm/{i}')
        assert child.address() == expected_addresses[i]

    expected_addresses = [
        '3EQR3ogLugdAw6gwdQZGfr6bx7vHLPiZo5',
        '361gjqdsUY8xBzArsR2ksggEWBaztAqhFL',
        '3HtN6sDxDA1ddnQsvwhvBtQa7JrkuAiVx3',
        '3LNXdKxd8c5RDbB5XRvGMwc2wfv4v26knu',
        '35TfgdHP5zqAQHcFwGCw4n2UigBZYx7dmQ',
    ]

    for i in range(5):
        child = root.derive_path(f'm/0/{i}')
        assert child.address() == expected_addresses[i]


def test_zpub_to_addresses():
    """Test vectors from here: https://iancoleman.io/bip39/"""
    zpub = 'zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q'  # noqa: E501
    root = HDKey.from_xpub(xpub=zpub, path='m')

    expected_addresses = [
        'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5',
        'bc1qnus7355ecckmeyrmvv56mlm42lxvwa4wuq5aev',
        'bc1qup7f8g5k3h5uqzfjed03ztgn8hhe542w69wc0g',
        'bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra',
        'bc1qm2cy0wg6qej4taaywtfx9ccw02zep08r5295gj',
    ]

    for i in range(5):
        child = root.derive_path(f'm/0/{i}')
        assert child.address() == expected_addresses[i]


def test_from_bad_xpub():
    with pytest.raises(XPUBError):
        HDKey.from_xpub('ddodod')
    with pytest.raises(XPUBError):
        HDKey.from_xpub('zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp33333333333333yDDxQUo3q')  # noqa: E501
    with pytest.raises(XPUBError):
        HDKey.from_xpub('xpriv68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')  # noqa: E501
    with pytest.raises(XPUBError):
        HDKey.from_xpub('apfiv68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')  # noqa: E501


def test_xpub_data_comparison():
    hdkey1 = HDKey.from_xpub('xpub6DCi5iJ57ZPd5qPzvTm5hUt6X23TJdh9H4NjNsNbt7t7UuTMJfawQWsdWRFhfLwkiMkB1rQ4ZJWLB9YBnzR7kbs9N8b2PsKZgKUHQm1X4or')  # noqa: E501
    hdkey2 = HDKey.from_xpub('xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')  # noqa: E501
    xpubdata1 = XpubData(xpub=hdkey1)
    xpubdata2 = XpubData(xpub=hdkey2)
    mapping = {xpubdata1: 1}
    # there is a reason for both queries (unneeded-not). In the first
    # implementation they did not both work correctly
    assert not xpubdata1 == xpubdata2  # pylint: disable=unneeded-not
    assert xpubdata1 != xpubdata2
    assert xpubdata1 in mapping
    assert xpubdata2 not in mapping

    xpubdata1 = XpubData(xpub=hdkey1)
    xpubdata2 = XpubData(xpub=hdkey1)
    assert xpubdata1 == xpubdata2
    assert not xpubdata1 != xpubdata2  # pylint: disable=unneeded-not

    xpubdata1 = XpubData(xpub=hdkey1, derivation_path='m')
    xpubdata2 = XpubData(xpub=hdkey1, derivation_path='m/0/0')
    assert xpubdata1 != xpubdata2
    assert not xpubdata1 == xpubdata2  # pylint: disable=unneeded-not


def test_is_valid_derivation_path():
    valid, msg = is_valid_derivation_path('m')
    assert valid
    assert msg == ''
    valid, msg = is_valid_derivation_path('m/0')
    assert valid
    assert msg == ''
    valid, msg = is_valid_derivation_path('m/0/1/49')
    assert valid
    assert msg == ''
    valid, msg = is_valid_derivation_path('m/1/13/1')
    assert valid
    assert msg == ''

    valid, msg = is_valid_derivation_path(55)
    assert not valid
    assert msg == 'Derivation path should be a string'
    valid, msg = is_valid_derivation_path('masdsd')
    assert not valid
    assert msg == 'Derivation paths accepted by rotki should start with m'
    valid, msg = is_valid_derivation_path('masd/0/1')
    assert not valid
    assert msg == 'Derivation paths accepted by rotki should start with m'
    valid, msg = is_valid_derivation_path('m/0/a')
    assert not valid
    assert msg == 'Found non integer node a in xpub derivation path'
    valid, msg = is_valid_derivation_path('m/1/-1/0')
    assert not valid
    assert msg == 'Found negative integer node -1 in xpub derivation path'
    valid, msg = is_valid_derivation_path("m/0/40/15'")
    expected_msg = (
        "Derivation paths accepted by rotki should have no hardened nodes. "
        "Meaning no nodes with a '"
    )
    assert not valid
    assert msg == expected_msg


@pytest.mark.parametrize('scriptpubkey, expected_address', [
    (
        '76a91462e907b15cbf27d5425399ebf6f0fb50ebb88f1888ac',
        '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
    ),
    (
        ENS_BRUNO_BTC_BYTES,
        ENS_BRUNO_BTC_ADDR,
    ),
])
def test_scriptpubkey_to_p2pkh_address(scriptpubkey, expected_address):
    address = scriptpubkey_to_p2pkh_address(bytes.fromhex(scriptpubkey))
    assert address == expected_address


def test_scriptpubkey_to_p2sh_address():
    scriptpubkey = 'a91462e907b15cbf27d5425399ebf6f0fb50ebb88f1887'

    address = scriptpubkey_to_p2sh_address(bytes.fromhex(scriptpubkey))
    assert address == '3Ai1JZ8pdJb2ksieUV8FsxSNVJCpoPi8W6'


@pytest.mark.parametrize('scriptpubkey, expected_address', [
    (
        '0014751e76e8199196d454941c45d1b3a323f1433bd6',
        'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
    ),
    (
        '5128751e76e8199196d454941c45d1b3a323f1433bd6751e76e8199196d454941c45d1b3a323f1433bd6',
        'bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k7grplx',
    ),
    (
        '6002751e',
        'bc1sw50qa3jx3s',
    ),
    (
        '5210751e76e8199196d454941c45d1b3a323',
        'bc1zw508d6qejxtdg4y5r3zarvaryvg6kdaj',
    ),
    (
        '00201863143c14c5166804bd19203356da136c985678cd4d27a1b8c6329604903262',
        'bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3',
    ),
])
def test_scriptpubkey_to_bech32_address(scriptpubkey, expected_address):
    address = scriptpubkey_to_bech32_address(bytes.fromhex(scriptpubkey))
    assert address == expected_address
