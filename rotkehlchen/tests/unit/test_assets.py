import warnings as test_warnings

import pytest
from eth_utils import is_checksum_address

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.spam_assets import KNOWN_ETH_SPAM_TOKENS
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import get_or_create_evm_token, symbol_to_ethereum_token
from rotkehlchen.constants.assets import A_DAI, A_USDT
from rotkehlchen.constants.resolver import ChainID, ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.handler import GlobalDBHandler


def test_unknown_asset():
    """Test than an unknown asset will throw"""
    with pytest.raises(UnknownAsset):
        Asset('jsakdjsladjsakdj')


def test_asset_nft():
    a = Asset('_nft_foo')
    assert a.identifier == '_nft_foo'
    assert a.symbol is not None
    assert a.name == 'nft with id _nft_foo'
    assert a.started is not None
    assert a.forked is None
    assert a.swapped_for is None
    assert a.cryptocompare is not None
    assert a.coingecko is None


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
    rdn_asset = EvmToken('eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6')
    assert rdn_asset.evm_address == '0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'
    assert rdn_asset.decimals == 18
    assert rdn_asset.is_evm_token()

    with pytest.raises(DeserializationError):
        EvmToken('BTC')


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
        ethaddress_to_identifier('0x16980b3B4a3f9D89E33311B5aa8f80303E5ca4F8'),  # noqa: E501 # Kira Network (KEX) but another KEX in CC
        'DON',     # Donnie Finance but Donation Coin in CC
        'BAG',     # Baguette but not in CC
        ethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),  # noqa: E501 # Gitcoin (GTC) but another GTC in CC
        ethaddress_to_identifier('0x6D0F5149c502faf215C89ab306ec3E50b15e2892'),  # noqa: E501 # Portion (PRT) but another PRT in CC
        'ANI',     # Animecoin (ANI) but another ANI in CC
        'XEP',     # Electra Protocol (XEP) but another XEP in CC
        ethaddress_to_identifier('0xcbb20D755ABAD34cb4a9b5fF6Dd081C76769f62e'),  # noqa: E501 # Cash Global Coin (CGC) but another CGC in CC
        ethaddress_to_identifier('0x9BE89D2a4cd102D8Fecc6BF9dA793be995C22541'),  # noqa: E501 # Binance Wrapped BTC (BBTC) but another BBTC in CC
        'NRV',     # Nerve Finance (NRV) but another NRV in CC
        'EDR-2',   # Endor Protocol Token but we have E-Dinar Coin
        ethaddress_to_identifier('0xDa007777D86AC6d989cC9f79A73261b3fC5e0DA0'),  # noqa: E501 # Dappnode (NODE) but another NODE in CC
        'QI',  # noqa: E501 # BENQI (QI) but another QI in CC
        ethaddress_to_identifier('0x1A4b46696b2bB4794Eb3D4c26f1c55F9170fa4C5'),  # noqa: E501 # BitDao (BIT) but another BIT in CC
        ethaddress_to_identifier('0x993864E43Caa7F7F12953AD6fEb1d1Ca635B875F'),  # noqa: E501 # Singularity DAO (SDAO) but another SDAO in CC
        ethaddress_to_identifier('0x114f1388fAB456c4bA31B1850b244Eedcd024136'),  # noqa: E501 # Cool Vauld (COOL) but another COOL in CC
        ethaddress_to_identifier('0xD70240Dd62F4ea9a6A2416e0073D72139489d2AA'),  # noqa: E501 # Glyph vault (GLYPH) but another GLYPH in CC
        ethaddress_to_identifier('0x269616D549D7e8Eaa82DFb17028d0B212D11232A'),  # noqa: E501 # PUNK vault (PUNK) but another PUNK in CC
        ethaddress_to_identifier('0x2d94AA3e47d9D5024503Ca8491fcE9A2fB4DA198'),  # noqa: E501 # Bankless token (BANK) but another BANK in CC
        ethaddress_to_identifier('0x1456688345527bE1f37E9e627DA0837D6f08C925'),  # noqa: E501 # USDP stablecoin (USDP) but another USDP in CC
        'POLIS',  # noqa: E501 # Star Atlas DAO (POLIS) but another POLIS in CC
        ethaddress_to_identifier('0x670f9D9a26D3D42030794ff035d35a67AA092ead'),  # noqa: E501 # XBullion Token (GOLD) but another GOLD in CC
        ethaddress_to_identifier('0x3b58c52C03ca5Eb619EBa171091c86C34d603e5f'),  # noqa: E501 # MCI Coin (MCI) but another MCI in CC
        ethaddress_to_identifier('0x5dD57Da40e6866C9FcC34F4b6DDC89F1BA740DfE'),  # noqa: E501 # Bright(BRIGHT) but another BRIGHT in CC
        ethaddress_to_identifier('0x40284109c3309A7C3439111bFD93BF5E0fBB706c'),  # noqa: E501 # Motiv protocol but another MOV in CC
        ethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'),  # noqa: E501 # Super Rare but another RARE in CC
        ethaddress_to_identifier('0x9D65fF81a3c488d585bBfb0Bfe3c7707c7917f54'),  # noqa: E501 # SSV token but another SSV in CC
        ethaddress_to_identifier('0x7b35Ce522CB72e4077BaeB96Cb923A5529764a00'),  # noqa: E501 # Impermax but another IMX in CC
        ethaddress_to_identifier('0x47481c1b44F2A1c0135c45AA402CE4F4dDE4D30e'),  # noqa: E501 # Meetple but another MPT in CC
        'CATE',  # catecoin but another CATE in CC
        'CHESS'  # tranchess but another CHESS in CC
        'BNC',  # Bifrost but another BNC in CC
        'BNX',  # BinaryX but anohter BNX in CC
        'DAR',  # Mines of Dalarnia but a different DAR in CC
        ethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),  # noqa: E501 # Bionic but another BNC in CC
        'CHESS',  # tranchess but another chess in CC
        'BNC',  # bifrost but another BNC in CC
        ethaddress_to_identifier('0x9e6C59321CEB205d5d3BC6c539c017aF6159B16c'),  # noqa: E501 # Mindcell but another MDC in CC
        'TIME',  # Wonderland but another TIME in CC
        'STARS',  # StarLaunch but another STARS in CC
        ethaddress_to_identifier('0x60EF10EDfF6D600cD91caeCA04caED2a2e605Fe5'),  # noqa: E501 # Mochi inu but MOCHI SWAP in CC
        ethaddress_to_identifier('0x3496B523e5C00a4b4150D6721320CdDb234c3079'),  # noqa: E501 # numbers protocol but another NUM in CC
        ethaddress_to_identifier('0x8dB253a1943DdDf1AF9bcF8706ac9A0Ce939d922'),  # noqa: E501 # unbound protocol but another UNB in CC
        'GODZ',  # gozilla but another GODZ in CC
        'DFL',  # Defi land but another DFL in CC
        'CDEX',  # Codex but another CDEX in CC
        'MIMO',  # mimosa but another MIMO in CC
        ethaddress_to_identifier('0x73d7c860998CA3c01Ce8c808F5577d94d545d1b4'),  # noqa: E501 # IXS token but IXS swap in CC
        'TULIP',  # Solfarm but TULIP project in CC
        'AIR',  # altair but another AIR in CC
        ethaddress_to_identifier('0xfC1Cb4920dC1110fD61AfaB75Cf085C1f871b8C6'),  # noqa: E501 # edenloop but cc has electron
        ethaddress_to_identifier('0x3392D8A60B77F8d3eAa4FB58F09d835bD31ADD29'),  # noqa: E501 # indiegg but cc has indicoin
        'NBT',  # nanobyte but cc has nix bridge
        'NHCT',  # Hurricane nft but cc has nano healthcare
        'ZBC',  # zebec but cc has zilbercoin
        'MINE',  # spacemine but cc has instamine
        'SIN',  # sincity but cc has sinnoverse
        'GST-2',  # green satoshi coin but cc has gstcoin
        ethaddress_to_identifier('0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),  # noqa: E501 # gearbox but cc has metagear
        ethaddress_to_identifier('0xA68Dd8cB83097765263AdAD881Af6eeD479c4a33'),  # noqa: E501 # fees.wtf but cc has WTF token
        'AUSD',  # alpaca usd but cc has appeal dollar
        'PLY',  # Aurigami but cc has playcoin
        'MLS',  # Pikaster but cc has crop
        ethaddress_to_identifier('0xcCeD5B8288086BE8c38E23567e684C3740be4D48'),  # noqa: E501 # rouletteToken but cc has Runner land
        ethaddress_to_identifier('0xb4bebD34f6DaaFd808f73De0d10235a92Fbb6c3D'),  # noqa: E501 # Yearn index but cc has yeti finance
        ethaddress_to_identifier('0xC76FB75950536d98FA62ea968E1D6B45ffea2A55'),  # noqa: E501 # Unit protocol but cc has clash of lilliput
        ethaddress_to_identifier('0xbc6E06778708177a18210181b073DA747C88490a'),  # noqa: E501 # Syndicate but cc has mobland
        ethaddress_to_identifier('0x23894DC9da6c94ECb439911cAF7d337746575A72'),  # noqa: E501 # geojam but cc has tune.fm
        'WELL',  # Moonwell but cc has well
        ethaddress_to_identifier('0xeEd4d7316a04ee59de3d301A384262FFbDbd589a'),  # noqa: E501 # Page network but cc has PhiGold
        ethaddress_to_identifier('0xbb70AdbE39408cB1E5258702ea8ADa7c81165b73'),  # noqa: E501 # AnteDao but cc has ante
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
        if not asset_data.asset_type == AssetType.EVM_TOKEN:
            continue

        msg = (
            f'Ethereum token\'s {asset_data.name} ethereum address '
            f'is not checksummed {asset_data.evm_address}'
        )
        assert is_checksum_address(asset_data.evm_address), msg


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


def test_coingecko_identifiers_are_reachable():
    """
    Test that all assets have a coingecko entry and that all the identifiers exist in coingecko
    """
    coingecko = Coingecko()
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
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0xFD25676Fc2c4421778B18Ec7Ab86E7C5701DF187'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0xcca0c9c383076649604eE31b20248BC04FdF61cA'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0xAef38fBFBF932D1AeF3B808Bc8fBd8Cd8E1f8BC5'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0x662aBcAd0b7f345AB7FfB1b1fbb9Df7894f18e66'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0x497bAEF294c11a5f0f5Bea3f2AdB3073DB448B56'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0xAbdf147870235FcFC34153828c769A70B3FAe01F'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0x4DF47B4969B2911C966506E3592c41389493953b'),
        # Token suggestion doesn't match token in db
        ethaddress_to_identifier('0xB563300A3BAc79FC09B93b6F84CE0d4465A2AC27'),
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
        'MUSIC',  # Music in coingecko is nftmusic and not our MUSIC
        'NAUT',  # Token suggestion doesn't match token in db
        'OCC',  # no Octoin Coin in Coingecko. Got other OCC symbol token
        'SPA',  # no SpainCoin Coin in Coingecko. Got other SPA symbol token
        'WEB-2',  # no Webchain in Coingecko. Got other WEB symbol token
        'WOLF',  # no Insanity Coin in Coingecko. Got other WOLF symbol token
        'XAI',  # Token suggestion doesn't match token in db
        'XPB',  # no Pebble Coin in Coingecko. Got other XPB symbol token
        'XNS',  # no Insolar in Coingecko. Got other XNS symbol token
        'PIGGY',  # Coingecko listed another asset PIGGY that is not Piggy Coin
        # coingecko listed CAR that is not our token CarBlock.io
        ethaddress_to_identifier('0x4D9e23a3842fE7Eb7682B9725cF6c507C424A41B'),
        # coingecko listed newb farm with symbol NEWB that is not our newb
        ethaddress_to_identifier('0x5A63Eb358a751b76e58325eadD86c2473fC40e87'),
        # coingecko has BigBang Core (BBC) that is not tradove
        ethaddress_to_identifier('0xe7D3e4413E29ae35B0893140F4500965c74365e5'),
        # MNT is Meownaut in coingecko and not media network token
        ethaddress_to_identifier('0xA9877b1e05D035899131DBd1e403825166D09f92'),
        # Project quantum in coingecko but we have Qubitica
        ethaddress_to_identifier('0xCb5ea3c190d8f82DEADF7ce5Af855dDbf33e3962'),
        # We have Cashbery Coin for symbol CBC that is not listed in the coingecko list
        'CBC-2',
        # We have Air token for symbol AIR. Got another AIR symbol token
        ethaddress_to_identifier('0x27Dce1eC4d3f72C3E457Cc50354f1F975dDEf488'),
        # We have Acorn Collective for symbol OAK. Got another OAK symbol token
        ethaddress_to_identifier('0x5e888B83B7287EED4fB7DA7b7d0A0D4c735d94b3'),
        # Coingecko has yearn v1 vault yUSD
        ethaddress_to_identifier('0x0ff3773a6984aD900f7FB23A9acbf07AC3aDFB06'),
        # Coingecko has yearn v1 vault yUSD (different vault from above but same symbol)
        ethaddress_to_identifier('0x4B5BfD52124784745c1071dcB244C6688d2533d3'),
        # Coingecko has Aston Martin Cognizant Fan Token and we have AeroME
        'AM',
        # Coingecko has Swarm (BZZ) and we have SwarmCoin
        'SWARM',
        # Coingecko has aircoin and we have a different airtoken
        'AIR-2',
        # Coingecko has Attlas Token and we have Authorship
        ethaddress_to_identifier('0x2dAEE1AA61D60A252DC80564499A69802853583A'),
        # Coingecko has Lever Network and we have Leverj
        ethaddress_to_identifier('0x0F4CA92660Efad97a9a70CB0fe969c755439772C'),
        # Coingecko has Twirl Governance Token and we have Target Coin
        ethaddress_to_identifier('0xAc3Da587eac229C9896D919aBC235CA4Fd7f72c1'),
        # Coingecko has MyWish and we have another WISH (ethereum addresses don't match)
        ethaddress_to_identifier('0x1b22C32cD936cB97C28C5690a0695a82Abf688e6'),
        # Coingecko has DroneFly and we have KlondikeCoin for symbol KDC
        'KDC',
        # Coingecko has CoinStarter and we have Student Coin for symbol STC
        ethaddress_to_identifier('0x15B543e986b8c34074DFc9901136d9355a537e7E'),
        # Coingecko has Nano Dogecoin symbol:ndc and we have NEVERDIE
        ethaddress_to_identifier('0xA54ddC7B3CcE7FC8b1E3Fa0256D0DB80D2c10970'),
        # Coingecko has olecoin and we have Olive
        ethaddress_to_identifier('0x9d9223436dDD466FC247e9dbbD20207e640fEf58'),
        # Coingecko has orica and we have origami
        ethaddress_to_identifier('0xd2Fa8f92Ea72AbB35dBD6DECa57173d22db2BA49'),
        # Coingeckop has a different storm token
        ethaddress_to_identifier('0xD0a4b8946Cb52f0661273bfbC6fD0E0C75Fc6433'),
        # We have Centra (CTR) but coingecko has creator platform
        ethaddress_to_identifier('0x96A65609a7B84E8842732DEB08f56C3E21aC6f8a'),
        # We have Gladius Token (GLA) but coingecko has Galaxy adventure
        ethaddress_to_identifier('0x71D01dB8d6a2fBEa7f8d434599C237980C234e4C'),
        # We have reftoken (REF) and coingecko has Ref Finance
        ethaddress_to_identifier('0x89303500a7Abfb178B274FD89F2469C264951e1f'),
        # We have Aidus (AID) and coingecko has aidcoin
        ethaddress_to_identifier('0xD178b20c6007572bD1FD01D205cC20D32B4A6015'),
        # We have depository network but coingecko has depo
        ethaddress_to_identifier('0x89cbeAC5E8A13F0Ebb4C74fAdFC69bE81A501106'),
        # Sinthetic ETH but coingecko has iEthereum
        ethaddress_to_identifier('0xA9859874e1743A32409f75bB11549892138BBA1E'),
        # blocklancer but coingecko has Linker
        ethaddress_to_identifier('0x63e634330A20150DbB61B15648bC73855d6CCF07'),
        # Kora network but coingecko Knekted
        ethaddress_to_identifier('0xfF5c25D2F40B47C4a37f989DE933E26562Ef0Ac0'),
        # gambit but coingecko has another gambit
        ethaddress_to_identifier('0xF67451Dc8421F0e0afEB52faa8101034ed081Ed9'),
        # publica but coingecko has another polkalab
        ethaddress_to_identifier('0x55648De19836338549130B1af587F16beA46F66B'),
        # Spin protocol but spinada in coingecko
        ethaddress_to_identifier('0x4F22310C27eF39FEAA4A756027896DC382F0b5E2'),
        # REBL but another REBL (rebel finance) in coingecko
        ethaddress_to_identifier('0x5F53f7A8075614b699Baad0bC2c899f4bAd8FBBF'),
        # Sp8de (SPX) but another SPX in coingecko
        ethaddress_to_identifier('0x05aAaA829Afa407D83315cDED1d45EB16025910c'),
        # marginless but another MRS in coingecko
        ethaddress_to_identifier('0x1254E59712e6e727dC71E0E3121Ae952b2c4c3b6'),
        # oyster (PRL) but another PRL in coingecko
        ethaddress_to_identifier('0x1844b21593262668B7248d0f57a220CaaBA46ab9'),
        # oyster shell but another SHL in coingecko
        ethaddress_to_identifier('0x8542325B72C6D9fC0aD2Ca965A78435413a915A0'),
        # dorado but another DOR in coingecko
        ethaddress_to_identifier('0x906b3f8b7845840188Eab53c3f5AD348A787752f'),
        # FundYourselfNow but coingecko has affyn
        ethaddress_to_identifier('0x88FCFBc22C6d3dBaa25aF478C578978339BDe77a'),
        # hat exchange but coingecko has joe hat token
        ethaddress_to_identifier('0x9002D4485b7594e3E850F0a206713B305113f69e'),
        # iconomi but coingecko has icon v2
        ethaddress_to_identifier('0x888666CA69E0f178DED6D75b5726Cee99A87D698'),
        # we have mcap and coingecko has meta capital
        ethaddress_to_identifier('0x93E682107d1E9defB0b5ee701C71707a4B2E46Bc'),
        # we have primalbase but coingecko has property blockchain
        ethaddress_to_identifier('0xF4c07b1865bC326A3c01339492Ca7538FD038Cc0'),
        # Sphere Identity and coingecko has Xid Network
        ethaddress_to_identifier('0xB110eC7B1dcb8FAB8dEDbf28f53Bc63eA5BEdd84'),
        # We have ultracoin and coingecko has unitech
        'UTC',
        # We have sonic and coingecko has secretworld
        'SSD',
        # We have shadowchash and coingecko has skydos
        'SDC',
        # We have getgems and coingecko has battlemerchs
        'GEMZ',
        # We have breackout and coingecko has blueark
        'BRK',
        # We have aerocoin and coingecko has aerochain
        'AERO',
        # coingecko has prime dai and we have pickle dai
        ethaddress_to_identifier('0x6949Bb624E8e8A90F87cD2058139fcd77D2F3F87'),
        # sinovate but we have sincity
        'SIN',
        # Hedge protocol but we have Hede crypto coin (book)
        ethaddress_to_identifier('0xfFe8196bc259E8dEDc544d935786Aa4709eC3E64'),
        # realchain but coingecko has reactor
        ethaddress_to_identifier('0x13f25cd52b21650caa8225C9942337d914C9B030'),
        # we have plutusdefi (usde) but coingecko has energi dollar
        'USDE',
        # gearbox is not returned by the coingecko api
        ethaddress_to_identifier('0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
        # bitcoindark bu coingecko has bitdollars
        'BTCD',
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
            found = coingecko_str in all_coins

        suggestions = []
        if not found:
            for cc_id, entry in all_coins.items():
                if entry['symbol'].upper() == asset_data.symbol.upper():
                    suggestions.append((cc_id, entry['name'], entry['symbol']))
                    continue

                if entry['name'].upper() == asset_data.symbol.upper():
                    suggestions.append((cc_id, entry['name'], entry['symbol']))
                    continue

        if have_id is False and (len(suggestions) == 0 or identifier in symbol_checked_exceptions):
            continue  # no coingecko identifier and no suggestion or is in known exception

        msg = f'Asset {identifier} with symbol {asset_data.symbol} coingecko mapping does not exist.'  # noqa: E501
        if len(suggestions) != 0:
            for s in suggestions:
                msg += f'\nSuggestion: id:{s[0]} name:{s[1]} symbol:{s[2]}'
        if not found:
            test_warnings.warn(UserWarning(msg))


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
    """Test that finding an asset with an unknown type does not crash rotki"""
    with pytest.raises(UnknownAsset):
        Asset('COMPRLASSET2')
    # After the test runs we must reset the asset resolver so that it goes back to
    # the normal list of assets
    AssetResolver._AssetResolver__instance = None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('force_reinitialize_asset_resolver', [True])
def test_get_or_create_evm_token(globaldb, database):
    cursor = globaldb.conn.cursor()
    assets_num = cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0]
    assert A_DAI == get_or_create_evm_token(
        userdb=database,
        symbol='DAI',
        evm_address='0x6B175474E89094C44Da98b954EedeAC495271d0F',
        chain=ChainID.ETHEREUM,
    )
    # Try getting a DAI token of a different address. Shold add new token to DB
    new_token = get_or_create_evm_token(
        userdb=database,
        symbol='DAI',
        evm_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
        chain=ChainID.ETHEREUM,
    )
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 1
    assert new_token.symbol == 'DAI'
    assert new_token.evm_address == '0xA379B8204A49A72FF9703e18eE61402FAfCCdD60'
    # Try getting a symbol of normal chain with different address. Should add new token to DB
    new_token = get_or_create_evm_token(
        userdb=database,
        symbol='DOT',
        evm_address='0xB179B8204A49672FF9703e18eE61402FAfCCdD60',
        chain=ChainID.ETHEREUM,
    )
    assert new_token.symbol == 'DOT'
    assert new_token.evm_address == '0xB179B8204A49672FF9703e18eE61402FAfCCdD60'
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2
    # Check that token with wrong symbol but existing address is returned
    assert A_USDT == get_or_create_evm_token(
        userdb=database,
        symbol='ROFL',
        evm_address='0xdAC17F958D2ee523a2206206994597C13D831ec7',
        chain=ChainID.ETHEREUM,
    )
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2


def test_spam_assets_are_valid():
    """Test that the information for our own list of spam assets is correct"""
    for address, info in KNOWN_ETH_SPAM_TOKENS.items():
        assert is_checksum_address(address)
        assert 'name' in info
        assert 'symbol' in info
        assert 'decimals' in info
