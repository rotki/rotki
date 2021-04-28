import json
import warnings as test_warnings
from pathlib import Path

import pytest
from eth_utils import is_checksum_address

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import get_ethereum_token, symbol_to_ethereum_token
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors import InputError, UnknownAsset
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler
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
    rdn_asset = EthereumToken('0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6')
    assert rdn_asset.ethereum_address == '0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'
    assert rdn_asset.decimals == 18
    assert rdn_asset.is_eth_token()

    with pytest.raises(UnknownAsset):
        EthereumToken('BTC')


def test_cryptocompare_asset_support(cryptocompare):
    """Try to detect if a token that we have as not supported by cryptocompare got added"""
    cc_assets = cryptocompare.all_coins()
    exceptions = (
        ethaddress_to_identifier('0xc88Be04c809856B75E3DfE19eB4dCf0a3B15317a'),  # noqa: E501 # Bankcoin Cash but Balkan Coin in CC
        ethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),     # noqa: E501 # Bionic but Benja Coin in CC
        'BTG-2',   # Bitgem but Bitcoin Gold in CC
        ethaddress_to_identifier('0x499A6B77bc25C26bCf8265E2102B1B3dd1617024'),  # noqa: E501 # Bitether but Bither in CC
        'CBC-2',   # Cashbery coin but Casino Betting Coin in CC
        ethaddress_to_identifier('0x17B26400621695c2D8C2D8869f6259E82D7544c4'),  # noqa: E501 #  CustomContractnetwork but CannaCoin in CC
        ethaddress_to_identifier('0xa456b515303B2Ce344E9d2601f91270f8c2Fea5E'),  # noqa: E501 # Cornichon but Corn in CC
        'CTX',     # Centauri coin but CarTaxi in CC
        ethaddress_to_identifier('0xf14922001A2FB8541a433905437ae954419C2439'),  # noqa: E501 # Direct insurance token but DitCoin in CC
        'DRM',     # Dreamcoin but Dreamchain in CC
        ethaddress_to_identifier('0x82fdedfB7635441aA5A92791D001fA7388da8025'),  # noqa: E501 # Digital Ticks but Data Exchange in CC
        'GNC',     # Galaxy network but Greencoin in CC
        ethaddress_to_identifier('0xfF5c25D2F40B47C4a37f989DE933E26562Ef0Ac0'),  # noqa: E501 # Kora network but Knekted in CC
        ethaddress_to_identifier('0x49bD2DA75b1F7AF1E4dFd6b1125FEcDe59dBec58'),  # noqa: E501 # Linkey but LuckyCoin in CC
        ethaddress_to_identifier('0x5D4d57cd06Fa7fe99e26fdc481b468f77f05073C'),  # noqa: E501 # Netkoin but Neurotoken in CC
        ethaddress_to_identifier('0xD56daC73A4d6766464b38ec6D91eB45Ce7457c44'),  # noqa: E501 # Panvala but Pantos in CC
        ethaddress_to_identifier('0x4689a4e169eB39cC9078C0940e21ff1Aa8A39B9C'),  # noqa: E501 # Proton token but Pink Taxi Token in CC
        ethaddress_to_identifier('0x7Dc4f41294697a7903C4027f6Ac528C5d14cd7eB'),  # noqa: E501 # Remicoin but Russian Miner Coin in CC
        ethaddress_to_identifier('0xBb1f24C0c1554b9990222f036b0AaD6Ee4CAec29'),  # noqa: E501 # Cryptosoul but Phantasma in CC
        ethaddress_to_identifier('0x72430A612Adc007c50e3b6946dBb1Bb0fd3101D1'),  # noqa: E501 # Thingschain but True Investment Coin in CC
        ethaddress_to_identifier('0x9a49f02e128a8E989b443a8f94843C0918BF45E7'),  # noqa: E501 # TOKOK but Tokugawa Coin in CC
        ethaddress_to_identifier('0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D'),  # noqa: E501 # Bitcoin card but Vindax Coin in CC
        ethaddress_to_identifier('0x1da015eA4AD2d3e5586E54b9fB0682Ca3CA8A17a'),  # noqa: E501 # Dragon Token but Dark Token in CC
        ethaddress_to_identifier('0x9C78EE466D6Cb57A4d01Fd887D2b5dFb2D46288f'),  # noqa: E501 # Must (Cometh) but Must protocol in CC
        ethaddress_to_identifier('0x73968b9a57c6E53d41345FD57a6E6ae27d6CDB2F'),  # noqa: E501 # Stake DAO token but TerraSDT in CC
        ethaddress_to_identifier('0x3449FC1Cd036255BA1EB19d65fF4BA2b8903A69a'),  # noqa: E501 # Basis Cash but BACoin in CC
        ethaddress_to_identifier('0xaF1250fa68D7DECD34fD75dE8742Bc03B29BD58e'),  # noqa: E501 # waiting until cryptocompare fixes historical price for this. https://github.com/rotki/rotki/pull/2176
        'FLOW',    # FLOW from dapper labs but "Flow Protocol" in CC
        ethaddress_to_identifier('0x8A9c4dfe8b9D8962B31e4e16F8321C44d48e246E'),  # noqa: E501 # Name change token but Polyswarm in CC
        ethaddress_to_identifier('0x1966d718A565566e8E202792658D7b5Ff4ECe469'),  # noqa: E501 # newdex token but Index token in CC
        ethaddress_to_identifier('0x1F3f9D3068568F8040775be2e8C03C103C61f3aF'),  # noqa: E501 # Archer DAO Governance token but Archcoin in CC
        ethaddress_to_identifier('0x9A0aBA393aac4dFbFf4333B06c407458002C6183'),  # noqa: E501 # Acoconut token but Asiacoin in CC
        ethaddress_to_identifier('0x6a6c2adA3Ce053561C2FbC3eE211F23d9b8C520a'),  # noqa: E501 # Tontoken but Tokamak network in CC
        ethaddress_to_identifier('0xB5FE099475d3030DDe498c3BB6F3854F762A48Ad'),  # noqa: E501 # Finiko token but FunKeyPai network in CC
        ethaddress_to_identifier('0xb0dFd28d3CF7A5897C694904Ace292539242f858'),  # noqa: E501 # Lotto token but LottoCoin in CC
        ethaddress_to_identifier('0xE4E822C0d5b329E8BB637972467d2E313824eFA0'),  # noqa: E501 # Dfinance token but XFinance in CC
        ethaddress_to_identifier('0xE081b71Ed098FBe1108EA48e235b74F122272E68'),  # noqa: E501 # Gold token but Golden Goose in CC
        'ACM',     # AC Milan Fan Token but Actinium in CC
        'TFC',     # TheFutbolCoin but The Freedom Coin in CC
        ethaddress_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'),  # noqa: E501 # Mask Network but NFTX Hashmask Index in CC
        ethaddress_to_identifier('0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14'),  # noqa: E501 # balanced crypto pie but 0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14 in CC
        ethaddress_to_identifier('0x7aBc60B3290F68c85f495fD2e0c3Bd278837a313'),  # noqa: E501 # Cyber Movie Chain but Crowdmachine in CC
        ethaddress_to_identifier('0xBAE235823D7255D9D48635cEd4735227244Cd583'),  # noqa: E501 # Staker Token but Gateio Stater in CC
        ethaddress_to_identifier('0xe2DA716381d7E0032CECaA5046b34223fC3f218D'),  # noqa: E501 # Carbon Utility Token but CUTCoin in CC
        ethaddress_to_identifier('0x1FA3bc860bF823d792f04F662f3AA3a500a68814'),  # noqa: E501 # 1X Short Bitcoin Token but Hedgecoin in CC
        ethaddress_to_identifier('0xc7283b66Eb1EB5FB86327f08e1B5816b0720212B'),  # noqa: E501 # Tribe Token (FEI) but another TribeToken in CC
        'DON',     # Donnie Finance but Donation Coin in CC
    )
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        potential_support = (
            asset_data.cryptocompare == '' and
            asset_data.symbol in cc_assets and
            asset_data.identifier not in exceptions
        )
        if potential_support:
            msg = (
                f'We have {asset_data.identifier} with symbol {asset_data.symbol} as not supported'
                f' by cryptocompare but the symbol appears in its supported assets'
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
    a1 = Asset('bTc')
    a2 = Asset('BTC')
    assert a1 == a2
    assert a1.identifier == 'BTC'
    assert a2.identifier == 'BTC'

    a3 = symbol_to_ethereum_token('UsDt')
    a4 = symbol_to_ethereum_token('usdt')
    assert a3.identifier == a4.identifier == ethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7')  # noqa: E501


def test_coingecko_identifiers_are_reachable(data_dir):
    """
    Test that all assets have a coingecko entry and that all the identifiers exist in coingecko
    """
    coingecko = Coingecko(data_directory=data_dir)
    all_coins = coingecko.all_coins()
    # If coingecko identifier is missing test is trying to suggest possible assets.
    symbol_checked_exceptions = (  # This is the list of already checked assets
        # only 300 in coingecko is spartan coin: https://www.coingecko.com/en/coins/spartan
        ethaddress_to_identifier('0xaEc98A708810414878c3BCDF46Aad31dEd4a4557'),
        # no arcade city in coingeko. Got other ARC symbol tokens
        ethaddress_to_identifier('0xAc709FcB44a43c35F0DA4e3163b117A17F3770f5'),
        # no avalon in coingecko. Got travalala.com
        ethaddress_to_identifier('0xeD247980396B10169BB1d36f6e278eD16700a60f'),
        # no Bionic in coingecko. Got Bnoincoin
        ethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),
        # no Bitair in coingecko. Got other BTCA symbol tokens
        ethaddress_to_identifier('0x02725836ebF3eCDb1cDf1c7b02FcbBfaa2736AF8'),
        # no Bither in coingecko. Got other BTR symbol tokens
        ethaddress_to_identifier('0xcbf15FB8246F679F9Df0135881CB29a3746f734b'),
        # no Content and Ad Network in coingecko. Got other CAN symbol tokens
        ethaddress_to_identifier('0x5f3789907b35DCe5605b00C0bE0a7eCDBFa8A841'),
        # no DICE money in coingecko. Got other CET symbol tokens
        ethaddress_to_identifier('0xF660cA1e228e7BE1fA8B4f5583145E31147FB577'),
        # no Cyberfi in coingecko. Got other CFI symbol tokens
        ethaddress_to_identifier('0x12FEF5e57bF45873Cd9B62E9DBd7BFb99e32D73e'),
        # The DAO is not in coingecko. Got other DAO symbol tokens
        ethaddress_to_identifier('0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413'),
        # no Earth Token in coingecko. Got other EARTH symbol token and in BSC
        ethaddress_to_identifier('0x900b4449236a7bb26b286601dD14d2bDe7a6aC6c'),
        # no iDice in coingecko. Got other ICE symbol token
        ethaddress_to_identifier('0x5a84969bb663fb64F6d015DcF9F622Aedc796750'),
        # no InvestFeed token in coingecko. Got other IFT symbol token
        ethaddress_to_identifier('0x7654915A1b82D6D2D0AFc37c52Af556eA8983c7E'),
        # no Invacio token in coingecko. Got other INV symbol token
        ethaddress_to_identifier('0xEcE83617Db208Ad255Ad4f45Daf81E25137535bb'),
        # no Live Start token in coingecko. Got other LIVE symbol token
        ethaddress_to_identifier('0x24A77c1F17C547105E14813e517be06b0040aa76'),
        # no Musiconomi in coingecko. Got other MCI symbol token
        ethaddress_to_identifier('0x138A8752093F4f9a79AaeDF48d4B9248fab93c9C'),
        # no Remicoin in coingecko. Got other RMC symbol token
        ethaddress_to_identifier('0x7Dc4f41294697a7903C4027f6Ac528C5d14cd7eB'),
        # no Sola token in coingecko. Got other SOL symbol token
        ethaddress_to_identifier('0x1F54638b7737193FFd86c19Ec51907A7c41755D8'),
        # no Bitcoin card token in coingecko. Got other VD symbol token
        ethaddress_to_identifier('0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D'),
        # no Venus Energy token in coingecko. Got other VENUS symbol token
        ethaddress_to_identifier('0xEbeD4fF9fe34413db8fC8294556BBD1528a4DAca'),
        # no WinToken in coingecko. Got other WIN symbol token
        ethaddress_to_identifier('0xBfaA8cF522136C6FAfC1D53Fe4b85b4603c765b8'),
        # no Snowball in coingecko. Got other SNBL symbol token
        ethaddress_to_identifier('0x198A87b3114143913d4229Fb0f6D4BCb44aa8AFF'),
        'ACC',  # no Adcoin in Coingecko. Got other ACC symbol token
        'APH',  # no Aphelion in Coingecko. Got other APH symbol token
        'ARCH',  # no ARCH in Coingecko. Got other ARCH symbol token
        'BET-2',  # no BetaCoin in Coingecko. Got other BET symbol token
        'CCN-2',  # no CannaCoin in Coingecko. Got other CCN symbol token
        'CHAT',  # no ChatCoin in Coingecko. Got other CHAT symbol token
        'CMT-2',  # no Comet in Coingecko. Got other CMT symbol token
        'CRC-2',  # no CrownCoin in Coingecko. Got other CRC symbol token
        'CYC',  # no ConspiracyCoin in Coingecko. Got other CYC symbol token
        'EDR-2',  # no E-Dinar coin in Coingecko. Got other EDR symbol token
        'FLAP',  # no FlappyCoin coin in Coingecko. Got other FLAP symbol token
        'HC-2',  # no Harvest Masternode Coin in Coingecko. Got other HC symbol token
        'KEY-3',  # no KeyCoin Coin in Coingecko. Got other KEY symbol token
        'OCC',  # no Octoin Coin in Coingecko. Got other OCC symbol token
        'SPA',  # no SpainCoin Coin in Coingecko. Got other SPA symbol token
        'WEB-2',  # no Webchain in Coingecko. Got other WEB symbol token
        'WOLF',  # no Insanity Coin in Coingecko. Got other WOLF symbol token
        'XPB',  # no Pebble Coin in Coingecko. Got other XPB symbol token
        'XNS',  # no Insolar in Coingecko. Got other XNS symbol token
    )
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        identifier = asset_data.identifier
        if identifier in DELISTED_ASSETS:
            # delisted assets won't be in the mapping
            continue

        if asset_data.asset_type == AssetType.FIAT:
            continue

        found = True
        coingecko_str = asset_data.coingecko
        have_id = True
        if coingecko_str is not None or coingecko_str != '':
            have_id = False
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

        if have_id is False and (len(suggestions) == 0 or identifier in symbol_checked_exceptions):
            continue  # no coingecko identifier and no suggestion or is in known exception

        msg = f'Asset {identifier} with symbol {asset_data.symbol} coingecko mapping does not exist.'  # noqa: E501
        if len(suggestions) != 0:
            for s in suggestions:
                msg += f'\nSuggestion: id:{s[0]} name:{s[1]} symbol:{s[2]}'
        if not found:
            test_warnings.warn(UserWarning(msg))


def test_assets_json_meta():
    """Test that all_assets.json md5 matches and that if md5 changes since last
    time then version is also bumped"""
    last_meta = {'md5': '51bddc1b4e8bd6d30027c4380cdf9d4f', 'version': 72}
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
