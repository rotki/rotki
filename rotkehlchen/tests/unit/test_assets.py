import os
import shutil
import warnings as test_warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest.mock import PropertyMock, patch

import pytest
import rsqlite
from eth_utils import is_checksum_address

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, CryptoAsset, CustomAsset, EvmToken, FiatAsset, Nft
from rotkehlchen.assets.converters import asset_from_nexo
from rotkehlchen.assets.ignored_assets_handling import IgnoredAssetsHandling
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import (
    get_crypto_asset_by_symbol,
    get_or_create_evm_token,
)
from rotkehlchen.constants.assets import A_DAI, A_USDT
from rotkehlchen.constants.misc import GLOBALDB_NAME
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.constants.timing import SPAM_ASSETS_DETECTION_REFRESH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.filtering import AssetsFilterQuery
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tasks.assets import autodetect_spam_assets_in_db
from rotkehlchen.tasks.manager import should_run_periodic_task
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SPAM_PROTOCOL, CacheType, ChainID, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def test_unknown_asset():
    """Test than an unknown asset will throw"""
    with pytest.raises(UnknownAsset):
        FiatAsset('jsakdjsladjsakdj')


def test_asset_nft():
    a = Asset('_nft_foo')
    assert a.identifier == '_nft_foo'
    should_not_exist = {'name', 'symbol', 'started', 'forked', 'swapped_for', 'cryptocompare', 'coingecko'}  # noqa: E501
    assert len(should_not_exist & a.__dict__.keys()) == 0


def test_repr():
    btc_repr = repr(CryptoAsset('BTC'))
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

    with pytest.raises(WrongAssetType):
        EvmToken('BTC')


