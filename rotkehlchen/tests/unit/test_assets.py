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
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.externalapis.coingecko import Coingecko
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
    )
    for identifier, asset_data in AssetResolver().assets.items():
        potential_support = (
            asset_data.get('cryptocompare', None) == '' and
            asset_data['symbol'] in cc_assets and
            identifier not in exceptions
        )
        if potential_support:
            msg = (
                f'We have {identifier} as not supported by cryptocompare but '
                f'the symbol appears in its supported assets'
            )
            test_warnings.warn(UserWarning(msg))


def test_tokens_address_is_checksummed():
    """Test that all ethereum saved token asset addresses are checksummed"""
    for _, asset_data in AssetResolver().assets.items():
        asset_type = asset_type_mapping[asset_data['type']]
        if asset_type not in (AssetType.ETH_TOKEN_AND_MORE, AssetType.ETH_TOKEN):
            continue

        msg = (
            f'Ethereum token\'s {asset_data["name"]} ethereum address '
            f'is not checksummed {asset_data["ethereum_address"]}'
        )
        assert is_checksum_address(asset_data['ethereum_address']), msg


def test_asset_identifiers_are_unique_all_lowercased():
    """Test that all asset identifiers would be unique if we do a lowercase comparison"""
    identifier_set = set()
    for asset_id, _ in AssetResolver().assets.items():
        assert asset_id.lower() not in identifier_set, f'id {asset_id} already in the assets set'
        identifier_set.add(asset_id)


def test_coingecko_identifiers_are_reachable(data_dir):
    """
    Test that all assets have a coingecko entry and that all the identifiers exist in coingecko
    """
    coins_delisted_from_coingecko = [
        '1SG',
        'FLUZ',
        'EBCH',
        'GOLOS',
        'NPER',
        'BLN',
        'ADN',
        'PIX',
        'MTC-2',
        'LKY',
        'ARB',
        'BBI',
        'BITCAR',
        'BTR',
        'OLE',
        'ROC',
        'VIN',
        'FIH',
        'WIN-2',
        'ADH',
        'AUR',
        'BAS',
        'BYC',
        'DGS',
        'GMT',
        'HST',
        'INS',
        'IPSX',
        'SHP',
        'WDC',
        'BOST',
        'FND',
        'LDC',
        'ORI',
        'RIPT',
        'SGR',
        'LOCUS',
        'REDC',
        'SGN',
        'SOAR',
        'YUP',
        'AC',
        'APIS',
        'BITPARK',
        'CO2',
        'DAN',
        'DEC',
        'DLT',
        'DROP',
        'ERD',
        'ETBS',
        'GEN',
        'STP',
        'SYNC',
        'TBT',
        'TNT',
        'WIC',
        'XCN',
        'XTP',
        'FREC',
        'PTC',
        'ACC-3',
        'J8T',
        'MRK',
        'TTV',
        'ALX',
        'EBC',
        'RCN-2',
        'SKYM',
        'BTT-2',
        'GBX-2',
        'MIC',
        'SND',
        '1ST',
        'aLEND',
        'aREP',
        'CRBT',
        'EXC-2',
        'DT',
        'CZR',
    ]
    coingecko = Coingecko(data_directory=data_dir)
    all_coins = coingecko.all_coins()

    for identifier, asset_data in AssetResolver().assets.items():
        if identifier in coins_delisted_from_coingecko:
            # data = coingecko.asset_data(Asset(identifier))
            # Figure out if the removed assets can still be queried
            # for historical prices. If not, then remove their mapping from
            # all_assets.json and remove them from this tests.
            continue

        asset_type = asset_type_mapping[asset_data['type']]
        if asset_type == AssetType.FIAT:
            continue

        found = True
        coingecko_str = asset_data.get('coingecko', None)
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
                if entry['symbol'].upper() == asset_data['symbol'].upper():
                    suggestions.append((entry['id'], entry['name'], entry['symbol']))
                    continue

                if entry['name'].upper() == asset_data['symbol'].upper():
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
    last_meta = {'md5': '01a9135bedd9eeffb76c6583f98f321a', 'version': 40}
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    data_md5 = file_md5(data_dir / 'all_assets.json')

    with open(data_dir / 'all_assets.meta', 'r') as f:
        saved_meta = json.loads(f.read())

    assert data_md5 == saved_meta['md5']

    if data_md5 != last_meta['md5']:
        msg = (
            'The md5 has changed since the last time assets.json was edited '
            'and the version has not been bumped',
        )
        assert saved_meta['version'] == last_meta['version'] + 1, msg


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
"COMPRLASSET": {
    "coingecko": "",
    "name": "Completely real asset, totally not for testing only",
    "symbol": "COMPRLASSET",
    "type": "not existing type"
}
}"""])
@pytest.mark.parametrize('force_reinitialize_asset_resolver', [True])
def test_asset_with_unknown_type_does_not_crash(asset_resolver):  # pylint: disable=unused-argument
    """Test that finding an asset with an unknown type does not crash Rotki"""
    new_asset = Asset("COMPRLASSET")
    assert new_asset.name == 'Completely real asset, totally not for testing only'
    token_list = AssetResolver().get_all_eth_token_info()
    assert len(token_list) == 0
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
