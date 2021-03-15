import json
import warnings as test_warnings
from pathlib import Path

import pytest
from eth_utils import is_checksum_address

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver, asset_type_mapping
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import get_ethereum_token
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.errors import DeserializationError, InputError, UnknownAsset
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import AssetType
from rotkehlchen.utils.hashing import file_md5


def test_unknown_asset():
    """Test than an unknown asset will throw"""
    with pytest.raises(UnknownAsset):
        Asset('jsakdjsladjsakdj')


def test_repr():
    btc_repr = repr(Asset('BTC'))
    assert btc_repr == '<Asset identifier:BTC name:Bitcoin symbol:BTC>'


def test_asset_hashes_properly():
    """Test that assets can be hashed and are equivalent to the canonical string"""
    btc_asset = Asset('BTC')
    eth_asset = Asset('ETH')
    mapping = {btc_asset: 100, 'ETH': 200}

    assert btc_asset in mapping
    assert eth_asset in mapping
    assert 'BTC' in mapping
    assert 'ETH' in mapping

    assert mapping[btc_asset] == 100
    assert mapping[eth_asset] == 200
    assert mapping['BTC'] == 100
    assert mapping['ETH'] == 200


def test_asset_equals():
    btc_asset = Asset('BTC')
    eth_asset = Asset('ETH')
    other_btc_asset = Asset('BTC')

    assert btc_asset == 'BTC'
    assert btc_asset != eth_asset
    assert btc_asset != 'ETH'
    assert btc_asset == other_btc_asset
    assert eth_asset == 'ETH'


def test_ethereum_tokens():
    rdn_asset = EthereumToken('RDN')
    assert rdn_asset.ethereum_address == '0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'
    assert rdn_asset.decimals == 18
    assert rdn_asset.is_eth_token()

    with pytest.raises(DeserializationError):
        EthereumToken('BTC')


def test_cryptocompare_asset_support(cryptocompare):
    """Try to detect if a token that we have as not supported by cryptocompare got added"""
    cc_assets = cryptocompare.all_coins()
    exceptions = (
        'BKC',     # Bankcoin Cash but Balkan Coin in CC
        'BNC',     # Bionic but Benja Coin in CC
        'BTG-2',   # Bitgem but Bitcoin Gold in CC
        'BTR',     # Bitether but Bither in CC
        'CBC-2',   # Cashbery coin but Casino Betting Coin in CC
        'CCN',     # CustomContractnetwork but CannaCoin in CC
        'CMCT-2',  # Cyber Movie Chain but Crowd Machine in CC
        'CORN-2',  # Cornichon but Corn in CC
        'CTX',     # Centauri coin but CarTaxi in CC
        'DIT',     # Direct insurance token but DitCoin in CC
        'DRM',     # Dreamcoin but Dreamchain in CC
        'DTX-2',   # Digital Ticks but Data Exchange in CC
        'GNC',     # Galaxy network but Greencoin in CC
        'KNT',     # Kora network but Knekted in CC
        'LKY',     # Linkey but LuckyCoin in CC
        'NTK-2',   # Netkoin but Neurotoken in CC
        'PAN',     # Panvala but Pantos in CC
        'PTT',     # Proton token but Pink Taxi Token in CC
        'RMC',     # Remicoin but Russian Miner Coin in CC
        'SOUL-2',  # Cryptosoul but Phantasma in CC
        'TIC',     # Thingschain but True Investment Coin in CC
        'TOK',     # TOKOK but Tokugawa Coin in CC
        'VD',      # Bitcoin card but Vindax Coin in CC
        'DT',      # Dragon Token but Dark Token in CC
        'MUST',    # Must (Cometh) but Must protocol in CC
        'SDT-2',   # Stake DAO token but TerraSDT in CC
        'BAC',     # Basis Cash but BACoin in CC
        'IHF',     # waiting until cryptocompare fixes historical price for this. https://github.com/rotki/rotki/pull/2176  # noqa: E501
        'FLOW',    # FLOW from dapper labs but "Flow Protocol" in CC
        'NCT-2',   # Name change token but Polyswarm in CC
        'NDX',     # newdex token but Index token in CC
        'ARCH-2',  # Archer DAO Governance token but Archcoin in CC
        'AC-2',    # Acoconut token but Asiacoin in CC
        'TON',     # Tontoken but Tokamak network in CC
        'FNK',     # Finiko token but FunKeyPai network in CC
        'LOTTO',   # Lotto token but LottoCoin in CC
        'XFI',     # Dfinance token but XFinance in CC
        'GOLD',    # Gold token but Golden Goose in CC
        'ACM',     # AC Milan Fan Token but Actinium in CC
        'TFC',     # TheFutbolCoin but The Freedom Coin in CC
        'MASK',    # Mask Network but NFTX Hashmask Index in CC
    )
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        potential_support = (
            asset_data.cryptocompare == '' and
            asset_data.symbol in cc_assets and
            asset_data.identifier not in exceptions
        )
        if potential_support:
            msg = (
                f'We have {asset_data.identifier} as not supported by cryptocompare but '
                f'the symbol appears in its supported assets'
            )
            test_warnings.warn(UserWarning(msg))