@pytest.mark.asset_test
def test_cryptocompare_asset_support(cryptocompare):
    """Try to detect if a token that we have as not supported by cryptocompare got added"""
    cc_assets = cryptocompare.all_coins()
    exceptions = (
        strethaddress_to_identifier('0xc88Be04c809856B75E3DfE19eB4dCf0a3B15317a'),  # Bankcoin Cash but Balkan Coin in CC  # noqa: E501
        strethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),  # Bionic but Benja Coin in CC  # noqa: E501
        'BTG-2',  # Bitgem but Bitcoin Gold in CC
        strethaddress_to_identifier('0x499A6B77bc25C26bCf8265E2102B1B3dd1617024'),  # Bitether but Bither in CC  # noqa: E501
        'CBC-2',  # Cashbery coin but Casino Betting Coin in CC
        strethaddress_to_identifier('0x17B26400621695c2D8C2D8869f6259E82D7544c4'),  # CustomContractnetwork but CannaCoin in CC  # noqa: E501
        strethaddress_to_identifier('0xa456b515303B2Ce344E9d2601f91270f8c2Fea5E'),  # Cornichon but Corn in CC  # noqa: E501
        'CTX',  # Centauri coin but CarTaxi in CC
        strethaddress_to_identifier('0xf14922001A2FB8541a433905437ae954419C2439'),  # Direct insurance token but DitCoin in CC  # noqa: E501
        'DRM',  # Dreamcoin but Dreamchain in CC
        strethaddress_to_identifier('0x82fdedfB7635441aA5A92791D001fA7388da8025'),  # Digital Ticks but Data Exchange in CC  # noqa: E501
        'GNC',  # Galaxy network but Greencoin in CC
        strethaddress_to_identifier('0xfF5c25D2F40B47C4a37f989DE933E26562Ef0Ac0'),  # Kora network but Knekted in CC  # noqa: E501
        strethaddress_to_identifier('0x49bD2DA75b1F7AF1E4dFd6b1125FEcDe59dBec58'),  # Linkey but LuckyCoin in CC  # noqa: E501
        strethaddress_to_identifier('0x5D4d57cd06Fa7fe99e26fdc481b468f77f05073C'),  # Netkoin but Neurotoken in CC  # noqa: E501
        strethaddress_to_identifier('0xD56daC73A4d6766464b38ec6D91eB45Ce7457c44'),  # Panvala but Pantos in CC  # noqa: E501
        strethaddress_to_identifier('0x4689a4e169eB39cC9078C0940e21ff1Aa8A39B9C'),  # Proton token but Pink Taxi Token in CC  # noqa: E501
        strethaddress_to_identifier('0x7Dc4f41294697a7903C4027f6Ac528C5d14cd7eB'),  # Remicoin but Russian Miner Coin in CC  # noqa: E501
        strethaddress_to_identifier('0xBb1f24C0c1554b9990222f036b0AaD6Ee4CAec29'),  # Cryptosoul but Phantasma in CC  # noqa: E501
        strethaddress_to_identifier('0x72430A612Adc007c50e3b6946dBb1Bb0fd3101D1'),  # Thingschain but True Investment Coin in CC  # noqa: E501
        strethaddress_to_identifier('0x9a49f02e128a8E989b443a8f94843C0918BF45E7'),  # TOKOK but Tokugawa Coin in CC  # noqa: E501
        strethaddress_to_identifier('0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D'),  # Bitcoin card but Vindax Coin in CC  # noqa: E501
        strethaddress_to_identifier('0x1da015eA4AD2d3e5586E54b9fB0682Ca3CA8A17a'),  # Dragon Token but Dark Token in CC  # noqa: E501
        strethaddress_to_identifier('0x9C78EE466D6Cb57A4d01Fd887D2b5dFb2D46288f'),  # Must (Cometh) but Must protocol in CC  # noqa: E501
        'eip155:137/erc20:0x9C78EE466D6Cb57A4d01Fd887D2b5dFb2D46288f',  # Must (Cometh) but Must protocol in CC  # noqa: E501
        strethaddress_to_identifier('0x73968b9a57c6E53d41345FD57a6E6ae27d6CDB2F'),  # Stake DAO token but TerraSDT in CC  # noqa: E501
        'eip155:137/erc20:0x361A5a4993493cE00f61C32d4EcCA5512b82CE90',  # Stake DAO token but TerraSDT in CC  # noqa: E501
        'eip155:42161/erc20:0x7bA4a00d54A07461D9DB2aEF539e91409943AdC9',  # Stake DAO token but TerraSDT in CC  # noqa: E501
        strethaddress_to_identifier('0x3449FC1Cd036255BA1EB19d65fF4BA2b8903A69a'),  # Basis Cash but BACoin in CC  # noqa: E501
        strethaddress_to_identifier('0xaF1250fa68D7DECD34fD75dE8742Bc03B29BD58e'),  # waiting until cryptocompare fixes historical price for this. https://github.com/rotki/rotki/pull/2176  # noqa: E501
        'FLOW',    # FLOW from dapper labs but "Flow Protocol" in CC
        strethaddress_to_identifier('0x8A9c4dfe8b9D8962B31e4e16F8321C44d48e246E'),  # Name change token but Polyswarm in CC  # noqa: E501
        strethaddress_to_identifier('0x1966d718A565566e8E202792658D7b5Ff4ECe469'),  # newdex token but Index token in CC  # noqa: E501
        strethaddress_to_identifier('0x1F3f9D3068568F8040775be2e8C03C103C61f3aF'),  # Archer DAO Governance token but Archcoin in CC  # noqa: E501
        strethaddress_to_identifier('0x9A0aBA393aac4dFbFf4333B06c407458002C6183'),  # Acoconut token but Asiacoin in CC  # noqa: E501
        strethaddress_to_identifier('0x6a6c2adA3Ce053561C2FbC3eE211F23d9b8C520a'),  # Tontoken but Tokamak network in CC  # noqa: E501
        strethaddress_to_identifier('0xB5FE099475d3030DDe498c3BB6F3854F762A48Ad'),  # Finiko token but FunKeyPai network in CC  # noqa: E501
        strethaddress_to_identifier('0xb0dFd28d3CF7A5897C694904Ace292539242f858'),  # Lotto token but LottoCoin in CC  # noqa: E501
        'eip155:56/erc20:0xF301C8435D4dFA51641f71B0615aDD794b52c8E9',
        strethaddress_to_identifier('0xE4E822C0d5b329E8BB637972467d2E313824eFA0'),  # Dfinance token but XFinance in CC  # noqa: E501
        strethaddress_to_identifier('0xE081b71Ed098FBe1108EA48e235b74F122272E68'),  # Gold token but Golden Goose in CC  # noqa: E501
        'ACM',  # AC Milan Fan Token but Actinium in CC
        'TFC',  # TheFutbolCoin but The Freedom Coin in CC
        strethaddress_to_identifier('0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14'),  # balanced crypto pie but 0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14 in CC  # noqa: E501
        strethaddress_to_identifier('0x7aBc60B3290F68c85f495fD2e0c3Bd278837a313'),  # Cyber Movie Chain but Crowdmachine in CC  # noqa: E501
        strethaddress_to_identifier('0xBAE235823D7255D9D48635cEd4735227244Cd583'),  # Staker Token but Gateio Stater in CC  # noqa: E501
        strethaddress_to_identifier('0xe2DA716381d7E0032CECaA5046b34223fC3f218D'),  # Carbon Utility Token but CUTCoin in CC  # noqa: E501
        strethaddress_to_identifier('0x1FA3bc860bF823d792f04F662f3AA3a500a68814'),  # 1X Short Bitcoin Token but Hedgecoin in CC  # noqa: E501
        strethaddress_to_identifier('0xc7283b66Eb1EB5FB86327f08e1B5816b0720212B'),  # Tribe Token (FEI) but another TribeToken in CC  # noqa: E501
        strethaddress_to_identifier('0x16980b3B4a3f9D89E33311B5aa8f80303E5ca4F8'),  # Kira Network (KEX) but another KEX in CC  # noqa: E501
        'eip155:56/erc20:0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E',  # Kira Network (KEX) but another KEX in CC  # noqa: E501
        'DON',  # Donnie Finance but Donation Coin in CC
        'BAG',  # Baguette but not in CC
        strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),  # Gitcoin (GTC) but another GTC in CC  # noqa: E501
        strethaddress_to_identifier('0x6D0F5149c502faf215C89ab306ec3E50b15e2892'),  # Portion (PRT) but another PRT in CC  # noqa: E501
        'eip155:56/erc20:0xAF00aAc2431b04EF6afD904d19B08D5146e3A9A0',  # Portion (PRT) but another PRT in CC  # noqa: E501
        'eip155:56/erc20:0xaC472D0EED2B8a2f57a6E304eA7eBD8E88D1d36f',  # Animecoin (ANI) but another ANI in CC  # noqa: E501
        'eip155:56/erc20:0xb897D0a0f68800f8Be7D69ffDD1c24b69f57Bf3e',  # Electra Protocol (XEP) but another XEP in CC  # noqa: E501
        strethaddress_to_identifier('0xcbb20D755ABAD34cb4a9b5fF6Dd081C76769f62e'),  # Cash Global Coin (CGC) but another CGC in CC  # noqa: E501
        strethaddress_to_identifier('0x9BE89D2a4cd102D8Fecc6BF9dA793be995C22541'),  # Binance Wrapped BTC (BBTC) but another BBTC in CC  # noqa: E501
        'eip155:56/erc20:0x42F6f551ae042cBe50C739158b4f0CAC0Edb9096',  # Nerve Finance (NRV) but another NRV in CC  # noqa: E501
        'EDR-2',  # Endor Protocol Token but we have E-Dinar Coin
        strethaddress_to_identifier('0xDa007777D86AC6d989cC9f79A73261b3fC5e0DA0'),  # Dappnode (NODE) but another NODE in CC  # noqa: E501
        'QI',  # BENQI (QI) but another QI in CC
        strethaddress_to_identifier('0x1A4b46696b2bB4794Eb3D4c26f1c55F9170fa4C5'),  # BitDao (BIT) but another BIT in CC  # noqa: E501
        strethaddress_to_identifier('0x993864E43Caa7F7F12953AD6fEb1d1Ca635B875F'),  # Singularity DAO (SDAO) but another SDAO in CC  # noqa: E501
        'eip155:56/erc20:0x90Ed8F1dc86388f14b64ba8fb4bbd23099f18240',  # Singularity DAO (SDAO) but another SDAO in CC  # noqa: E501
        strethaddress_to_identifier('0x114f1388fAB456c4bA31B1850b244Eedcd024136'),  # Cool Vauld (COOL) but another COOL in CC  # noqa: E501
        strethaddress_to_identifier('0xD70240Dd62F4ea9a6A2416e0073D72139489d2AA'),  # Glyph vault (GLYPH) but another GLYPH in CC  # noqa: E501
        strethaddress_to_identifier('0x269616D549D7e8Eaa82DFb17028d0B212D11232A'),  # PUNK vault (PUNK) but another PUNK in CC  # noqa: E501
        strethaddress_to_identifier('0x2d94AA3e47d9D5024503Ca8491fcE9A2fB4DA198'),  # Bankless token (BANK) but another BANK in CC  # noqa: E501
        'eip155:137/erc20:0xDB7Cb471dd0b49b29CAB4a1C14d070f27216a0Ab',  # Bankless token (BANK) but another BANK in CC  # noqa: E501
        strethaddress_to_identifier('0x1456688345527bE1f37E9e627DA0837D6f08C925'),  # USDP stablecoin (USDP) but another USDP in CC  # noqa: E501
        'POLIS',  # Star Atlas DAO (POLIS) but another POLIS in CC
        strethaddress_to_identifier('0x670f9D9a26D3D42030794ff035d35a67AA092ead'),  # XBullion Token (GOLD) but another GOLD in CC  # noqa: E501
        strethaddress_to_identifier('0x3b58c52C03ca5Eb619EBa171091c86C34d603e5f'),  # MCI Coin (MCI) but another MCI in CC  # noqa: E501
        strethaddress_to_identifier('0x5dD57Da40e6866C9FcC34F4b6DDC89F1BA740DfE'),  # Bright(BRIGHT) but another BRIGHT in CC  # noqa: E501
        'eip155:100/erc20:0x83FF60E2f93F8eDD0637Ef669C69D5Fb4f64cA8E',  # Bright(BRIGHT) but another BRIGHT in CC  # noqa: E501
        strethaddress_to_identifier('0x40284109c3309A7C3439111bFD93BF5E0fBB706c'),  # Motiv protocol but another MOV in CC  # noqa: E501
        strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'),  # Super Rare but another RARE in CC  # noqa: E501
        strethaddress_to_identifier('0x9D65fF81a3c488d585bBfb0Bfe3c7707c7917f54'),  # SSV token but another SSV in CC  # noqa: E501
        strethaddress_to_identifier('0x7b35Ce522CB72e4077BaeB96Cb923A5529764a00'),  # Impermax but another IMX in CC  # noqa: E501
        'eip155:137/erc20:0x60bB3D364B765C497C8cE50AE0Ae3f0882c5bD05',  # Impermax but another IMX in CC  # noqa: E501
        'eip155:42161/erc20:0x9c67eE39e3C4954396b9142010653F17257dd39C',  # Impermax but another IMX in CC  # noqa: E501
        'eip155:43114/erc20:0xeA6887e4a9CdA1B77E70129E5Fba830CdB5cdDef',  # Impermax but another IMX in CC  # noqa: E501
        strethaddress_to_identifier('0x47481c1b44F2A1c0135c45AA402CE4F4dDE4D30e'),  # Meetple but another MPT in CC  # noqa: E501
        'eip155:56/erc20:0xE4FAE3Faa8300810C835970b9187c268f55D998F',  # catecoin but another CATE in CC  # noqa: E501
        'eip155:56/erc20:0x20de22029ab63cf9A7Cf5fEB2b737Ca1eE4c82A6'  # tranchess but another CHESS in CC  # noqa: E501
        'BNC',  # Bifrost but another BNC in CC
        'eip155:56/erc20:0x8C851d1a123Ff703BD1f9dabe631b69902Df5f97',  # BinaryX but another BNX in CC  # noqa: E501
        'eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978',  # Mines of Dalarnia but a different DAR in CC  # noqa: E501
        strethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),  # Bionic but another BNC in CC  # noqa: E501
        'CHESS',  # tranchess but another chess in CC
        'BNC',  # bifrost but another BNC in CC
        strethaddress_to_identifier('0x9e6C59321CEB205d5d3BC6c539c017aF6159B16c'),  # Mindcell but another MDC in CC  # noqa: E501
        'TIME',  # Wonderland but another TIME in CC
        'STARS',  # StarLaunch but another STARS in CC
        strethaddress_to_identifier('0x60EF10EDfF6D600cD91caeCA04caED2a2e605Fe5'),  # Mochi inu but MOCHI SWAP in CC  # noqa: E501
        strethaddress_to_identifier('0x3496B523e5C00a4b4150D6721320CdDb234c3079'),  # numbers protocol but another NUM in CC  # noqa: E501
        'eip155:56/erc20:0xeCEB87cF00DCBf2D4E2880223743Ff087a995aD9',  # numbers protocol but another NUM in CC  # noqa: E501
        strethaddress_to_identifier('0x8dB253a1943DdDf1AF9bcF8706ac9A0Ce939d922'),  # unbound protocol but another UNB in CC  # noqa: E501
        'eip155:56/erc20:0x301AF3Eff0c904Dc5DdD06FAa808f653474F7FcC',  # unbound protocol but another UNB in CC  # noqa: E501
        'eip155:56/erc20:0xDa4714fEE90Ad7DE50bC185ccD06b175D23906c1',  # gozilla but another GODZ in CC  # noqa: E501
        'DFL',  # Defi land but another DFL in CC
        'CDEX',  # Codex but another CDEX in CC
        'MIMO',  # mimosa but another MIMO in CC
        strethaddress_to_identifier('0x73d7c860998CA3c01Ce8c808F5577d94d545d1b4'),  # IXS token but IXS swap in CC  # noqa: E501
        'TULIP',  # Solfarm but TULIP project in CC
        'AIR',  # altair but another AIR in CC
        strethaddress_to_identifier('0xfC1Cb4920dC1110fD61AfaB75Cf085C1f871b8C6'),  # edenloop but cc has electron  # noqa: E501
        strethaddress_to_identifier('0x3392D8A60B77F8d3eAa4FB58F09d835bD31ADD29'),  # indiegg but cc has indicoin  # noqa: E501
        'NBT',  # nanobyte but cc has nix bridge
        'eip155:43114/erc20:0x3CE2fceC09879af073B53beF5f4D04327a1bC032',  # Hurricane nft but cc has nano healthcare  # noqa: E501
        'ZBC',  # zebec but cc has zilbercoin
        'MINE',  # spacemine but cc has instamine
        'eip155:56/erc20:0x6397de0F9aEDc0F7A8Fa8B438DDE883B9c201010',  # sincity but cc has sinnoverse  # noqa: E501
        'GST-2',  # green satoshi coin but cc has gstcoin
        strethaddress_to_identifier('0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),  # gearbox but cc has metagear  # noqa: E501
        strethaddress_to_identifier('0xA68Dd8cB83097765263AdAD881Af6eeD479c4a33'),  # fees.wtf but cc has WTF token  # noqa: E501
        'AUSD',  # alpaca usd but cc has appeal dollar
        'PLY',  # Aurigami but cc has playcoin
        'MLS',  # Pikaster but cc has crop
        strethaddress_to_identifier('0xcCeD5B8288086BE8c38E23567e684C3740be4D48'),  # rouletteToken but cc has Runner land  # noqa: E501
        strethaddress_to_identifier('0xb4bebD34f6DaaFd808f73De0d10235a92Fbb6c3D'),  # Yearn index but cc has yeti finance  # noqa: E501
        strethaddress_to_identifier('0xC76FB75950536d98FA62ea968E1D6B45ffea2A55'),  # Unit protocol but cc has clash of lilliput  # noqa: E501
        strethaddress_to_identifier('0xbc6E06778708177a18210181b073DA747C88490a'),  # Syndicate but cc has mobland  # noqa: E501
        strethaddress_to_identifier('0x23894DC9da6c94ECb439911cAF7d337746575A72'),  # geojam but cc has tune.fmy  # noqa: E501
        'WELL',  # Moonwell but cc has well
        strethaddress_to_identifier('0xeEd4d7316a04ee59de3d301A384262FFbDbd589a'),  # Page network but cc has PhiGold  # noqa: E501
        strethaddress_to_identifier('0xbb70AdbE39408cB1E5258702ea8ADa7c81165b73'),  # AnteDao but cc has ante  # noqa: E501
        'eip155:56/erc20:0xDCEcf0664C33321CECA2effcE701E710A2D28A3F',  # Alpaca USD but cc has appeal dollar  # noqa: E501
        'GBPT',  # pound but cc has listed poundtoken
        'MNFT',  # mongol NFT but cc has marvelous NFT
        'ETHS',  # Ethereum PoS fork IOU but CC has ethereum script
        'eip155:137/erc20:0xabEDe05598760E399ed7EB24900b30C51788f00F',  # stepwatch but cc has kava swap  # noqa: E501
        'BSX',  # basilixc but cc has bitspace
        'eip155:43114/erc20:0xb54f16fB19478766A268F172C9480f8da1a7c9C3',  # wonderland but a different time in cc  # noqa: E501
        'eip155:56/erc20:0x5F2F6c4C491B690216E0f8Ea753fF49eF4E36ba6',  # Metaland but cc has crops
        strethaddress_to_identifier('0x2620638EDA99F9e7E902Ea24a285456EE9438861'),  # crust storage but cc has consentium  # noqa: E501
        'FB',  # fitbit but cc has fenerbache
        'CMP',  # cadecius but cc has compcoin
        'KUSD',  # kolibri usd but cc has kowala
        strethaddress_to_identifier('0x4b13006980aCB09645131b91D259eaA111eaF5Ba'),  # mycelium but cc has a different one  # noqa: E501
        'eip155:42161/erc20:0xC74fE4c715510Ec2F8C61d70D397B32043F55Abe',  # mycelium but cc has a different one  # noqa: E501
        'eip155:56/erc20:0xfEB4e9B932eF708c498Cc997ABe51D0EE39300cf',  # getkicks but cc has sessia
        strethaddress_to_identifier('0x06450dEe7FD2Fb8E39061434BAbCFC05599a6Fb8'),  # xen crypto but cc has xenxin  # noqa: E501
        strethaddress_to_identifier('0x3593D125a4f7849a1B059E64F4517A86Dd60c95d'),  # mantra dao but cc has another MO  # noqa: E501
        strethaddress_to_identifier('0x9b5161a41B58498Eb9c5FEBf89d60714089d2253'),  # metafinance but cc has meta fighter  # noqa: E501
        strethaddress_to_identifier('0x3593D125a4f7849a1B059E64F4517A86Dd60c95d'),  # metafinance but cc has meta fighter  # noqa: E501
        'eip155:56/erc20:0x186866858aEf38c05829166A7711b37563e15994',    # hold finance but cc has hashflow  # noqa: E501
        'STC',  # starchain but cc has satoshi island
        'KCAL',  # kcal but cc has pantasma energy
        'MC',  # mechaverse but cc has merit circle
        'eip155:250/erc20:0x904f51a2E7eEaf76aaF0418cbAF0B71149686f4A',  # fantom maker but cc has fane mma  # noqa: E501  # spellchecker:disable-line
        'ARG',  # argentina fc token but cc has argentum
        'eip155:56/erc20:0x9df90628D40c72F85137e8cEE09dde353a651266',  # mechaverse but cc has merit circle  # noqa: E501
        'ALT',  # aptos launch but cc has alitas
        strethaddress_to_identifier('0x329cf160F30D21006bCD24b67EAde561E54CDE4c'),  # carecoin but cc has carebit  # noqa: E501
        strethaddress_to_identifier('0xf5dF66B06DFf95226F1e8834EEbe4006420D295F'),  # alpaca markets but cc has alpaca finance  # noqa: E501
        strethaddress_to_identifier('0x602Eb0D99A5e3e76D1510372C4d2020e12EaEa8a'),  # Trident in cc but we have T  # noqa: E501
        strethaddress_to_identifier('0x332E824e46FcEeB9E59ba9491B80d3e6d42B0B59'),  # cheesfry but cc has cheese  # noqa: E501
        strethaddress_to_identifier('0xDE12c7959E1a72bbe8a5f7A1dc8f8EeF9Ab011B3'),  # dei but cc has deimos  # noqa: E501
        strethaddress_to_identifier('0x8b921e618dD3Fa5a199b0a8B7901f5530D74EF27'),  # QabbalahBit but cc has project quantum  # noqa: E501
        strethaddress_to_identifier('0xC285B7E09A4584D027E5BC36571785B515898246'),  # coin98 but cc has carbon  # noqa: E501
        strethaddress_to_identifier('0xc56c2b7e71B54d38Aab6d52E94a04Cbfa8F604fA'),  # z.com but cc has zusd  # noqa: E501
        strethaddress_to_identifier('0x9F77BA354889BF6eb5c275d4AC101e9547f15AdB'),  # black box token but cc has bitbook  # noqa: E501
        strethaddress_to_identifier('0x5E5d9aEeC4a6b775a175b883DCA61E4297c14Ecb'),  # florin but cc has flare  # noqa: E501
        strethaddress_to_identifier('0x178E029173417b1F9C8bC16DCeC6f697bC323746'),  # fiat stable pool but cc has fud finance  # noqa: E501
        strethaddress_to_identifier('0x6BC08509B36A98E829dFfAD49Fde5e412645d0a3'),  # woofwoof but cc has shibance token  # noqa: E501
        strethaddress_to_identifier('0x865377367054516e17014CcdED1e7d814EDC9ce4'),  # we have dolla stable coin but cc has a different dolla  # noqa: E501
        strethaddress_to_identifier('0xBEA0000029AD1c77D3d5D23Ba2D8893dB9d1Efab'),  # cc has a different bean than us  # noqa: E501
        # assets that match the one in coingecko and are not the ones locally
        strethaddress_to_identifier('0x68037790A0229e9Ce6EaA8A99ea92964106C4703'),
        strethaddress_to_identifier('0x69e8b9528CABDA89fe846C67675B5D73d463a916'),
        strethaddress_to_identifier('0x2370f9d504c7a6E775bf6E14B3F12846b594cD53'),
        strethaddress_to_identifier('0x0a5E677a6A24b2F1A2Bf4F3bFfC443231d2fDEc8'),
        strethaddress_to_identifier('0xDC59ac4FeFa32293A95889Dc396682858d52e5Db'),
        strethaddress_to_identifier('0x6BeA7CFEF803D1e3d5f7C0103f7ded065644e197'),
        strethaddress_to_identifier('0x4104b135DBC9609Fc1A9490E61369036497660c8'),
        strethaddress_to_identifier('0x9C4A4204B79dd291D6b6571C5BE8BbcD0622F050'),
        strethaddress_to_identifier('0x559eBC30b0E58a45Cc9fF573f77EF1e5eb1b3E18'),
        strethaddress_to_identifier('0x45fDb1b92a649fb6A64Ef1511D3Ba5Bf60044838'),
        strethaddress_to_identifier('0x3236A63c21Fc524a51001ea2627697fDcA86E897'),
        strethaddress_to_identifier('0xd7C9F0e536dC865Ae858b0C0453Fe76D13c3bEAc'),
        strethaddress_to_identifier('0x6967299e9F3d5312740Aa61dEe6E9ea658958e31'),
        'eip155:42161/erc20:0x602Eb0D99A5e3e76D1510372C4d2020e12EaEa8a',
        'KON',
        evm_address_to_identifier(address='0x20658291677a29EFddfd0E303f8b23113d837cC7', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0x2dff88a56767223a5529ea5960da7a3f5f766406', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0xe238ecb42c424e877652ad82d8a939183a04c35f', chain_id=ChainID.POLYGON_POS, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0xA35923162C49cF95e6BF26623385eb431ad920D3', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0x297E4e5e59Ad72B1B0A2fd446929e76117be0E0a', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0x297E4e5e59Ad72B1B0A2fd446929e76117be0E0a', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # GDX but cc has gold miner
        'KING',  # different king
        evm_address_to_identifier(address='0x9bf1D7D63dD7a4ce167CF4866388226EEefa702E', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # BEN memecoin but cc has bitcoen
        evm_address_to_identifier(address='0xF831938CaF837cd505dE196BBb408D81A06376ab', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # JEFF memecoin but cc has jeff on space
        evm_address_to_identifier(address='0x3c8b650257cfb5f272f799f5e2b4e65093a11a05', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # velodrome but cc has a different one
        evm_address_to_identifier(address='0x01BA67AAC7f75f647D94220Cc98FB30FCc5105Bf', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # lyra but cc has scryptia
        'ACS',
        'HDX',
        'NXRA',
        'NOM',
        evm_address_to_identifier(address='0x9559Aaa82d9649C7A7b220E7c461d2E74c9a3593', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # reth2 in cc
        evm_address_to_identifier(address='0xAB846Fb6C81370327e784Ae7CbB6d6a6af6Ff4BF', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # paladin but cc has policypal
        evm_address_to_identifier(address='0x01597E397605Bf280674Bf292623460b4204C375', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # bent token but bent finance in cc
        evm_address_to_identifier(address='0xb3Ad645dB386D7F6D753B2b9C3F4B853DA6890B8', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # contractor but cc has creator platform
        evm_address_to_identifier(address='0x8bb08042c06FA0Fc26cd2474C5F0C03a1056Ad2F', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # consumer price index but cc has crypto price
        'IRON',  # iron fish but cc has iron
        'VARA',  # equilibre but VARA chain in cc
        evm_address_to_identifier(address='0x9bf1D7D63dD7a4ce167CF4866388226EEefa702E', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # eaglegx but cc has EagleCoin
        evm_address_to_identifier(address='0x6589fe1271A0F29346796C6bAf0cdF619e25e58e', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # grain(farm) but cc has Granary
        evm_address_to_identifier(address='0x6589fe1271A0F29346796C6bAf0cdF619e25e58e', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # grain(farm) but cc has Granary
        evm_address_to_identifier(address='0x24086EAb82DBDaa4771d0A5D66B0D810458b0E86', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # we have an older meme coin pepeai
        evm_address_to_identifier(address='0x3007083EAA95497cD6B2b809fB97B6A30bdF53D3', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # address doesn't match
        'ANDY',  # we have andy on sol but cc has andy
        evm_address_to_identifier(address='0x22B6C31c2bEB8f2d0d5373146Eed41Ab9eDe3caf', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have cocktailbar and cc has coin of champions
        evm_address_to_identifier(address='0xb8a87405d9a4F2F866319B77004e88dfF66c0d92', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have soraAI but cc has sora validator
        evm_address_to_identifier(address='0x20547341E58fB558637FA15379C92e11F7b7F710', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501  # we have mozaic and cc has mozik
        evm_address_to_identifier(address='0xe7E4279b80D319EDe2889855135A22021baf0907', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have zeus founding and cc has zeus network
        evm_address_to_identifier(address='0xf53AD2c6851052A81B42133467480961B2321C09', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have pooled eth but cc has jpeg's ETH
        evm_address_to_identifier(address='0x04cC847F81A01328c69EA58321f2E0F8e8ED9681', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # we have a unknown WLD token but cc has worldcoin
        evm_address_to_identifier(address='0xbbd6CD3A31Cbc5CbD6f89D476D15D5bD2F260AcB', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # we have a unknown AERO token
        evm_address_to_identifier(address='0x1efF8aF5D577060BA4ac8A29A13525bb0Ee2A3D5', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have balancer pool token but cc has black pool
        evm_address_to_identifier(address='0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # we have balancer pool token but cc has black pool
        evm_address_to_identifier(address='0x6432096f054288Ee45b7f6ad8863a1F4A8e1201C', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # we have fomo base but cc has aavegochi fomo
        'WZRD',  # bitcoin wizards but cc has wizardia
        evm_address_to_identifier(address='0xb0eCc6ac0073c063DCFC026cCdC9039Cae2998E1', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501  # account abstraction but cc has alva
        evm_address_to_identifier(address='0x12652C6d93FDB6F4f37d48A8687783C782BB0d10', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # entangle cc gold fever
        evm_address_to_identifier(address='0x6043A3f2f4Fe127d81896220369F9E9CF5Fdf66F', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # panda but cc has panda dao
        evm_address_to_identifier(address='0x77be1ba1Cd2D7a63BFfC772D361168cc327dd8bc', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # meow meme coin but cc has ZERO
        evm_address_to_identifier(address='0x13832bEC9b7029a82988017a7f6095BDf0207D62', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # milk but cc has milkshake
        evm_address_to_identifier(address='0xeF0b2Ccb53A683fA48799245f376D6a60929f003', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # unknown moon and cc has reddit moon
        evm_address_to_identifier(address='0xfF07fc776206BDdd9d285A5E571dcDF98131120B', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # chiUSD but cc has CHI GAS TOKEN
        evm_address_to_identifier(address='0x6DcB98f460457fe4952e12779Ba852F82eCC62C1', chain_id=ChainID.ARBITRUM_NOVA, token_type=TokenKind.ERC20),  # noqa: E501  # bricks but cc has MyBricks
        evm_address_to_identifier(address='0x5e06eA564efcB3158a85dBF0B9E017cb003ff56f', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # usd stable but cc has Mountain Protocol
        evm_address_to_identifier(address='0x1d75AA781665A189b240ca3D6D3CbB540EC7f02A', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # base frens but cc has farm friends
        evm_address_to_identifier(address='0x8Fa0FF7350B07c2e1244daD303fbe4ec71bB7E9a', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # scam ETH token
        evm_address_to_identifier(address='0x70da6ec1fCbE89122c66ECAAC8430CB15580b8Ee', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # wif fake token
        evm_address_to_identifier(address='0x302ab9ae394D675676Ddb41E294169224824fc9A', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # cheezburger but cc has chiliz
        evm_address_to_identifier(address='0x3108ccFd96816F9E663baA0E8c5951D229E8C6da', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # cc has a dark without any address info
        'SBF',  # we have sam token but cc has sam in jail
        evm_address_to_identifier(address='0x79F05c263055BA20EE0e814ACD117C20CAA10e0c', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # different ICE
        evm_address_to_identifier(address='0xc335Df7C25b72eEC661d5Aa32a7c2B7b2a1D1874', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # different ice
        evm_address_to_identifier(address='0xa8a8d0373642977CD491e29572484012174ADfBd', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Jesus on base but cc doesn't have any
        evm_address_to_identifier(address='0x12E8E49A585123F85b08Fe4114443f9E7dbe0746', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # fake jesus on base
        evm_address_to_identifier(address='0x348Fdfe2c35934A96C1353185F09D0F9efBAdA86', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # trove on base but trove isn't listed on base
        evm_address_to_identifier(address='0x994f0DffdbaE0BbF09b652D6f11A493fd33F42B9', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501 # this is eagle coin but cc is eagle token
        'POCHITA',  # this is a different pochita as seen by the token logo
        'WORM',  # this is deep worm but cc is healthy worm
        'TRAC',  # this is trac(ordinals) but cc is origin trail
        'MVRS',  # this is magaverse but cc is meta mvrs
        'KACY',  # this is markkacy but cc is Kassandra
        evm_address_to_identifier(address='0x8d80de8A78198396329dfA769aD54d24bF90E7aa', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Nami.Trade but CC has Nirvana Chain
        evm_address_to_identifier(address='0x832904863978b94802123106e6eB491BDF0Df928', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # OptiToken but CC has Optimus AI
        evm_address_to_identifier(address='0x126c121f99e1E211dF2e5f8De2d96Fa36647c855', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # DEGEN Index but CC has Degen
        evm_address_to_identifier(address='0xAE6e3540E97b0b9EA8797B157B510e133afb6282', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501  # DEGEN Index but CC has Degen
        evm_address_to_identifier(address='0x908EF6B57a6BB5B043Ea6EF84142895b519c713c', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Matchcup but CC has Matching Game
        evm_address_to_identifier(address='0xD0ACCF05878caFe24ff8b3F82F194C62Ed755707', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # SIMP Token but CC has SO-COL
        evm_address_to_identifier(address='0xb8919522331C59f5C16bDfAA6A121a6E03A91F62', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Home but CC has OtterHome
        evm_address_to_identifier(address='0xea3Fb6f331735252E7Bfb0b24b3B761301293DBe', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Vader USD but CC has Verified USD
        evm_address_to_identifier(address='0x44dB359bf01F8b521A6295E4d56991277f410AA2', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0x7616113782AaDAB041d7B10d474F8A0c04EFf258', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Vee Token but CC has BLOCKv
        evm_address_to_identifier(address='0x326f5834d73a2dc02b3c492E9ef1b24399d430b3', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # StargateToken but CC has Stargate Finance
        evm_address_to_identifier(address='0xAD038Eb671c44b853887A7E32528FaB35dC5D710', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Dola Borrowing Right but CC has deBridge
        evm_address_to_identifier(address='0xD04E772BC0d591fBD288f2E2a86aFA3D3CB647F8', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # CryptoGPT Token but CC has QnA3.AI
        evm_address_to_identifier(address='0xE0151763455A8a021e64880C238ba1cff3787fF0', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Aped but CC has Baddest Alpha Ape Bundle
        evm_address_to_identifier(address='0xDFE29AFdF5A7D0bb92A01A56Adabfa87D652E0E7', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Optimus but CC has Opus
        evm_address_to_identifier(address='0x9CBf044bc535db4C93a9F11205A69631d9DCeF26', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Billy Token but CC has Billy
        evm_address_to_identifier(address='0x5888641e3e6cBeA6D84Ba81EDb217bD691d3bE38', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Bobo but CC has BOBO
        evm_address_to_identifier(address='0x9452D45d33490234B8C96f42342F1Be28c0FE097', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Swaperry but CC has Perry The BNB
        evm_address_to_identifier(address='0xB6b8CCD230Bb4235C7b87986274E7aB550b72261', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # HALO Token but CC has Halo Coin
        evm_address_to_identifier(address='0xAAA6C1E32C55A7Bfa8066A6FAE9b42650F262418', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501  # Ramses but CC has Ramifi Protocol
        evm_address_to_identifier(address='0xAcf79C09Fff518EcBe2A96A2c4dA65B68fEDF6D3', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Karate but CC has Karate Combat
        evm_address_to_identifier(address='0x0678Ca162E737C44cab2Ea31b4bbA78482E1313d', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Turbos Finance but CC has Turbos Finance
        evm_address_to_identifier(address='0xF1182229B71E79E504b1d2bF076C15a277311e05', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # LBR but CC has Lybra Finance
        evm_address_to_identifier(address='0x9A601C5bb360811d96A23689066af316a30c3027', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Pika but CC has Pikaboss
        evm_address_to_identifier(address='0xC9D21E5A24110b67af31aF464edfDC2dAe5Ec7D5', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # BitMeme but CC has Bytom
        evm_address_to_identifier(address='0x244b797d622D4DEe8b188b03546ACAAbD0Cf91A0', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Four but CC has 4THPILLAR TECHNOLOGIES
        evm_address_to_identifier(address='0x9Ee75952E3408ed7005225855aA1835D6d0023CA', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Stamen Tellus Token but CC has Statter Network
        evm_address_to_identifier(address='0xdFA46478F9e5EA86d57387849598dbFB2e964b02', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Mai Stablecoin but CC has Mindsync
        evm_address_to_identifier(address='0xb504035a11E672e12a099F32B1672b9C4a78b22f', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Safereum but CC has Safereum
        evm_address_to_identifier(address='0x27DCB425C7005DD7558F9583797edA39A8D70ABd', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Wrapped Ether but CC has WETH
        evm_address_to_identifier(address='0x95987b0cdC7F65d989A30B3B7132a38388c548Eb', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # PURSE TOKEN but CC has Pundi X PURSE
        evm_address_to_identifier(address='0xC256F81d35a54c3599B424171d719E9Ae87b2E9b', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # ZOOA but CC has Zoopia
        evm_address_to_identifier(address='0x56cCEA18F8c7c23328Cdfd545c50c7c370f8d263', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # RSCOIN but CC has ResearchCoin
        evm_address_to_identifier(address='0x3ADb04E127b9C0a5D36094125669d4603AC52a0c', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Gro Vault Token but CC has Genesis Vision
        evm_address_to_identifier(address='0x21ad647b8F4Fe333212e735bfC1F36B4941E6Ad2', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Squid but CC has Squid Game
        evm_address_to_identifier(address='0x35A9b440Da4410dD63dF8c54672b728970560328', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Mana but CC has Decentraland
        evm_address_to_identifier(address='0x33d63Ba1E57E54779F7dDAeaA7109349344cf5F1', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # DATA Economy Index but CC has Streamr
        evm_address_to_identifier(address='0x47110d43175f7f2C2425E7d15792acC5817EB44f', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Bankless DeFi Innovation Index but CC has GamiFi
        evm_address_to_identifier(address='0xcf32c644fed4FeFF94017a10B2882Bf71eE740dD', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Brawl Token but CC has BitBrawl
        evm_address_to_identifier(address='0x3001f57F8308b189EB412a64322Aad5eF9951290', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # GEC but CC has Geco.one
        evm_address_to_identifier(address='0x7e4C1D51ace44E26c5924d590995dEA3eB8aD505', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Gameta but CC has HIPPOP
        evm_address_to_identifier(address='0xaA247c0D81B83812e1ABf8bAB078E4540D87e3fB', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # meson.network but CC has Manson Coin
        evm_address_to_identifier(address='0x102c776DDB30C754dEd4fDcC77A19230A60D4e4f', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Flooring Lab Credit but CC has FlowChainCoin
        evm_address_to_identifier(address='0x3417E54A51924C225330f8770514aD5560B9098D', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # REDKoin but CC has RED TOKEN
        evm_address_to_identifier(address='0xCa0E54b636DB823847B29F506BFFEE743F57729D', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Chi USD but CC has Chi Gastoken
        evm_address_to_identifier(address='0x39FdE572a18448F8139b7788099F0a0740f51205', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Oath Token but CC has OATH Protocol
        evm_address_to_identifier(address='0xbfD291DA8A403DAAF7e5E9DC1ec0aCEaCd4848B9', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # dForce USD but CC has USX Quantum
        evm_address_to_identifier(address='0xB0ae108669CEB86E9E98e8fE9e40d98b867855fD', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # OneRing but CC has Darwinia Network
        evm_address_to_identifier(address='0x12ff4a259e14D4DCd239C447D23C9b00F7781d8F', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # PEPE Optimism but CC has Pepe
        evm_address_to_identifier(address='0x3F56e0c36d275367b8C502090EDF38289b3dEa0d', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # QiDao but CC has BENQI
        evm_address_to_identifier(address='0x3Ebb31CB2888e0Acbb81cBE2FeC65AEE24be3BD4', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # AVT but CC has Aventus
        evm_address_to_identifier(address='0xB25EA095997F5bBaa6cEa962c4fBf3bfc3C09776', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Promethios but CC has Matr1x Fire
        evm_address_to_identifier(address='0x47536F17F4fF30e64A96a7555826b8f9e66ec468', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # MUMMY but CC has Mummy Finance
        evm_address_to_identifier(address='0x8901cB2e82CC95c01e42206F8d1F417FE53e7Af0', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # YieldFarming Index but CC has Your Futures Exchange
        evm_address_to_identifier(address='0xC1c167CC44f7923cd0062c4370Df962f9DDB16f5', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Pepe but CC has Pepe
        evm_address_to_identifier(address='0x57ebDb4c8E41eBAc32986DF4A4D591296E5fB0F1', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # SSS but CC has StarSharks
        evm_address_to_identifier(address='0xb532178708814F0c174B29B991D2b355106Afbc3', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Astrava but CC has AirSwap
        evm_address_to_identifier(address='0xAb1047894dA4ec207c71bE0AEF5c7885e07B2DaF', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # LSD DAO but CC has Pontem Liquidswap
        evm_address_to_identifier(address='0x2e80259C9071B6176205FF5F5Eb6F7EC8361b93f', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # HashDAO Token but CC has Provenance Blockchain
        evm_address_to_identifier(address='0xef9aE714dCd61A9DE189c63c40B0082F2ead576D', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0x158b4eD5b3bd2383ceC2A045C7c8F3594B72Cad2', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0xFe1F3C6D42376e74d3E9C0724ed132c1e0Dcdd8a', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0xbf0c7ccB143126C1bE90a426f676f5cb313956d9', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Tempest but CC has Temtum
        evm_address_to_identifier(address='0xFd5494CDf4f1a5b5abA8cE5D7ee1d04eF47f2FCA', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0x9e57B3d7fD1a8F8FcE8C4214cC1148D518D6f6fE', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0xf4d620009d9381094CD70eBEE2B0730E095A3b12', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Test but CC has Test
        evm_address_to_identifier(address='0xcb7348d51E49402591A6a382F3a76e33FD4b341e', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Pepe but CC has Pepe
        evm_address_to_identifier(address='0xDe8E894148C47cC0BaEfd0Bc56BA0DBc1a61201A', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Bc Game but CC has BlockChainGames
        evm_address_to_identifier(address='0xA1f085846381335aD10C86E1001dFB833C218897', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # CHERY FINANCE but CC has Crafting Finance
        evm_address_to_identifier(address='0x00e1724885473B63bCE08a9f0a52F35b0979e35A', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # Oath Token but CC has OATH Protocol
        evm_address_to_identifier(address='0x2c94dab6B2C970d9e3049491AAC48e8E0F3b3068', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # ECO but CC has Ormeus Ecosystem
        evm_address_to_identifier(address='0x619f56Ad816f7182678E6443c8A7b2d276305C86', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501  # POP but CC has Popcoin
        evm_address_to_identifier(address='0x00e1724885473B63bCE08a9f0a52F35b0979e35A', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Oath Token but CC has OATH Protocol
        evm_address_to_identifier(address='0xbf1aeA8670D2528E08334083616dD9C5F3B087aE', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Mai Stablecoin but CC has Mindsync
        evm_address_to_identifier(address='0x9E53e88dCff56d3062510A745952DEC4cEFDff9E', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Basic Dog Meme but CC has DOG•GO•TO•THE•MOON
        evm_address_to_identifier(address='0x8901cB2e82CC95c01e42206F8d1F417FE53e7Af0', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # YieldFarming Index but CC has Your Futures Exchange
        evm_address_to_identifier(address='0x5c185329BC7720AebD804357043121D26036D1B3', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # BAI but CC has BearAI
        evm_address_to_identifier(address='0x5D1A42E32d84560fF46f4F06302fE4C69d28135d', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # AAA but CC has Moon Rabbit
        evm_address_to_identifier(address='0x8544FE9D190fD7EC52860abBf45088E81Ee24a8c', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Toshi but CC has Toshi
        evm_address_to_identifier(address='0xd7c9621e3A5051f5e5A5982c8c430Fd4B55Eda22', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Blue but CC has Bluefin
        evm_address_to_identifier(address='0x595675dcbe5D2aD1f4d7b910c50567c0f9230633', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # ShipeDEX but CC has ShipChain
        evm_address_to_identifier(address='0xc142171B138DB17a1B7Cb999C44526094a4dae05', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # dForce USD but CC has USX Quantum
        evm_address_to_identifier(address='0xb53Be0BE88bA245B5086E558D00Ad56ee7344556', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # TOSHI but CC has Toshi
        evm_address_to_identifier(address='0x60b72C00681A43e423F097ab61CC526a1045B048', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # friend.tech but CC has Friend.tech
        evm_address_to_identifier(address='0x03617dC1ab7f959cc3593bB43ca43e192e6662da', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Colibri but CC has Drone Coin
        evm_address_to_identifier(address='0x2168eb98C6D416Afb85E7beef5abDc4FB4177dfE', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Blp but CC has BullPerks
        evm_address_to_identifier(address='0xbeFD5C25A59ef2C1316c5A4944931171F30Cd3E4', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # GoldenBoys but CC has CyberDragon Gold
        evm_address_to_identifier(address='0xC19669A405067927865B40Ea045a2baabbbe57f5', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # STAR but CC has FileStar
        evm_address_to_identifier(address='0x2B6A85CD35D15691357eea61d88cB3f401A92FC3', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # SurvToken but CC has Survival Game Online
        evm_address_to_identifier(address='0x5D67a4AFb9fBFc3640e163e93766Cf1eAF2F7045', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Gold but CC has Goldario
        evm_address_to_identifier(address='0x9Cc2fC2f75768b0307925C7935396Ec9D94bbA44', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Meta but CC has Meta
        evm_address_to_identifier(address='0x60be663a88401c917372b945b7D04cd75e5ABd12', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # LA but CC has LATOKEN
        evm_address_to_identifier(address='0xEf6b19D71B342EAE33773346b05EAD8F0966BD42', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # TEST but CC has Test
        evm_address_to_identifier(address='0x7Ee9cf972BC8441ebc112c5F01a96Ce85b0a44Bd', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Dai but CC has Dai
        evm_address_to_identifier(address='0x2259ba575F7C66cF10d59a1Fe2F7BA77C5685770', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # BAI but CC has BearAI
        evm_address_to_identifier(address='0xBe449c2aB88B5D9BF33eDe32270957d240155597', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Mushroom but CC has Meta Ruffy
        evm_address_to_identifier(address='0xCa080DD32EEaa87711Db63543C9712b08795926a', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # test but CC has Test
        evm_address_to_identifier(address='0xE2B21D4684b2bA62F3BE1FE286eacb90D26E394d', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # CryptoOracle Collective but CC has Coin of the champions
        evm_address_to_identifier(address='0xf908326E871561E31b346499F70854350aCe3Dd2', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Base AI but CC has BearAI
        evm_address_to_identifier(address='0x0e80F46D9Eb7611748e07aC234be4eBa260e4531', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Test Token but CC has ThunderCore
        evm_address_to_identifier(address='0x981D41C115a2d48Cb1215D13Bda8f989d407c9c5', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Xena but CC has XEN Crypto
        evm_address_to_identifier(address='0x07388Ecb5584622c80fbd21355bFB778f77361D8', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # TestToken but CC has Titan Coin
        evm_address_to_identifier(address='0xba7D47f471ADD16875e765edEe0858C3413A56Fd', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Meta but CC has Meta (mStable Governance: Meta)
        evm_address_to_identifier(address='0x063D2DB6D348Fa5957b78B6141d144426486c68C', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # SocioCat but CC has Simon's Cat
        evm_address_to_identifier(address='0x3CCEc427b833496FE7FDB62b577C109551E12f55', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # THE KEY 33 but CC has SelfKey
        evm_address_to_identifier(address='0x0a5aBd23cC5e3F4061270482b571e93226F7Df7A', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # THE KEY 33 but CC has SelfKey
        evm_address_to_identifier(address='0x7EC4Ef6F0F5D46f0A462cee307Ea8CB8efcca4DC', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # MEME MASTER but CC has Mastercoin
        evm_address_to_identifier(address='0x7BC401227777F173Ff871993b198A8632741B9Bb', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Detto Token but CC has Delta Exchange
        evm_address_to_identifier(address='0x677a3AfA51bA1a95f70F5B971DcA72047690faA2', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # TEST NAME but CC has Test
        evm_address_to_identifier(address='0x58Ed4FD0C3d930b674BA50a293f03ef6cD7dE7a3', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # ArbiDex Token but CC has ARCS
        evm_address_to_identifier(address='0x8fCC55494C7939d563620C8f697D462A0D8C230F', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Cool Base Cool but CC has Casino Betting Coin
        evm_address_to_identifier(address='0xC435B542aCB241185c72D3653447E070994Da59f', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Free Coin but CC has FREE coin
        evm_address_to_identifier(address='0xa11810F2df32263A65Ef7f5f5754F88CCd8De8df', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # ALI but CC has Alethea Artificial Liquid Intelligence Token
        evm_address_to_identifier(address='0xFAaA87943bFca6D97434bE3d26C589647FEA4375', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # ACEToken but CC has Fusionist
        evm_address_to_identifier(address='0x1337420dED5ADb9980CFc35f8f2B054ea86f8aB1', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Subsquid but CC has SQD
        evm_address_to_identifier(address='0x1cCF27211e8bf052f6255329ed641B4E94E80603', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # meta baby but CC has BabySwap
        evm_address_to_identifier(address='0xcb1592591996765Ec0eFc1f92599A19767ee5ffA', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # BIO but CC has Bio Protocol
        evm_address_to_identifier(address='0xEab49138BA2Ea6dd776220fE26b7b8E446638956', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Send but CC has Suilend
        evm_address_to_identifier(address='0x7e3784220740e61dC700501bd6771226E11d8897', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Cyber Arena Token but CC has Simon's Cat
        evm_address_to_identifier(address='0x1121AcC14c63f3C872BFcA497d10926A6098AAc5', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Department Of Government Efficiency but CC has Dogecoin
        evm_address_to_identifier(address='0x67f0870BB897F5E1c369976b4A2962d527B9562c', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Department Of Government Efficiency but CC has Dogecoin
        evm_address_to_identifier(address='0xf9Fa60EF4F23F00CCE403cc4d2c11Baf4880A0d6', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # FARCANA but CC has Farmland Protocol
        evm_address_to_identifier(address='0x5F32AbeeBD3c2fac1E7459A27e1AE9f1C16ccccA', chain_id=ChainID.POLYGON_POS, token_type=TokenKind.ERC20),  # noqa: E501  # FARCANA but CC has Farmland Protocol
        evm_address_to_identifier(address='0x6bfDB6f4E65Ead27118592A41eB927cEa6956198', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Fame AI but CC has Fimarkcoin
        evm_address_to_identifier(address='0x6bfDB6f4E65Ead27118592A41eB927cEa6956198', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Fame AI but CC has Fimarkcoin
        evm_address_to_identifier(address='0x1C4CcA7C5DB003824208aDDA61Bd749e55F463a3', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # GAME by Virtuals but CC has GameBuild
        evm_address_to_identifier(address='0x0C1dC73159e30c4b06170F2593D3118968a0DCa5', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # GoPlus Security but CC has Triffic
        evm_address_to_identifier(address='0x7eDC0eC89F987ECd85617b891c44fE462a325869', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Gunstar Metaverse but CC has CoinGhost
        evm_address_to_identifier(address='0xD5D053D5B769383e860d1520Da7a908E00919F36', chain_id=ChainID.AVALANCHE, token_type=TokenKind.ERC20),  # noqa: E501  # JUICE but CC has Juice Finance
        evm_address_to_identifier(address='0xc732B6586A93b6B7CF5FeD3470808Bc74998224D', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # KmonCoin but CC has Kryptomon
        evm_address_to_identifier(address='0xc4170fd71ECed3C80baDca77f4e12E8AaC1e3436', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # KmonCoin but CC has Kryptomon
        evm_address_to_identifier(address='0x55cD6469F597452B5A7536e2CD98fDE4c1247ee4', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Luna by Virtuals but CC has Terra
        evm_address_to_identifier(address='0x0000000000c5dc95539589fbD24BE07c6C14eCa4', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Milady Cult Coin but CC has Cult DAO
        evm_address_to_identifier(address='0x0944D5848BD9F60A34Ba92aEa300d4286696Eb76', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Palette Token but CC has Poollotto.finance
        evm_address_to_identifier(address='0xB299751B088336E165dA313c33e3195B8c6663A6', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # StarHeroes but CC has FileStar
        evm_address_to_identifier(address='0xB299751B088336E165dA313c33e3195B8c6663A6', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501  # StarHeroes but CC has FileStar
        evm_address_to_identifier(address='0x35bEdBF9291b22218a0dA863170dcC9329Ef2563', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # TAP Coin but CC has TAP FANTASY
        evm_address_to_identifier(address='0xfd418e42783382E86Ae91e445406600Ba144D162', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Zircuit but CC has ZrCoin
        evm_address_to_identifier(address='0x5c8D0C48810FD37A0A824D074ee290E64f7A8Fa2', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # AVL but CC has Aston Villa Fan Token
        evm_address_to_identifier(address='0x9BeEE89723cEeC27d7c2834bec6834208FFdc202', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # AVL but CC has Aston Villa Fan Token
        evm_address_to_identifier(address='0x0Db510e79909666d6dEc7f5e49370838c16D950f', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Super Anon but CC has ANON
        evm_address_to_identifier(address='0x28561B8A2360F463011c16b6Cc0B0cbEF8dbBcad', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # MOO DENG but CC has Moo Deng (moodengsol.com)
        evm_address_to_identifier(address='0x3C6256F234Ba638E5883c46b3fEdb00ea2e66b8A', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Moongate but CC has Megatech
        evm_address_to_identifier(address='0x3Ab1A5f76E12202d1AD1548A08a799501581Da4E', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # DIN but CC has Dinero
        evm_address_to_identifier(address='0xe343167631d89B6Ffc58B88d6b7fB0228795491D', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Global Dollar but CC has USDG
        evm_address_to_identifier(address='0xcacf1ca03983CE6c7E235fb20C70aCC70ed13509', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # AstroPepeX but CC has ApolloX
        evm_address_to_identifier(address='0xed4e879087ebD0e8A77d66870012B5e0dffd0Fa4', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # AstroPepeX but CC has ApolloX
        evm_address_to_identifier(address='0xdBcD57cc74b180f928258F7B1a32F6f7e64BF12e', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Baby Pepe Token but CC has Blast Pepe
        evm_address_to_identifier(address='0xFc4b4ec763722B71eB1D729749B447A9645f5F30', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # DumbMoney but CC has GameStop
        evm_address_to_identifier(address='0xb02eF03245fc7DF987BBd876768E6d441b7099B6', chain_id=ChainID.POLYGON_POS, token_type=TokenKind.ERC20),  # noqa: E501  # Satoshi Airline but CC has Jet Protocol
        evm_address_to_identifier(address='0x7f72EBb448387537C174a5D17E762C877db28fB6', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Fishkoin but CC has Koinos
        evm_address_to_identifier(address='0x4f7eA8F6487a7007ca054F35c4a7b961f5b18961', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # GoldenCat but CC has CatCoin Token
        evm_address_to_identifier(address='0x8808434a831eFea81170A56a9ddc57Cc9E6De1d8', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501  # Bork on Ethereum but CC has Bork
        evm_address_to_identifier(address='0xBA5E66FB16944Da22A62Ea4FD70ad02008744460', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Based Turbo but CC has Turbo
        evm_address_to_identifier(address='0x49d803d2DF2295185610f44961F2Dcd40326F25C', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # noqa: E501  # Shark Cat but CC has Siacoin
        evm_address_to_identifier(address='0x23D3F4EaaA515403C6765bb623F287a8Cca28F2b', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501  # Broccoli but CC has CZ'S Dog (broccoli.gg)
        'COOHA',  # CoolMining but CC has CoolHash
        'MOR',  # Moreal but CC has Morpheus
        'OXBT',  # OXBT but CC has OXBT (Ordinals)
        'MTC',  # MTC but CC has Matrix Chain
        'MYRA',  # Myra but CC has Mytheria
        'STAMP',  # STAMP but CC has SafePost
        'SPOODY',  # Spodermen but CC has Spoody Man
        'EGG',  # Eggdog but CC has Goose Finance
        'MXM',  # MixMob but CC has Maximine
        'INTX',  # IntentX but CC has Intexcoin
        'BUZZ',  # Hive AI but CC has BuzzCoin
        'ALCH',  # Alchemist AI but CC has Alchemy
        'AVAAI',  # Ava AI but CC has Travala
        'BTF',  # Bitfinity Network but CC has Blockchain Traded Fund
        'CATS',  # CATS but CC has CatCoin Token
        'CTT',  # Cashtree Token but CC has Castweet
        'PGC',  # PiggyPiggyCoin but CC has Pegascoin
        'SLC',  # Silencio but CC has Solice
        'STREAM',  # Streamflow but CC has STREAMIT COIN
        'STOP',  # LETSTOP but CC has SatoPay
        'PI',  # Pi Network but CC has Plian
        'ROCK',  # ROCK DAO but CC has Bedrock
        'SEND',  # Sendcoin but CC has Suilend
        'SNOW',  # Snowman but CC has Snowswap
        'TCAT',  # Tron Cat but CC has The Currency Analytics
        'METAV',  # METAVERSE but CC has MetaVPad
        'EVAN',  # Evan but CC has Evanesco Network
        'HABIBI',  # Habibi (Sol) but CC has The Habibiz
        'HAT',  # Top Hat but CC has Hawala.Exchange
        strethaddress_to_identifier('0x5888641e3e6cBeA6D84Ba81EDb217bD691d3bE38'),  # Bobo but BOBO in CC  # noqa: E501
        strethaddress_to_identifier('0x8808434a831eFea81170A56a9ddc57Cc9E6De1d8'),  # Bork on Ethereum but Bork in CC  # noqa: E501
        strethaddress_to_identifier('0xdBcD57cc74b180f928258F7B1a32F6f7e64BF12e'),  # Baby Pepe Token but Blast Pepe in CC  # noqa: E501
        strethaddress_to_identifier('0x9CBf044bc535db4C93a9F11205A69631d9DCeF26'),  # Billy Token but Billy in CC  # noqa: E501
        strethaddress_to_identifier('0x8fc17671D853341D9e8B001F5Fc3C892d09CB53A'),  # BlockGames but Blockasset in CC  # noqa: E501
        evm_address_to_identifier(address='0x37DEfBC399e5737D53Dfb5533d9954572F5B19bf', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # BLAZE but StoryFire in CC  # noqa: E501
        evm_address_to_identifier(address='0x3A4F0DB58D36A3362673a8ea7e2087fb2Ae68616', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # Black Rock but Bedrock in CC  # noqa: E501
        evm_address_to_identifier(address='0x56cCEA18F8c7c23328Cdfd545c50c7c370f8d263', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # Lorenzo Governance Token but Float Protocol in CC  # noqa: E501
        evm_address_to_identifier(address='0xBA5E66FB16944Da22A62Ea4FD70ad02008744460', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # Based Turbo but Turbo in CC  # noqa: E501
        strethaddress_to_identifier('0xBB49A51Ee5a66ca3a8CbE529379bA44Ba67E6771'),  # Cryptosolartech but Crypto Samurai in CC  # noqa: E501
        strethaddress_to_identifier('0x3108ccFd96816F9E663baA0E8c5951D229E8C6da'),  # DarkToken but Dark Eclipse in CC  # noqa: E501
        evm_address_to_identifier(address='0xd327d36EB6E1f250D191cD62497d08b4aaa843Ce', chain_id=ChainID.BASE, token_type=TokenKind.ERC20),  # Father Of Meme: Origin but Fomo in CC  # noqa: E501
        evm_address_to_identifier(address='0x324f76014C8a7C3b3C0c574bC331F950C5F8c6Fd', chain_id=ChainID.ZKSYNC_ERA, token_type=TokenKind.ERC20),  # Holdstation but Holdcoin in CC  # noqa: E501
        strethaddress_to_identifier('0xD8E8438CF7bEEd13cFABC82F300Fb6573962c9e3'),  # Pepoclown but Honk in CC  # noqa: E501
        strethaddress_to_identifier('0x8E4d27d772099e18900CAF5Dcc36Cb612DcEE886'),  # Architex but ARC Governance in CC  # noqa: E501
        evm_address_to_identifier(address='0x27DCB425C7005DD7558F9583797edA39A8D70ABd', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # MyMetaTrader Token but MeMusic in CC  # noqa: E501
        strethaddress_to_identifier('0xA75AD62a1b6b78eEA6c54C22Eb697Ca0b125f97a'),  # meow but Zero Tech in CC  # noqa: E501
        strethaddress_to_identifier('0x8B95Fe1C06E58C269f1267e0f0093b7b26b85481'),  # MOJO The Gorilla but Planet Mojo in CC  # noqa: E501
        strethaddress_to_identifier('0x6E835aC221d5622bf65aE21a22eB7484d1898598'),  # Pepe2.0 but Pepe 2.0 in CC  # noqa: E501
        strethaddress_to_identifier('0x9fBFed658919A896B5Dc7b00456Ce22D780f9B65'),  # PlutusDeFi but Poollotto.finance in CC  # noqa: E501
        strethaddress_to_identifier('0xfcaF0e4498E78d65526a507360F755178b804Ba8'),  # NicCageWaluigiElmo42069Inu but Shiba Inu in CC  # noqa: E501
        strethaddress_to_identifier('0x0AFf507aC29B8CEA2FB10d2ad14408c2d79A35AD'),  # CrypTalk but Talken in CC  # noqa: E501
        strethaddress_to_identifier('0x86B69F38BEA3e02f68fF88534bc61EC60E772b19'),  # NEVER SURRENDER but OFFICIAL TRUMP in CC  # noqa: E501
        strethaddress_to_identifier('0x31d4Eb09a216e181eC8a43ce79226A487D6F0BA9'),  # USDM but Mountain Protocol in CC  # noqa: E501
        'solana/token:99ouK5YUK3JPGCPX9joNtHsMU7NPpU7w91JN4kdQ97po',  # AI Community but Sleepless in CC  # noqa: E501
        'solana/token:9jaZhJM6nMHTo4hY9DGabQ1HNuUWhJtm7js1fmKMVpkN',  # AMC but AI Meta Coin in CC  # noqa: E501
        'solana/token:DKu9kykSfbN5LBfFXtNNDPaX35o4Fv6vJ9FKk7pZpump',  # Ava AI but Travala in CC  # noqa: E501
        'solana/token:FuQASH8ps9NPeDu4h3rVtMBygKYoSiSTZ4uSiA5tpump',  # Banana for Scale but Banana Gun in CC  # noqa: E501
        'solana/token:FaUKsgcuqAd9sCaFz3if7ia1DasaxVoNPTXWFs2GScWN',  # DONALDCAT but Dogechain in CC  # noqa: E501
        'solana/token:EXA537HSBVpsFijENbt6Muuy9AADUN8dUmYKD4oKbjJE',  # Eggdog but Goose Finance in CC  # noqa: E501
        'solana/token:wo1zgt8rfrYpvdVi4nidoj1SYfcR4pQx69bmNv2JLhQ',  # JustAnEgg but Goose Finance in CC  # noqa: E501
        'solana/token:3BgwJ8b7b9hHX4sgfZ2KJhv9496CoVfsMK2YePevsBRw',  # THE EPIK DUCK but EPIK Token in CC  # noqa: E501
        'solana/token:6MAWnfagDCzqmHQh88FVt9F1zzLqXpwGJpaL7zUTpump',  # EYE Am Watching You but MEDIA EYE in CC  # noqa: E501
        'solana/token:WARcU61sECeEK5DEbkY3wcjGxSGr4W8bVUpKbBNbgbu',  # This Is Fine but Refinable in CC  # noqa: E501
        'solana/token:BgpZ9cXE2dRMTUPhroffbMQm3q8QTLpRorpHYeJspump',  # This Is Fine but Refinable in CC  # noqa: E501
        'solana/token:AFbX8oGjGpmVFywbVouvhQSRmiW2aR1mohfahi4Y2AdB',  # Green Satoshi Token but CoinGhost in CC  # noqa: E501
        'solana/token:864YJRb3JAVARC4FNuDtPKFxdEsYRbB39Nwxkzudxy46',  # Habibi (Sol) but The Habibiz in CC  # noqa: E501
        'solana/token:CymqTrLSVZ97v87Z4W3dkF4ipZE1kYyeasmN2VckUL4J',  # i dont know but IDK in CC  # noqa: E501
        'solana/token:H53UGEyBrB9easo9ego8yYk7o4Zq1G5cCtkxD3E3hZav',  # MixMob but Maximine in CC  # noqa: E501
        'solana/token:H1aN3vcvB68eaFPbMkoAss3vnfi4AhP5C2dpnrZzdBc7',  # Myra but Mytheria in CC  # noqa: E501
        'solana/token:7yZFFUhq9ac7DY4WobLL539pJEUbMnQ5AGQQuuEMpump',  # OBOT but Obortech in CC  # noqa: E501
        'solana/token:SENDdRQtYMWaQrBroBrJ2Q53fgVuq95CV9UPGEvpCxa',  # Sendcoin but Suilend in CC  # noqa: E501
        'solana/token:8XVXzmsMMw7ufa8RC21fHcDP6TGti5y3ZidQinnYurqr',  # Laughing shoe but ShoeFy in CC  # noqa: E501
        'solana/token:8Nd3TZJfxt9yYKiPmYp6S5DhLftG3bwSqdW3KJwArb',  # Spodermen but Spoody Man in CC  # noqa: E501
    )
    for asset_data in GlobalDBHandler.get_all_asset_data(mapping=False):
        potential_support = (
            asset_data.cryptocompare == '' and
            asset_data.symbol in cc_assets and
            cc_assets[asset_data.symbol]['IsTrading'] and
            asset_data.identifier not in exceptions and
            asset_data.protocol != SPAM_PROTOCOL
        )
        if potential_support:
            msg = (
                f'We have {asset_data.identifier} with symbol {asset_data.symbol} and name '
                f'{asset_data.name} as not supported '
                f'by cryptocompare but the symbol appears in its supported assets'
            )
            test_warnings.warn(UserWarning(msg))


def test_assets_tokens_addresses_are_checksummed():
    """Test that all ethereum saved token asset addresses are checksummed"""
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        if asset_data.asset_type != AssetType.EVM_TOKEN:
            continue

        msg = (
            f"Ethereum token's {asset_data.name} ethereum address "
            f'is not checksummed {asset_data.address}'
        )
        assert is_checksum_address(asset_data.address), msg


def test_asset_identifiers_are_unique_all_lowercased():
    """Test that adding an identifier that exists but with different case, would fail"""
    with pytest.raises(InputError):
        GlobalDBHandler.add_asset(CryptoAsset.initialize(
            identifier='Eth',
            asset_type=AssetType.OWN_CHAIN,
            name='a',
            symbol='b',
        ))


def test_case_does_not_matter_for_asset_constructor():
    """Test that whatever case we give to asset constructor result is the same"""
    a1 = CryptoAsset('bTc')
    a2 = CryptoAsset('BTC')
    assert a1 == a2
    assert a1.identifier == 'BTC'
    assert a2.identifier == 'BTC'

    def symbol_to_evm_token(symbol: str) -> EvmToken:
        """Tries to turn the given symbol to an evm token

        May raise:
        - UnknownAsset if an evm token can't be found by the symbol or if
        more than one tokens match this symbol
        """
        maybe_asset = get_crypto_asset_by_symbol(
            symbol=symbol,
            asset_type=AssetType.EVM_TOKEN,
            chain_id=ChainID.ETHEREUM,
        )
        if maybe_asset is None:
            raise UnknownAsset(symbol)

        return maybe_asset.resolve_to_evm_token()

    a3 = symbol_to_evm_token('DAI')
    a4 = symbol_to_evm_token('dAi')
    assert a3.identifier == a4.identifier == strethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F')  # noqa: E501


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- it executes locally every time we check the assets so can be skipped',
)
@pytest.mark.asset_test
def test_coingecko_identifiers_are_reachable(socket_enabled):  # pylint: disable=unused-argument
    """
    Test that all assets have a coingecko entry and that all the identifiers exist in coingecko
    """
    coingecko = Coingecko(database=None)
    all_coins = coingecko.all_coins()
    # If coingecko identifier is missing test is trying to suggest possible assets.
    symbol_checked_exceptions = (  # This is the list of already checked assets
        # only 300 in coingecko is spartan coin: https://www.coingecko.com/en/coins/spartan
        strethaddress_to_identifier('0xaEc98A708810414878c3BCDF46Aad31dEd4a4557'),
        # no arcade city in coingeko. Got other ARC symbol tokens
        strethaddress_to_identifier('0xAc709FcB44a43c35F0DA4e3163b117A17F3770f5'),
        # no avalon in coingecko. Got travalala.com
        strethaddress_to_identifier('0xeD247980396B10169BB1d36f6e278eD16700a60f'),
        # no Bionic in coingecko. Got Bnoincoin
        strethaddress_to_identifier('0xEf51c9377FeB29856E61625cAf9390bD0B67eA18'),
        # no Bitair in coingecko. Got other BTCA symbol tokens
        strethaddress_to_identifier('0x02725836ebF3eCDb1cDf1c7b02FcbBfaa2736AF8'),
        # no Bither in coingecko. Got other BTR symbol tokens
        strethaddress_to_identifier('0xcbf15FB8246F679F9Df0135881CB29a3746f734b'),
        # no Content and Ad Network in coingecko. Got other CAN symbol tokens
        strethaddress_to_identifier('0x5f3789907b35DCe5605b00C0bE0a7eCDBFa8A841'),
        # no DICE money in coingecko. Got other CET symbol tokens
        strethaddress_to_identifier('0xF660cA1e228e7BE1fA8B4f5583145E31147FB577'),
        # no Cyberfi in coingecko. Got other CFI symbol tokens
        strethaddress_to_identifier('0x12FEF5e57bF45873Cd9B62E9DBd7BFb99e32D73e'),
        # The DAO is not in coingecko. Got other DAO symbol tokens
        strethaddress_to_identifier('0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413'),
        # no Earth Token in coingecko. Got other EARTH symbol token and in BSC
        strethaddress_to_identifier('0x900b4449236a7bb26b286601dD14d2bDe7a6aC6c'),
        # no iDice in coingecko. Got other ICE symbol token
        strethaddress_to_identifier('0x5a84969bb663fb64F6d015DcF9F622Aedc796750'),
        # no InvestFeed token in coingecko. Got other IFT symbol token
        strethaddress_to_identifier('0x7654915A1b82D6D2D0AFc37c52Af556eA8983c7E'),
        # no Invacio token in coingecko. Got other INV symbol token
        strethaddress_to_identifier('0xEcE83617Db208Ad255Ad4f45Daf81E25137535bb'),
        # no Live Start token in coingecko. Got other LIVE symbol token
        strethaddress_to_identifier('0x24A77c1F17C547105E14813e517be06b0040aa76'),
        # no Musiconomi in coingecko. Got other MCI symbol token
        strethaddress_to_identifier('0x138A8752093F4f9a79AaeDF48d4B9248fab93c9C'),
        # no Remicoin in coingecko. Got other RMC symbol token
        strethaddress_to_identifier('0x7Dc4f41294697a7903C4027f6Ac528C5d14cd7eB'),
        # no Sola token in coingecko. Got other SOL symbol token
        strethaddress_to_identifier('0x1F54638b7737193FFd86c19Ec51907A7c41755D8'),
        # no Bitcoin card token in coingecko. Got other VD symbol token
        strethaddress_to_identifier('0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D'),
        # no Venus Energy token in coingecko. Got other VENUS symbol token
        strethaddress_to_identifier('0xEbeD4fF9fe34413db8fC8294556BBD1528a4DAca'),
        # no WinToken in coingecko. Got other WIN symbol token
        strethaddress_to_identifier('0xBfaA8cF522136C6FAfC1D53Fe4b85b4603c765b8'),
        # no Snowball in coingecko. Got other SNBL symbol token
        strethaddress_to_identifier('0x198A87b3114143913d4229Fb0f6D4BCb44aa8AFF'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0xFD25676Fc2c4421778B18Ec7Ab86E7C5701DF187'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0xcca0c9c383076649604eE31b20248BC04FdF61cA'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0xAef38fBFBF932D1AeF3B808Bc8fBd8Cd8E1f8BC5'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0x662aBcAd0b7f345AB7FfB1b1fbb9Df7894f18e66'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0x497bAEF294c11a5f0f5Bea3f2AdB3073DB448B56'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0xAbdf147870235FcFC34153828c769A70B3FAe01F'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0x4DF47B4969B2911C966506E3592c41389493953b'),
        # Token suggestion doesn't match token in db
        strethaddress_to_identifier('0xB563300A3BAc79FC09B93b6F84CE0d4465A2AC27'),
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
        strethaddress_to_identifier('0x4D9e23a3842fE7Eb7682B9725cF6c507C424A41B'),
        # coingecko listed newb farm with symbol NEWB that is not our newb
        strethaddress_to_identifier('0x5A63Eb358a751b76e58325eadD86c2473fC40e87'),
        # coingecko has BigBang Core (BBC) that is not tradove
        strethaddress_to_identifier('0xe7D3e4413E29ae35B0893140F4500965c74365e5'),
        # MNT is Meownaut in coingecko and not media network token
        strethaddress_to_identifier('0xA9877b1e05D035899131DBd1e403825166D09f92'),
        # Project quantum in coingecko but we have Qubitica
        strethaddress_to_identifier('0xCb5ea3c190d8f82DEADF7ce5Af855dDbf33e3962'),
        # We have Cashbery Coin for symbol CBC that is not listed in the coingecko list
        'CBC-2',
        # We have Air token for symbol AIR. Got another AIR symbol token
        strethaddress_to_identifier('0x27Dce1eC4d3f72C3E457Cc50354f1F975dDEf488'),
        # We have Acorn Collective for symbol OAK. Got another OAK symbol token
        strethaddress_to_identifier('0x5e888B83B7287EED4fB7DA7b7d0A0D4c735d94b3'),
        # Coingecko has yearn v1 vault yUSD
        strethaddress_to_identifier('0x0ff3773a6984aD900f7FB23A9acbf07AC3aDFB06'),
        # Coingecko has yearn v1 vault yUSD (different vault from above but same symbol)
        strethaddress_to_identifier('0x4B5BfD52124784745c1071dcB244C6688d2533d3'),
        # Coingecko has Aston Martin Cognizant Fan Token and we have AeroME
        'AM',
        # Coingecko has Swarm (BZZ) and we have SwarmCoin
        'SWARM',
        # Coingecko has aircoin and we have a different airtoken
        'AIR-2',
        # Coingecko has Attlas Token and we have Authorship
        strethaddress_to_identifier('0x2dAEE1AA61D60A252DC80564499A69802853583A'),
        # Coingecko has Lever Network and we have Leverj
        strethaddress_to_identifier('0x0F4CA92660Efad97a9a70CB0fe969c755439772C'),
        # Coingecko has Twirl Governance Token and we have Target Coin
        strethaddress_to_identifier('0xAc3Da587eac229C9896D919aBC235CA4Fd7f72c1'),
        # Coingecko has MyWish and we have another WISH (ethereum addresses don't match)
        strethaddress_to_identifier('0x1b22C32cD936cB97C28C5690a0695a82Abf688e6'),
        # Coingecko has DroneFly and we have KlondikeCoin for symbol KDC
        'KDC',
        # Coingecko has CoinStarter and we have Student Coin for symbol STC
        strethaddress_to_identifier('0x15B543e986b8c34074DFc9901136d9355a537e7E'),
        # Coingecko has Nano Dogecoin symbol:ndc and we have NEVERDIE
        strethaddress_to_identifier('0xA54ddC7B3CcE7FC8b1E3Fa0256D0DB80D2c10970'),
        # Coingecko has olecoin and we have Olive
        strethaddress_to_identifier('0x9d9223436dDD466FC247e9dbbD20207e640fEf58'),
        # Coingecko has orica and we have origami
        strethaddress_to_identifier('0xd2Fa8f92Ea72AbB35dBD6DECa57173d22db2BA49'),
        # Coingeckop has a different storm token
        strethaddress_to_identifier('0xD0a4b8946Cb52f0661273bfbC6fD0E0C75Fc6433'),
        # We have Centra (CTR) but coingecko has creator platform
        strethaddress_to_identifier('0x96A65609a7B84E8842732DEB08f56C3E21aC6f8a'),
        # We have Gladius Token (GLA) but coingecko has Galaxy adventure
        strethaddress_to_identifier('0x71D01dB8d6a2fBEa7f8d434599C237980C234e4C'),
        # We have reftoken (REF) and coingecko has Ref Finance
        strethaddress_to_identifier('0x89303500a7Abfb178B274FD89F2469C264951e1f'),
        # We have Aidus (AID) and coingecko has aidcoin
        strethaddress_to_identifier('0xD178b20c6007572bD1FD01D205cC20D32B4A6015'),
        # We have depository network but coingecko has depo
        strethaddress_to_identifier('0x89cbeAC5E8A13F0Ebb4C74fAdFC69bE81A501106'),
        # Sinthetic ETH but coingecko has iEthereum
        strethaddress_to_identifier('0xA9859874e1743A32409f75bB11549892138BBA1E'),
        # blocklancer but coingecko has Linker
        strethaddress_to_identifier('0x63e634330A20150DbB61B15648bC73855d6CCF07'),
        # Kora network but coingecko Knekted
        strethaddress_to_identifier('0xfF5c25D2F40B47C4a37f989DE933E26562Ef0Ac0'),
        # gambit but coingecko has another gambit
        strethaddress_to_identifier('0xF67451Dc8421F0e0afEB52faa8101034ed081Ed9'),
        # publica but coingecko has another polkalab
        strethaddress_to_identifier('0x55648De19836338549130B1af587F16beA46F66B'),
        # Spin protocol but spinada in coingecko
        strethaddress_to_identifier('0x4F22310C27eF39FEAA4A756027896DC382F0b5E2'),
        # REBL but another REBL (rebel finance) in coingecko
        strethaddress_to_identifier('0x5F53f7A8075614b699Baad0bC2c899f4bAd8FBBF'),
        # Sp8de (SPX) but another SPX in coingecko
        strethaddress_to_identifier('0x05aAaA829Afa407D83315cDED1d45EB16025910c'),
        # marginless but another MRS in coingecko
        strethaddress_to_identifier('0x1254E59712e6e727dC71E0E3121Ae952b2c4c3b6'),
        # oyster (PRL) but another PRL in coingecko
        strethaddress_to_identifier('0x1844b21593262668B7248d0f57a220CaaBA46ab9'),
        # oyster shell but another SHL in coingecko
        strethaddress_to_identifier('0x8542325B72C6D9fC0aD2Ca965A78435413a915A0'),
        # dorado but another DOR in coingecko
        strethaddress_to_identifier('0x906b3f8b7845840188Eab53c3f5AD348A787752f'),
        # FundYourselfNow but coingecko has affyn
        strethaddress_to_identifier('0x88FCFBc22C6d3dBaa25aF478C578978339BDe77a'),
        # hat exchange but coingecko has joe hat token
        strethaddress_to_identifier('0x9002D4485b7594e3E850F0a206713B305113f69e'),
        # iconomi but coingecko has icon v2
        strethaddress_to_identifier('0x888666CA69E0f178DED6D75b5726Cee99A87D698'),
        # we have mcap and coingecko has meta capital
        strethaddress_to_identifier('0x93E682107d1E9defB0b5ee701C71707a4B2E46Bc'),
        # we have primalbase but coingecko has property blockchain
        strethaddress_to_identifier('0xF4c07b1865bC326A3c01339492Ca7538FD038Cc0'),
        # Sphere Identity and coingecko has Xid Network
        strethaddress_to_identifier('0xB110eC7B1dcb8FAB8dEDbf28f53Bc63eA5BEdd84'),
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
        strethaddress_to_identifier('0x6949Bb624E8e8A90F87cD2058139fcd77D2F3F87'),
        # sinovate but we have sincity
        'SIN',
        # Hedge protocol but we have Hede crypto coin (book)
        strethaddress_to_identifier('0xfFe8196bc259E8dEDc544d935786Aa4709eC3E64'),
        # realchain but coingecko has reactor
        strethaddress_to_identifier('0x13f25cd52b21650caa8225C9942337d914C9B030'),
        # we have plutusdefi (usde) but coingecko has energi dollar
        'USDE',
        # gearbox is not returned by the coingecko api
        strethaddress_to_identifier('0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
        # bitcoindark but coingecko has bitdollars
        'BTCD',
        strethaddress_to_identifier('0x78a73B6CBc5D183CE56e786f6e905CaDEC63547B'),
        # defidollar but has been marked as inactive
        strethaddress_to_identifier('0x5BC25f649fc4e26069dDF4cF4010F9f706c23831'),
        # zeus but has been marked as inactive
        strethaddress_to_identifier('0xe7E4279b80D319EDe2889855135A22021baf0907'),
        # tok but has been marked as inactive
        strethaddress_to_identifier('0x9a49f02e128a8E989b443a8f94843C0918BF45E7'),
        # fabrik but another ft in coingecko
        strethaddress_to_identifier('0x78a73B6CBc5D183CE56e786f6e905CaDEC63547B'),
        # memorycoin but cc has monopoly
        'MMC',
        # lendconnect but cc has localtraders
        strethaddress_to_identifier('0x05C7065d644096a4E4C3FE24AF86e36dE021074b'),
        # tether GBPT but cc has poundtoken
        'GBPT',
        # hope eth and not huobi eth
        evm_address_to_identifier(address='0xc46F2004006d4C770346f60a7BaA3f1Cc67dFD1c', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0x1fDeAF938267ca43388eD1FdB879eaF91e920c7A', chain_id=ChainID.POLYGON_POS, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0xE38faf9040c7F09958c638bBDB977083722c5156', chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0xDa7c0de432a9346bB6e96aC74e3B61A36d8a77eB', chain_id=ChainID.ARBITRUM_ONE, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0xc46F2004006d4C770346f60a7BaA3f1Cc67dFD1c', chain_id=ChainID.GNOSIS, token_type=TokenKind.ERC20),  # noqa: E501
        # peth from maker but congecko has another PETH
        strethaddress_to_identifier('0xf53AD2c6851052A81B42133467480961B2321C09'),
        # alpaca markets but coingecko has alpaca finance
        strethaddress_to_identifier('0xf5dF66B06DFf95226F1e8834EEbe4006420D295F'),
        # blizzard dao but coingecko has blizzard
        strethaddress_to_identifier('0xbb97a6449A6f5C53b7e696c8B5b6E6A53CF20143'),
        # peth from makerdao but a different one in coignecko
        strethaddress_to_identifier('0x836A808d4828586A69364065A1e064609F5078c7'),
        # stakeit but coingecko has stake (xdai)
        strethaddress_to_identifier('0x836A808d4828586A69364065A1e064609F5078c7'),
        # iron bank dai but coingecko has instadapp-dai
        strethaddress_to_identifier('0x8e595470Ed749b85C6F7669de83EAe304C2ec68F'),
        # iron bank usdc but coingecko has instadapp-usdc
        strethaddress_to_identifier('0x76Eb2FE28b36B3ee97F3Adae0C69606eeDB2A37c'),
        # iron bank btc but coingecko has interest bearing bitcoin
        strethaddress_to_identifier('0xc4E15973E6fF2A35cC804c2CF9D2a1b817a8b40F'),
        # fryUSD but coingecko has fuse dollar
        strethaddress_to_identifier('0x42ef9077d8e79689799673ae588E046f8832CB95'),
        # vanadium dollar but coingecko has version
        strethaddress_to_identifier('0xEe95CD26291fd1ad5d94bCeD4027e396a20d1F38'),
        # cheesefry but coingecko has cheese
        strethaddress_to_identifier('0x332E824e46FcEeB9E59ba9491B80d3e6d42B0B59'),
        # florin but coingecko has flare
        strethaddress_to_identifier('0x5E5d9aEeC4a6b775a175b883DCA61E4297c14Ecb'),
        # wrapped omi but coingecko has wrapped ecomi
        strethaddress_to_identifier('0x04969cD041C0cafB6AC462Bd65B536A5bDB3A670'),
        # fiat stable pool but coingecko has fud aavegochi
        strethaddress_to_identifier('0x178E029173417b1F9C8bC16DCeC6f697bC323746'),
        # titanium dollar but coingecko hash threshold
        strethaddress_to_identifier('0x6967299e9F3d5312740Aa61dEe6E9ea658958e31'),
        # we have transfercoin but coingecko has tradix
        'TX',
        # pear but we have one  with a different address
        strethaddress_to_identifier('0x46cD37F057dC78f6Cd2a4eB89BF9F991fB81BaAb'),
        # tokens that don't match the addresses in coingecko
        strethaddress_to_identifier('0x45fDb1b92a649fb6A64Ef1511D3Ba5Bf60044838'),
        strethaddress_to_identifier('0x69e8b9528CABDA89fe846C67675B5D73d463a916'),
        strethaddress_to_identifier('0xDC59ac4FeFa32293A95889Dc396682858d52e5Db'),
        strethaddress_to_identifier('0x6BeA7CFEF803D1e3d5f7C0103f7ded065644e197'),
        strethaddress_to_identifier('0xcaDC0acd4B445166f12d2C07EAc6E2544FbE2Eef'),
        strethaddress_to_identifier('0x559eBC30b0E58a45Cc9fF573f77EF1e5eb1b3E18'),
        strethaddress_to_identifier('0x8b921e618dD3Fa5a199b0a8B7901f5530D74EF27'),
        strethaddress_to_identifier('0xBEA0000029AD1c77D3d5D23Ba2D8893dB9d1Efab'),
        strethaddress_to_identifier('0x9F77BA354889BF6eb5c275d4AC101e9547f15AdB'),
        # boosted lusd but not lusd. Also no activity on the token
        evm_address_to_identifier(address='0x20658291677a29EFddfd0E303f8b23113d837cC7', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # coingecko has PTS but we have PETAL
        evm_address_to_identifier(address='0x2e60f6C4CA05bC55A8e577DEeBD61FCe727c4a6e', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # USV but the address doesn't match the one in coingecko
        evm_address_to_identifier(address='0x6bAD6A9BcFdA3fd60Da6834aCe5F93B8cFed9598', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # VEE but the address doesn't match the ones in coingecko
        evm_address_to_identifier(address='0x7616113782AaDAB041d7B10d474F8A0c04EFf258', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # Alladin cvxCRV but coingecko has aave crv
        evm_address_to_identifier(address='0x2b95A1Dcc3D405535f9ed33c219ab38E8d7e0884', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # coingecko has crypto price intex that doesn't match the address
        evm_address_to_identifier(address='0x8bb08042c06FA0Fc26cd2474C5F0C03a1056Ad2F', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        evm_address_to_identifier(address='0x85089389C14Bd9c77FC2b8F0c3d1dC3363Bf06Ef', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        'RVR',  # revolutionVR but coingecko has reality vr
        'BTG-2',  # bitgem but coingecko has bitcoin gold
        # karate but coingecko has karate combat
        evm_address_to_identifier(address='0xAcf79C09Fff518EcBe2A96A2c4dA65B68fEDF6D3', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501
        # simp but coingecko has socol
        evm_address_to_identifier(address='0xD0ACCF05878caFe24ff8b3F82F194C62Ed755707', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501
        # coingecko has a turbos in sui
        evm_address_to_identifier(address='0x0678Ca162E737C44cab2Ea31b4bbA78482E1313d', chain_id=ChainID.BINANCE_SC, token_type=TokenKind.ERC20),  # noqa: E501
        # inx but coingecko has different address
        evm_address_to_identifier(address='0x84fE25f3921f3426395c883707950d0c00367576', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
        # monfter but coingecko doesn't match any
        evm_address_to_identifier(address='0xcaCc19C5Ca77E06D6578dEcaC80408Cc036e0499', chain_id=ChainID.ETHEREUM, token_type=TokenKind.ERC20),  # noqa: E501
    )
    for asset_data in GlobalDBHandler().get_all_asset_data(mapping=False):
        identifier = asset_data.identifier
        if (
            identifier in DELISTED_ASSETS or  # delisted assets won't be in the mapping
            asset_data.asset_type == AssetType.FIAT or
            asset_data.protocol == SPAM_PROTOCOL
        ):
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

        msg = f'Asset {identifier} with symbol {asset_data.symbol} coingecko mapping {asset_data.coingecko} does not exist.'  # noqa: E501
        if len(suggestions) != 0:
            for s in suggestions:
                msg += f'\nSuggestion: id:{s[0]} name:{s[1]} symbol:{s[2]}'
        if not found:
            test_warnings.warn(UserWarning(msg))


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('force_reinitialize_asset_resolver', [True])
def test_get_or_create_evm_token(globaldb, database):
    cursor = globaldb.conn.cursor()
    assets_num = cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0]
    assert get_or_create_evm_token(
        userdb=database,
        symbol='DAI',
        evm_address='0x6B175474E89094C44Da98b954EedeAC495271d0F',
        chain_id=ChainID.ETHEREUM,
    ) == A_DAI
    # Try getting a DAI token of a different address. Should add new token to DB
    new_token = get_or_create_evm_token(
        userdb=database,
        symbol='DAI',
        evm_address='0xA379B8204A49A72FF9703e18eE61402FAfCCdD60',
        chain_id=ChainID.ETHEREUM,
    )
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 1
    assert new_token.symbol == 'DAI'
    assert new_token.evm_address == '0xA379B8204A49A72FF9703e18eE61402FAfCCdD60'
    # Try getting a symbol of normal chain with different address. Should add new token to DB
    new_token = get_or_create_evm_token(
        userdb=database,
        symbol='DOT',
        evm_address='0xB179B8204A49672FF9703e18eE61402FAfCCdD60',
        chain_id=ChainID.ETHEREUM,
    )
    assert new_token.symbol == 'DOT'
    assert new_token.evm_address == '0xB179B8204A49672FF9703e18eE61402FAfCCdD60'
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2
    # Check that token with wrong symbol but existing address is returned
    assert get_or_create_evm_token(
        userdb=database,
        symbol='ROFL',
        evm_address='0xdAC17F958D2ee523a2206206994597C13D831ec7',
        chain_id=ChainID.ETHEREUM,
    ) == A_USDT
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2


def test_resolve_nft():
    """Test that a special case of nft is handled when checking asset type and when resolving"""
    nft_asset = Asset('_nft_foo')
    assert nft_asset.is_nft() is True
    assert nft_asset.is_fiat() is False
    assert nft_asset.resolve() == Nft.initialize(
        identifier='_nft_foo',
        chain_id=ChainID.ETHEREUM,
    )


def test_symbol_or_name(database):
    db_custom_assets = DBCustomAssets(database)
    db_custom_assets.add_custom_asset(CustomAsset.initialize(
        identifier='xyz',
        name='custom name',
        custom_asset_type='lolkek',
    ))
    assert Asset('ETH').symbol_or_name() == 'ETH'
    assert Asset('xyz').symbol_or_name() == 'custom name'
    with pytest.raises(UnknownAsset):
        Asset('i-dont-exist').symbol_or_name()


def test_load_from_packaged_db(globaldb: GlobalDBHandler):
    """Test that connecting to the packaged globaldb doesn't try to write into it."""
    packaged_db_path = Path(__file__).resolve().parent.parent.parent / 'data' / GLOBALDB_NAME
    with TemporaryDirectory(
            ignore_cleanup_errors=True,  # needed on windows, see https://tinyurl.com/tmp-win-err
    ) as tmpdirname:
        # Create a copy of the global db in a temp file
        dest_file = Path(tmpdirname) / 'data' / GLOBALDB_NAME
        os.makedirs(dest_file.parent, exist_ok=True)
        backup = Path(shutil.copy(packaged_db_path, dest_file))

        # connect to the database and edit it to verify that we are later connecting
        # to the right one
        conn = rsqlite.connect(dest_file, check_same_thread=False)
        conn.cursor().execute('UPDATE assets SET name="my eth" WHERE identifier="ETH"')
        conn.commit()
        conn.close()

        # set the permissions for the copy of the globaldb to read only. This ensures
        # that no write happen without raising an error
        backup.chmod(0o444)

        # mock Path parent attribute to return the destination file always
        def parent():
            return Path(tmpdirname)

        # mock the parent method from pathlib in the initialization of the globaldb
        with patch('pathlib.Path.parent', new_callable=PropertyMock) as mock_path:
            mock_path.side_effect = parent
            # the execution of the function shouldn't raise any error
            globaldb.packaged_db_conn()

        # check that we can read from the database and is the correct one
        assert globaldb._packaged_db_conn is not None
        with globaldb._packaged_db_conn.cursor() as cursor:
            cursor.execute('SELECT name FROM assets WHERE identifier="ETH"')
            assert cursor.fetchone()[0] == 'my eth'


def test_nexo_converter():
    """Test that we don't have overlapping keys in nexo and resolve to the expected assets"""
    assert asset_from_nexo('USDT') == A_USDT
    assert asset_from_nexo('USDTERC') == A_USDT
    assert EvmToken('eip155:1/erc20:0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206') == asset_from_nexo('NEXONEXO')  # noqa: E501


def test_spam_detection_respects_whitelist(globaldb: 'GlobalDBHandler', database: 'DBHandler'):
    """Check that automatic spam detection doesn't add whitelisted assets"""
    token = Asset('eip155:1/erc20:0xB63B606Ac810a52cCa15e44bB630fd42D8d1d83d')  # crypto.com that gets detected as spam due to the . in the name  # noqa: E501
    new_token_whitelisted = EvmToken.initialize(
        address=make_evm_address(),
        name='crypto.com',  # use a number that will flag it as spam
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
    )
    globaldb.add_asset(new_token_whitelisted)

    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
            values=(new_token_whitelisted.identifier,),
        )

    autodetect_spam_assets_in_db(database)
    assert token.resolve_to_evm_token().protocol != SPAM_PROTOCOL
    assert Asset(new_token_whitelisted.identifier).resolve_to_evm_token().protocol != SPAM_PROTOCOL
    assert should_run_periodic_task(
        database=database,
        key_name=DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY,
        refresh_period=SPAM_ASSETS_DETECTION_REFRESH,
    ) is False


def test_all_assets_pagination(globaldb: 'GlobalDBHandler', database: 'DBHandler'):
    """Test the pagination by OFFSET and LIMIT parameters in the assets retrieval function.
    With page1 having un-ignored assets from 0-10 and page2 having un-ignored assets from 10-20,
    page1 and page2 should be different, and page1 + page2 should return assets from 0-20."""
    page1, page2 = (globaldb.retrieve_assets(
        userdb=database,
        filter_query=AssetsFilterQuery.make(
            and_op=True,
            limit=10,
            offset=offset,
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,
        ),
    ) for offset in (10, 20))
    both_pages = globaldb.retrieve_assets(
        userdb=database,
        filter_query=AssetsFilterQuery.make(
            and_op=True,
            limit=20,
            offset=10,
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,
        ),
    )
    assert page1[0] != page2[0]
    assert page1[0] + page2[0] == both_pages[0]

    # test that we calculate the entries found correctly
    _, found_without_ignored = globaldb.retrieve_assets(
        userdb=database,
        filter_query=AssetsFilterQuery.make(
            and_op=True,
            limit=10,
            offset=0,
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,
        ),
    )
    _, found_all = globaldb.retrieve_assets(
        userdb=database,
        filter_query=AssetsFilterQuery.make(
            and_op=True,
            limit=10,
            offset=0,
            ignored_assets_handling=IgnoredAssetsHandling.NONE,
        ),
    )
    _, found_ignored = globaldb.retrieve_assets(
        userdb=database,
        filter_query=AssetsFilterQuery.make(
            and_op=True,
            limit=10,
            offset=0,
            ignored_assets_handling=IgnoredAssetsHandling.SHOW_ONLY,
        ),
    )
    assert found_ignored < found_without_ignored < found_all


def test_merge_assets_timed_balances(database: 'DBHandler') -> None:
    """Ensure that timed balances are merged when replacing assets.
    This is a regression test.
    """
    with database.conn.write_ctx() as write_cursor:
        serialized_balances = [
            (0, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (0, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
            (0, 'ETH', '0.50', '87', BalanceType.LIABILITY.serialize_for_db()),
            (1, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (1, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
            (2, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (3, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
        ]
        write_cursor.executemany(
            'INSERT INTO timed_balances( '
            'timestamp, currency, amount, usd_value, category) '
            ' VALUES(?, ?, ?, ?, ?)',
            serialized_balances,
        )

    database.replace_asset_identifier(source_identifier='ETH', target_asset=Asset('BTC'))
    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT timestamp, currency, amount, category FROM timed_balances')
        assert cursor.fetchall() == [
            (0, 'BTC', '2.0', BalanceType.ASSET.serialize_for_db()),  # 1 ETH + 1 BTC
            (0, 'BTC', '0.5', BalanceType.LIABILITY.serialize_for_db()),  # 0.5 ETH -> 0.5 BTC
            (1, 'BTC', '2.0', BalanceType.ASSET.serialize_for_db()),  # 1 ETH + 1 BTC
            (2, 'BTC', '1.0', BalanceType.ASSET.serialize_for_db()),  # 1 BTC = 1 BTC
            (3, 'BTC', '1.0', BalanceType.ASSET.serialize_for_db()),  # 1 ETH -> 1 BTC
        ]
