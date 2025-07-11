import re
from contextlib import nullcontext
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import (
    WitnessVersion,
    is_valid_btc_address,
    is_valid_derivation_path,
    pubkey_to_base58_address,
    pubkey_to_bech32_address,
    scriptpubkey_to_bech32_address,
    scriptpubkey_to_p2pkh_address,
    scriptpubkey_to_p2sh_address,
)
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.constants import NON_BITCOIN_CHAINS, SupportedBlockchain
from rotkehlchen.errors.misc import RemoteError, XPUBError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ens import ENS_BRUNO_BTC_ADDR, ENS_BRUNO_BTC_BYTES
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    UNIT_BTC_ADDRESS3,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager


def test_is_valid_btc_address():
    """Test cases for Bech32 addresses taken from here:
    https://en.bitcoin.it/wiki/BIP_0173#Test_vectors
    https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki#test-vectors
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
    # taproot addresses
    assert is_valid_btc_address('bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kt5nd6y')  # noqa: E501
    assert is_valid_btc_address('bc1pgns9vmclx9dfyffsxhknwuedaunz40up23xn0x6wkrznu2jqvgkqxulmws')
    assert is_valid_btc_address('bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0')

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
    assert not is_valid_btc_address('bc1p38j9r5y49hruaue7wxjce0updqjuyyx0kh56v8s25huc6995vvpql3jow4')  # noqa: E501
    assert not is_valid_btc_address('BC130XLXVLHEMJA6C4DQV22UAPCTQUPFHLXM9H8Z3K2E72Q4K9HCZ7VQ7ZWS8R')  # noqa: E501


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
        witver=WitnessVersion.BECH32,
    )
    assert address == 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
    address = pubkey_to_bech32_address(
        bytes.fromhex('037ff51223cb6fddbfc2c90f0ce5bbb3ee1f846f319858940856b1724f7fa1e15c'),
        witver=WitnessVersion.BECH32,
    )
    assert address == 'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5'
    address = pubkey_to_bech32_address(
        bytes.fromhex('02192dce4b382adecdcf74a366fc1f39dd1b88d0829eb058d746702c1d2626ab55'),
        witver=WitnessVersion.BECH32,
    )
    assert address == 'bc1q96nd0va09tdalp7f232ukhj6lp4s5m2g3s2hdy'
    address = pubkey_to_bech32_address(
        bytes.fromhex('03ad84bf691e9d7ddb44d7e9311857af575b686e71506d2c9e8e1d2d11d4f115c1'),
        witver=WitnessVersion.BECH32,
    )
    assert address == 'bc1q7zxvguxdazzjd4m7d7ahlt03nnakc9fhxhskd5'
    address = pubkey_to_bech32_address(
        bytes.fromhex('03cc8a4bc64d897bddc5fbc2f670f7a8ba0b386779106cf1223c6fc5d7cd6fc115'),
        witver=WitnessVersion.BECH32M,
    )
    assert address == 'bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr'
    address = pubkey_to_bech32_address(
        bytes.fromhex('0302f3fa32b3a9da1601f7b843304ce0f4c7efe530650572f28375279a217ecb77'),
        witver=WitnessVersion.BECH32M,
    )
    assert address == 'bc1pwauql42p6wgehs5g8kwkf3vjuw6a66akxv4dndrs9p2nvay8wvmqw2dsld'
    address = pubkey_to_bech32_address(
        bytes.fromhex('0350a1269caac14f3bc69bcfb6096cb40cb26e5e23bfe5ca683c94360f25973f62'),
        witver=WitnessVersion.BECH32M,
    )
    assert address == 'bc1pgns9vmclx9dfyffsxhknwuedaunz40up23xn0x6wkrznu2jqvgkqxulmws'
    address = pubkey_to_bech32_address(
        bytes.fromhex('0277e49029d3a63784d7b719304d7c45b22fa912224635aa4c585d5cf3ed375205'),
        witver=WitnessVersion.BECH32M,
    )
    assert address == 'bc1pnys6fn50vddyhse5t2n59rj2nta9jcmrjlfg7e3p67r3zdgjt5ssd8cl2z'
    address = pubkey_to_bech32_address(
        bytes.fromhex('030dbdc19f74ea2cacf829315c4af1ef7439562b2ddcd040bfa229215ebab1be82'),
        witver=WitnessVersion.BECH32M,
    )
    assert address == 'bc1p0vuq2cmrm7xdyc4wskdg8hp2prgkpe56g09knye73ne97tjdqfgqru9fkg'


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

    # taproot xpubs using test vectors from:
    # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors
    xpub = 'xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ'  # noqa: E501
    root = HDKey.from_xpub(xpub=xpub, xpub_type=XpubType.P2TR, path='m/86/0/0')

    expected_addresses = [
        'bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr',
        'bc1p4qhjn9zdvkux4e44uhx8tc55attvtyu358kutcqkudyccelu0was9fqzwh',
    ]
    for i in range(2):
        child = root.derive_path(f'm/86/0/0/0/{i}')
        assert child.address() == expected_addresses[i]

    child = root.derive_path('m/86/0/0/1/0')
    assert child.address() == 'bc1p3qkhfews2uk44qtvauqyr2ttdsw7svhkl9nkm9s9c3x4ax5h60wqwruhk7'


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
        HDKey.from_xpub('zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp33333333333333yDDxQUo3q')
    with pytest.raises(XPUBError):
        HDKey.from_xpub('xpriv68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')
    with pytest.raises(XPUBError):
        HDKey.from_xpub('apfiv68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')


def test_xpub_data_comparison():
    hdkey1 = HDKey.from_xpub('xpub6DCi5iJ57ZPd5qPzvTm5hUt6X23TJdh9H4NjNsNbt7t7UuTMJfawQWsdWRFhfLwkiMkB1rQ4ZJWLB9YBnzR7kbs9N8b2PsKZgKUHQm1X4or')  # noqa: E501
    hdkey2 = HDKey.from_xpub('xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk')  # noqa: E501
    xpubdata1 = XpubData(xpub=hdkey1, blockchain=SupportedBlockchain.BITCOIN)
    xpubdata2 = XpubData(xpub=hdkey2, blockchain=SupportedBlockchain.BITCOIN)
    mapping = {xpubdata1: 1}
    # there is a reason for both queries (unneeded-not). In the first
    # implementation they did not both work correctly
    assert not xpubdata1 == xpubdata2  # pylint: disable=unneeded-not  # noqa: SIM201
    assert xpubdata1 != xpubdata2
    assert xpubdata1 in mapping
    assert xpubdata2 not in mapping

    xpubdata1 = XpubData(xpub=hdkey1, blockchain=SupportedBlockchain.BITCOIN)
    xpubdata2 = XpubData(xpub=hdkey1, blockchain=SupportedBlockchain.BITCOIN_CASH)
    mapping = {xpubdata1: 1}
    # there is a reason for both queries (unneeded-not). In the first
    # implementation they did not both work correctly
    assert not xpubdata1 == xpubdata2  # pylint: disable=unneeded-not  # noqa: SIM201
    assert xpubdata1 != xpubdata2
    assert xpubdata1 in mapping
    assert xpubdata2 not in mapping

    xpubdata1 = XpubData(xpub=hdkey1, blockchain=SupportedBlockchain.BITCOIN)
    xpubdata2 = XpubData(xpub=hdkey1, blockchain=SupportedBlockchain.BITCOIN)
    assert xpubdata1 == xpubdata2
    assert not xpubdata1 != xpubdata2  # pylint: disable=unneeded-not  # noqa: SIM202

    xpubdata1 = XpubData(xpub=hdkey1, derivation_path='m', blockchain=SupportedBlockchain.BITCOIN)
    xpubdata2 = XpubData(xpub=hdkey1, derivation_path='m/0/0', blockchain=SupportedBlockchain.BITCOIN)  # noqa: E501
    assert xpubdata1 != xpubdata2
    assert not xpubdata1 == xpubdata2  # pylint: disable=unneeded-not  # noqa: SIM201


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
        'Derivation paths accepted by rotki should have no hardened nodes. '
        "Meaning no nodes with a '"
    )
    assert not valid
    assert msg == expected_msg


@pytest.mark.parametrize(('scriptpubkey', 'expected_address'), [
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


@pytest.mark.parametrize(('scriptpubkey', 'expected_address'), [
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


def test_valid_bitcoin_chains():
    """Test that checks that Bitcoin chains are not in `NON_BITCOIN_CHAIN` constant."""
    for blockchain in SupportedBlockchain:
        if blockchain not in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            assert blockchain in NON_BITCOIN_CHAINS


BLOCKCHAIN_INFO_RESULT = {
    'addresses': [
        {
            'address': '34SjMcbLquZ7HmFmQiAHqEHY4mBEbvGeVL',
            'final_balance': 0,
            'n_tx': 0,
            'total_received': 0,
            'total_sent': 0,
        },
        {
            'address': '3J7sT2fbDaF3XrjpWM5GsUyaDr7i7psi88',
            'final_balance': 0,
            'n_tx': 0,
            'total_received': 0,
            'total_sent': 0,
        },
        {
            'address': '36Z62MQfJHF11DWqMMzc3rqLiDFGiVF8CB',
            'final_balance': 0,
            'n_tx': 0,
            'total_received': 0,
            'total_sent': 0,
        },
        {
            'address': '33k4CdyQJFwXQD9giSKyo36mTvE9Y6C9cP',
            'final_balance': 0,
            'n_tx': 0,
            'total_received': 0,
            'total_sent': 0,
        },
        {
            'address': '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5',
            'final_balance': 2520331,
            'n_tx': 238,
            'total_received': 255627050,
            'total_sent': 253106719,
        },
    ],
    'wallet': {
        'final_balance': 2520331,
        'n_tx': 100,
        'n_tx_filtered': 100,
        'total_received': 255627050,
        'total_sent': 253106719,
    },
    'txs': [],
    'info': {
        'latest_block': {
            'hash': '000000000000000000024b14ba68f5f9ac5fbc6c3c41dd7ae939183ef62d9847',
            'height': 767846,
            'time': 1671317014,
            'block_index': 767846,
        },
    },
    'recommend_include_fee': True,
}


def test_bitcoin_balance_api_resolver(
        network_mocking: bool,
        bitcoin_manager: 'BitcoinManager',
) -> None:
    """Test that bitcoin balances are queried and that if one source fails we use the next"""
    address_re = re.compile(r'.*/address/(.*)')
    addresses = [
        BTCAddress('3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5'),
        BTCAddress('34SjMcbLquZ7HmFmQiAHqEHY4mBEbvGeVL'),
        BTCAddress('3J7sT2fbDaF3XrjpWM5GsUyaDr7i7psi88'),
        BTCAddress('36Z62MQfJHF11DWqMMzc3rqLiDFGiVF8CB'),
        BTCAddress('33k4CdyQJFwXQD9giSKyo36mTvE9Y6C9cP'),
    ]

    def mock_blockstream_or_mempool_query(url, **kwargs):  # pylint: disable=unused-argument
        match = address_re.search(url)
        assert match
        address = match.group(1)
        contents = f"""{{
        "address": "{address}",
        "chain_stats": {{"funded_txo_count": 216, "funded_txo_sum": 255627050,
        "spent_txo_count": 201, "spent_txo_sum": 253106719, "tx_count": 238
        }},
        "mempool_stats": {{
        "funded_txo_count": 0, "funded_txo_sum": 0, "spent_txo_count": 0, "spent_txo_sum": 0,
        "tx_count": 0}}}}"""
        return MockResponse(200, contents)

    def check_balances(balances_to_check: dict[BTCAddress, FVal]) -> None:
        for addr in addresses:
            assert addr in balances_to_check

    blockchain_info_mock = patch(
        'rotkehlchen.chain.bitcoin.btc.manager.request_get_dict',
        return_value=BLOCKCHAIN_INFO_RESULT,
    ) if network_mocking else nullcontext()
    blockstream_mempool_mock = patch(
        'requests.get',
        side_effect=mock_blockstream_or_mempool_query,
    ) if network_mocking else nullcontext()

    # Test balances are returned properly if first source works
    with blockchain_info_mock:
        balances = bitcoin_manager.get_balances(addresses)
    check_balances(balances)

    def mock_query_blockstream_or_mempool(only_blockstream: bool, **kwargs):
        if only_blockstream and 'blockstream' in kwargs['url']:
            raise RemoteError('Fatality')

        return request_get_dict(**kwargs)

    # First source fails
    with patch(
            'rotkehlchen.chain.bitcoin.btc.manager.BitcoinManager._query_blockchain_info',
            MagicMock(side_effect=KeyError('someProperty')),
    ):
        with blockstream_mempool_mock:
            balances = bitcoin_manager.get_balances(addresses)
        check_balances(balances)

        # Second source fails
        with patch(
            'rotkehlchen.chain.bitcoin.btc.manager.request_get_dict',
            new=lambda *args, **kwargs: mock_query_blockstream_or_mempool(
                only_blockstream=True,
                **kwargs,
            ),
        ):
            with blockstream_mempool_mock:
                balances = bitcoin_manager.get_balances(addresses)
            check_balances(balances)

            # Third source fails - FATALITY!!!
            with patch(
                'rotkehlchen.chain.bitcoin.btc.manager.request_get_dict',
                new=lambda *args, **kwargs: mock_query_blockstream_or_mempool(
                    only_blockstream=False,
                    **kwargs,
                ),
            ):
                bitcoin_manager.get_balances(addresses)