def test_all_assets_json_tokens_address_is_checksummed():
    """Test that all ethereum saved token asset addresses are checksummed"""
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        if not asset_data.asset_type == AssetType.ETHEREUM_TOKEN:
            continue

        msg = (
            f'Ethereum token\'s {asset_data.name} ethereum address '
            f'is not checksummed {asset_data.ethereum_address}'
        )
        assert is_checksum_address(asset_data.ethereum_address), msg


def test_asset_identifiers_are_unique_all_lowercased():
    """Test that adding an identifier that exists but with different case, would fail"""
    with pytest.raises(InputError):
        GlobalDBHandler().add_asset(
            'Eth',
            AssetType.BINANCE_TOKEN,
            {'name': 'a', 'symbol': 'b'},
        )


def test_case_does_not_matter_for_asset_constructor():
    """Test that whatever case we give to asset constructor result is the same"""
    a1 = Asset('USDt')
    a2 = Asset('USDT')
    assert a1 == a2
    assert a1.identifier == 'USDT'
    assert a2.identifier == 'USDT'


def test_all_assets_json_assets_have_common_keys():
    """Test that checks that the keys and types of tokens in all_assets.json are correct"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    with open(root_dir / 'data' / 'all_assets.json', 'r') as f:
        assets = json.loads(f.read())
    # Create a list of pairs with fields with their types. We'll add more fields to check
    # if we are dealing with a token
    verify = (("symbol", str), ("name", str), ("type", str), ("started", int))
    verify_fiat = (("symbol", str), ("name", str), ("type", str))
    verify_token = (("symbol", str), ("name", str), ("type", str), ("started", int),
                    ("ethereum_address", str), ("ethereum_token_decimals", int))
    optional = (("active", bool), ("ended", int), ("forked", str), ("swapped_for", str),
                ("cryptocompare", str), ("coingecko", str))

    for asset_id, asset_data in assets.items():
        verify_against = verify

        # Check if the asset is a token and update the keys to verify
        asset_type = asset_type_mapping[asset_data['type']]
        if asset_type == AssetType.ETHEREUM_TOKEN:
            verify_against = verify_token
        elif asset_type == AssetType.FIAT:
            verify_against = verify_fiat

        # make the basic checks
        msg = f'Key verification in asset {asset_id} failed'
        assert all((key in asset_data.keys() and isinstance(asset_data[key], key_type)
                    for (key, key_type) in verify_against
                    )), msg

        # check the optional fields
        for key, key_type in optional:
            if asset_data.get(key) is not None:
                assert isinstance(asset_data.get(key), key_type), msg


def test_coingecko_identifiers_are_reachable(data_dir):
    """
    Test that all assets have a coingecko entry and that all the identifiers exist in coingecko
    """
    coingecko = Coingecko(data_directory=data_dir)
    all_coins = coingecko.all_coins()

    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        identifier = asset_data.identifier
        if identifier in DELISTED_ASSETS:
            # delisted assets won't be in the mapping
            continue

        if asset_data.asset_type == AssetType.FIAT:
            continue

        found = True
        coingecko_str = asset_data.coingecko
        msg = f'Asset {identifier} does not have a coingecko entry'
        assert coingecko_str is not None, msg
        if coingecko_str != '':
            found = False
            for entry in all_coins:
                if coingecko_str == entry['id']:
                    found = True
                    break

        suggestions = []
        if not found:
            for entry in all_coins:
                if entry['symbol'].upper() == asset_data.symbol.upper():
                    suggestions.append((entry['id'], entry['name'], entry['symbol']))
                    continue

                if entry['name'].upper() == asset_data.symbol.upper():
                    suggestions.append((entry['id'], entry['name'], entry['symbol']))
                    continue

        msg = f'Asset {identifier} coingecko mapping does not exist.'
        if len(suggestions) != 0:
            for s in suggestions:
                msg += f'\nSuggestion: id:{s[0]} name:{s[1]} symbol:{s[2]}'
        if not found:
            test_warnings.warn(UserWarning(msg))


def test_assets_json_meta():
    """Test that all_assets.json md5 matches and that if md5 changes since last
    time then version is also bumped"""
    last_meta = {'md5': 'bd4e22bc1bd65aef857bdbf9137b37d9', 'version': 71}
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    data_md5 = file_md5(data_dir / 'all_assets.json')

    with open(data_dir / 'all_assets.meta', 'r') as f:
        saved_meta = json.loads(f.read())

    assert data_md5 == saved_meta['md5']

    msg = 'The last meta md5 of the test does not match the one in all_assets.meta'
    assert saved_meta['md5'] == last_meta['md5'], msg
    msg = 'The last meta version of the test does not match the one in all_assets.meta'
    assert saved_meta['version'] == last_meta['version'], msg


@pytest.mark.parametrize('mock_asset_meta_github_response', ['{"md5": "", "version": 99999999}'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('mock_asset_github_response', ["""{
"COMPRLASSET": {
    "coingecko": "",
    "name": "Completely real asset, totally not for testing only",
    "symbol": "COMPRLASSET",
    "type": "own chain"
}
}"""])
@pytest.mark.parametrize('force_reinitialize_asset_resolver', [True])
def test_assets_pulling_from_github_works(asset_resolver):  # pylint: disable=unused-argument
    """Test that pulling assets from mock github (due to super high version) makes the
    pulled assets available to the local Rotki instance"""
    new_asset = Asset("COMPRLASSET")
    assert new_asset.name == 'Completely real asset, totally not for testing only'
    # After the test runs we must reset the asset resolver so that it goes back to
    # the normal list of assets
    AssetResolver._AssetResolver__instance = None


@pytest.mark.parametrize('mock_asset_meta_github_response', ['{"md5": "", "version": 99999999}'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('mock_asset_github_response', ["""{
"COMPRLASSET2": {
    "coingecko": "",
    "name": "Completely real asset, totally not for testing only",
    "symbol": "COMPRLASSET2",
    "type": "not existing type"
}
}"""])
@pytest.mark.parametrize('force_reinitialize_asset_resolver', [True])
def test_asset_with_unknown_type_does_not_crash(asset_resolver):  # pylint: disable=unused-argument
    """Test that finding an asset with an unknown type does not crash Rotki"""
    with pytest.raises(UnknownAsset):
        Asset('COMPRLASSET2')
    # After the test runs we must reset the asset resolver so that it goes back to
    # the normal list of assets
    AssetResolver._AssetResolver__instance = None


def test_get_ethereum_token():
    assert A_DAI == get_ethereum_token(
        symbol='DAI',
        ethereum_address='0x6B175474E89094C44Da98b954EedeAC495271d0F',
    )
    unknown_token = UnknownEthereumToken(
        symbol='DAI',
        ethereum_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
        decimals=18,
    )
    assert unknown_token == get_ethereum_token(
        symbol='DAI',
        ethereum_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
    ), 'correct symbol but wrong address should result in unknown token'
    unknown_token = UnknownEthereumToken(
        symbol='DOT',
        ethereum_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
        decimals=18,
    )
    assert unknown_token == get_ethereum_token(
        symbol='DOT',
        ethereum_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
    ), 'symbol of normal chain (polkadot here) should result in unknown token'
