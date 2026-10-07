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
from rotkehlchen.assets import asset as asset_module
from rotkehlchen.assets.asset import (
    Asset,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    FiatAsset,
    Nft,
    UnderlyingToken,
)
from rotkehlchen.assets.converters import asset_from_nexo
from rotkehlchen.assets.ignored_assets_handling import IgnoredAssetsHandling
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.assets.utils import (
    get_crypto_asset_by_symbol,
    get_or_create_evm_token,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
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
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    SolanaAddress,
    TokenKind,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def query_all_asset_data() -> list[AssetData]:
    """Return all asset data from the global DB in a single bulk query.

    Test-only helper used by the checks that need to iterate over every asset.
    Doing it in one query avoids a per-asset roundtrip to the DB.
    """
    result: list[AssetData] = []
    querystr = f"""
    SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind FROM assets as A JOIN evm_tokens as B
    ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = '{AssetType.EVM_TOKEN.serialize_for_db()}'
    UNION ALL
    SELECT A.identifier, A.type, S.address, S.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, S.protocol, null, S.token_kind FROM assets as A JOIN solana_tokens as S
    ON S.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = S.identifier WHERE A.type = '{AssetType.SOLANA_TOKEN.serialize_for_db()}'
    UNION ALL
    SELECT A.identifier, A.type, null, null, A.name, B.symbol, B.started, B.forked, B.swapped_for, B.coingecko, B.cryptocompare, null, null, null from assets as A JOIN common_asset_details as B
    ON B.identifier = A.identifier WHERE A.type NOT IN ('{AssetType.EVM_TOKEN.serialize_for_db()}', '{AssetType.SOLANA_TOKEN.serialize_for_db()}');
    """  # noqa: E501
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for entry in cursor.execute(querystr):
            asset_type = AssetType.deserialize_from_db(entry[1])
            address: ChecksumEvmAddress | SolanaAddress | None
            token_kind: TokenKind | None
            if asset_type == AssetType.EVM_TOKEN:
                address = string_to_evm_address(entry[2])
                chain_id = ChainID.deserialize_from_db(entry[12])
                token_kind = TokenKind.deserialize_evm_from_db(entry[13])
            elif asset_type == AssetType.SOLANA_TOKEN:
                address = SolanaAddress(entry[2])
                chain_id = None
                token_kind = TokenKind.deserialize_solana_from_db(entry[13])
            else:
                address, chain_id, token_kind = None, None, None
            result.append(AssetData(
                identifier=entry[0],
                asset_type=asset_type,
                address=address,
                chain_id=chain_id,
                token_kind=token_kind,
                decimals=entry[3],
                name=entry[4],
                symbol=entry[5],
                started=entry[6],
                forked=entry[7],
                swapped_for=entry[8],
                coingecko=entry[9],
                cryptocompare=entry[10],
                protocol=entry[11],
            ))

    return result


def test_unknown_asset():
    """Test than an unknown asset will throw"""
    with pytest.raises(UnknownAsset):
        FiatAsset('jsakdjsladjsakdj')


def test_asset_nft():
    a = Asset('_nft_foo')
    assert a.identifier == '_nft_foo'
    should_not_exist = {'name', 'symbol', 'started', 'forked', 'swapped_for', 'cryptocompare', 'coingecko'}  # noqa: E501
    assert all(hasattr(a, attr) is False for attr in should_not_exist)


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


@pytest.fixture(name='allow_case_mismatch')
def fixture_allow_case_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let a test compare deliberately miscased identifiers.

    The suite-wide _asset_case_diagnostics fixture turns a case-only mismatch into a failure,
    which is precisely what the tests pinning the comparison contract construct on purpose.
    """
    monkeypatch.setattr(asset_module, 'ASSET_CASE_DIAGNOSTICS', False)


@pytest.mark.usefixtures('allow_case_mismatch')
def test_asset_equals():
    btc_asset = Asset('BTC')
    eth_asset = Asset('ETH')
    other_btc_asset = Asset('BTC')

    assert btc_asset == 'BTC'
    assert btc_asset != eth_asset
    assert btc_asset != 'ETH'
    assert btc_asset == other_btc_asset
    assert eth_asset == 'ETH'
    # identifiers are compared exactly. Normalizing is the boundary's job, so a differently
    # cased identifier is a missing normalization and must not silently compare equal
    assert Asset('eTh') != eth_asset
    assert Asset('eTh') != 'ETH'


@pytest.mark.usefixtures('allow_case_mismatch')
def test_asset_hash_matches_equality():
    """Equal assets must hash equal, and the Asset<->str key contract must survive"""
    assert hash(Asset('ETH')) == hash(Asset('ETH'))
    assert len({Asset('ETH'), Asset('ETH')}) == 1
    # the contract asserted by test_asset_hashes_properly
    assert hash(Asset('ETH')) == hash('ETH')
    # differently cased identifiers are unequal, so they are allowed to hash differently.
    # What must not happen is the reverse: equal assets hashing differently
    assert Asset('eTh') != Asset('ETH')


@pytest.mark.usefixtures('allow_case_mismatch')
def test_asset_ordering_agrees_with_equality():
    """@total_ordering derives __le__/__gt__/__ge__ from __eq__ and __lt__, so the two must
    not contradict each other or sorting becomes dependent on the input order"""
    for first, second in (
            (Asset('BTC'), Asset('ETH')),
            (Asset('eTh'), Asset('ETH')),
            (Asset('ETH'), Asset('ETH')),
    ):
        assert not (first == second and (first < second or second < first))
        assert (first == second) != (first < second or second < first)


def test_ethereum_tokens():
    rdn_asset = EvmToken('eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6')
    assert rdn_asset.evm_address == '0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'
    assert rdn_asset.decimals == 18
    assert rdn_asset.is_evm_token()

    with pytest.raises(WrongAssetType):
        EvmToken('BTC')


def test_assets_tokens_addresses_are_checksummed():
    """Test that all ethereum saved token asset addresses are checksummed"""
    for asset_data in query_all_asset_data():
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
    for asset_data in query_all_asset_data():
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
        evm_address='0xb179b8204a49672ff9703E18EE61402fafCCdD60',
        chain_id=ChainID.ETHEREUM,
    )
    assert new_token.symbol == 'DOT'
    assert new_token.evm_address == '0xb179b8204a49672ff9703E18EE61402fafCCdD60'
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2
    # Check that token with wrong symbol but existing address is returned
    assert get_or_create_evm_token(
        userdb=database,
        symbol='ROFL',
        evm_address='0xdAC17F958D2ee523a2206206994597C13D831ec7',
        chain_id=ChainID.ETHEREUM,
    ) == A_USDT
    assert cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0] == assets_num + 2


def test_edit_placeholder_token_keeps_missing_metadata(globaldb, database):
    """Editing a single field of a token with missing metadata must not persist the
    placeholders the loaded token object holds for that missing metadata"""
    GlobalDBHandler.add_asset(EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='Parent',
        symbol='PRNT',
        decimals=18,
        underlying_tokens=[UnderlyingToken(
            address=(underlying_address := make_evm_address()),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    ))
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=underlying_address,
        chain_id=ChainID.ETHEREUM,
        protocol='some-protocol',
    )
    assert globaldb.conn.cursor().execute(
        'SELECT A.name, C.symbol, B.decimals, B.protocol FROM assets AS A '
        'JOIN evm_tokens AS B ON A.identifier=B.identifier '
        'JOIN common_asset_details AS C ON A.identifier=C.identifier WHERE A.identifier=?',
        (token.identifier,),
    ).fetchone() == (None, None, None, 'some-protocol')


def test_same_underlying_tokens_as_list_do_not_edit_token(database):
    """Underlying tokens given as a list equal to the stored ones are not a change"""
    GlobalDBHandler.add_asset(EvmToken.initialize(
        address=(address := make_evm_address()),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='Parent',
        symbol='PRNT',
        decimals=18,
        underlying_tokens=(underlying_tokens := [UnderlyingToken(
            address=A_DAI.resolve_to_evm_token().evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )]),
    ))
    with patch.object(GlobalDBHandler, 'edit_token_fields') as edit_token_fields:
        get_or_create_evm_token(
            userdb=database,
            evm_address=address,
            chain_id=ChainID.ETHEREUM,
            underlying_tokens=underlying_tokens,
        )
    assert edit_token_fields.call_count == 0


def test_token_with_missing_metadata_loads_the_same_everywhere(globaldb):
    """A token with NULL name, symbol and decimals must load with the same values
    through the resolver and through the token queries"""
    GlobalDBHandler.add_asset(EvmToken.initialize(
        address=(address := make_evm_address()),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
    ))
    resolved = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
    queried = globaldb.get_evm_token(address=address, chain_id=ChainID.ETHEREUM)
    assert resolved.to_dict() == queried.to_dict()
    assert (resolved.name, resolved.symbol, resolved.decimals) == (resolved.identifier, '', None)


def test_resolve_nft():
    """Test that a special case of nft is handled when checking asset type and when resolving"""
    nft_asset = Asset('_nft_foo')
    assert nft_asset.is_nft() is True
    assert nft_asset.is_fiat() is False
    assert nft_asset.resolve() == Nft.initialize(
        identifier='_nft_foo',
        chain_id=ChainID.ETHEREUM,
    )


def test_resolver_cache_clean_during_resolution_not_resurrected(globaldb: GlobalDBHandler):
    """A cache clean for an edited/deleted asset landing while a resolution is in
    flight must not be undone by that resolution writing its stale result back"""
    AssetResolver.clean_memory_cache()
    original_resolve = GlobalDBHandler.resolve_asset

    def resolve_then_concurrent_edit(*args, **kwargs):
        result = original_resolve(*args, **kwargs)
        # an edit of the asset lands after the DB read but before the write-back
        AssetResolver.clean_memory_cache(A_DAI.identifier)
        return result

    with patch.object(GlobalDBHandler, 'resolve_asset', side_effect=resolve_then_concurrent_edit):
        assert A_DAI.resolve().identifier == A_DAI.identifier
    assert AssetResolver.assets_cache.get(A_DAI.identifier) is None, 'stale result should not have been cached'  # noqa: E501

    # without an interleaved clean the resolution populates the cache normally
    assert A_DAI.resolve().identifier == A_DAI.identifier
    assert AssetResolver.assets_cache.get(A_DAI.identifier) is not None

    # a resolution inside an open global DB write transaction (own uncommitted
    # data) must not enter the cache either
    AssetResolver.clean_memory_cache()
    with globaldb.conn.write_ctx():
        assert A_DAI.resolve().identifier == A_DAI.identifier
        assert AssetResolver.assets_cache.get(A_DAI.identifier) is None
    assert AssetResolver.assets_cache.get(A_DAI.identifier) is None


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


def test_spam_detection_respects_whitelist(globaldb: GlobalDBHandler, database: DBHandler):
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


def test_all_assets_pagination(globaldb: GlobalDBHandler, database: DBHandler):
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


def test_merge_assets_timed_balances(database: DBHandler) -> None:
    """Ensure that timed balances are merged when replacing assets.
    This is a regression test.
    """
    with database.conn.write_ctx() as write_cursor:
        serialized_balances = [
            # ts 0: source(ETH) inserted BEFORE target(BTC) for the shared asset row. This is the
            # case that used to leave a stale duplicate target row and double-count it, since the
            # merge result depended on which row sqlite happened to pick in its GROUP BY.
            (0, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
            (0, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (0, 'ETH', '0.50', '87', BalanceType.LIABILITY.serialize_for_db()),
            (1, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (1, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
            (2, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
            (3, 'ETH', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
            # ts 4: high-precision amounts that are NOT float-exact, both present at the same
            # timestamp. Locks in that the sum is computed with FVal (exact) and not via a
            # float-coercing SQL SUM() over the TEXT columns.
            (4, 'ETH', '0.1', '0', BalanceType.ASSET.serialize_for_db()),
            (4, 'BTC', '0.2', '0', BalanceType.ASSET.serialize_for_db()),
            # ts 5: a single high-precision source row, to ensure even unmerged rows keep their
            # full precision instead of being truncated to a float.
            (5, 'ETH', '123456789.123456789123456789', '0', BalanceType.ASSET.serialize_for_db()),
        ]
        write_cursor.executemany(
            'INSERT INTO timed_balances( '
            'timestamp, currency, amount, usd_value, category) '
            ' VALUES(?, ?, ?, ?, ?)',
            serialized_balances,
        )

    database.replace_asset_identifier(source_identifier='ETH', target_asset=Asset('BTC'))
    with database.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT timestamp, currency, amount, category FROM timed_balances '
            'ORDER BY timestamp, category',
        )
        assert cursor.fetchall() == [
            (0, 'BTC', '2', BalanceType.ASSET.serialize_for_db()),  # 1 ETH + 1 BTC, single row
            (0, 'BTC', '0.5', BalanceType.LIABILITY.serialize_for_db()),  # 0.5 ETH -> 0.5 BTC
            (1, 'BTC', '2', BalanceType.ASSET.serialize_for_db()),  # 1 ETH + 1 BTC
            (2, 'BTC', '1', BalanceType.ASSET.serialize_for_db()),  # 1 BTC = 1 BTC
            (3, 'BTC', '1', BalanceType.ASSET.serialize_for_db()),  # 1 ETH -> 1 BTC
            (4, 'BTC', '0.3', BalanceType.ASSET.serialize_for_db()),  # 0.1 + 0.2 exactly, not 0.3000..04  # noqa: E501
            (5, 'BTC', '123456789.123456789123456789', BalanceType.ASSET.serialize_for_db()),  # full precision kept  # noqa: E501
        ]
