import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, Set

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


MISSING_NAME_SPAM_TOKEN = 'Autodetected spam token'
MISSING_SYMBOL_SPAM_TOKEN = 'SPAM-TOKEN'

KNOWN_ETH_SPAM_TOKENS: Dict[ChecksumEvmAddress, Dict[str, Any]] = {
    # khex.net and said to be spam by etherscan
    string_to_evm_address('0x4AF9ab04615cB91e2EE8cbEDb43fb52eD205041B'): {
        'name': MISSING_NAME_SPAM_TOKEN,
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # yLiquidate (YQI) seems to be a scam
    string_to_evm_address('0x3d3d5cCE38afb7a379B2C3175Ee56e2dC72CD7C8'): {
        'name': 'yLiquidate',
        'symbol': 'YQI',
        'decimals': 18,
    },
    # Old kick token
    string_to_evm_address('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'): {
        'name': 'KICK TOKEN OLD',
        'symbol': 'KICK',
        'decimals': 18,
    },
    # kick token. Only can be withdrawn from their exchange
    string_to_evm_address('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'): {
        'name': 'KICK TOKEN',
        'symbol': 'KICK',
        'decimals': 18,
    },
    # Fake gear token warned by etherscan
    string_to_evm_address('0x6D38b496dCc9664C6908D8Afba6ff926887Fc359'): {
        'name': 'FAKE gear token',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # EthTrader Contribution (CONTRIB) few txs and all failed
    string_to_evm_address('0xbe1fffB262a2C3e65c5eb90f93caf4eDC7d28c8d'): {
        'name': 'EthTrader Contribution',
        'symbol': 'CONTRIB',
        'decimals': 18,
    },
    string_to_evm_address('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'): {
        'name': 'a68.net',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x82dfDB2ec1aa6003Ed4aCBa663403D7c2127Ff67'): {
        'name': 'akswap.io',
        'symbol': 'akswap.io',
        'decimals': 18,
    },
    string_to_evm_address('0x43661F4b1c67dd6c1e48C6Faf2887b22AeE3dDf5'): {
        'name': 'akswap.io',
        'symbol': 'akswap.io',
        'decimals': 18,
    },
    string_to_evm_address('0xF9d25EB4C75ed744596392cf89074aFaA43614a8'): {
        'name': 'UP1.org',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x01454cdC3FAb2a026CC7d1CB2aEa9B909D5bA0EE'): {
        'name': 'deApy.org',
        'symbol': 'deApy.org',
        'decimals': 18,
    },
    string_to_evm_address('0x73885eb0dA4ba8B061acF1bfC5eA7073B07ccEA2'): {
        'name': 'Adidas fake token',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xc85E0474068dbA5B49450c26879541EE6Cc94554'): {
        'name': 'KyDy.org',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'): {
        'name': 'A68.net',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # Apple spam/scam token
    string_to_evm_address('0x3c4f8Fe3Cf50eCA5439F8D4DE5BDf40Ae71860Ae'): {
        'name': 'Apple 29',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # Blizzard spam/scam token
    string_to_evm_address('0xbb97a6449A6f5C53b7e696c8B5b6E6A53CF20143'): {
        'name': 'Activision Blizzard DAO',
        'symbol': 'BLIZZARD',
        'decimals': 18,
    },
    # Audi spam/scam token
    string_to_evm_address('0x9b9090DfA2cEbBef592144EE01Fe508f0c817B3A'): {
        'name': 'Audi Metaverse',
        'symbol': 'Audi',
        'decimals': 18,
    },
    # LunaV2.io (Luna Token)
    string_to_evm_address('0xAF0b2fBeDd5d1Fda457580FB3DAbAD1F5C8bBC36'): {
        'name': 'LunaV2.io',
        'symbol': 'Luna Token',
        'decimals': 18,
    },
    string_to_evm_address('0x3baB61Ad5D103Bb5b203C9092Eb3a5e11677a5D0'): {
        'name': 'ETH2Dao.net',
        'symbol': 'ETH2DAO.net',
        'decimals': 18,
    },
    string_to_evm_address('0x622651529Bda465277Cb890EF9176C442f42B338'): {
        'name': 'abekky.com',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xED123a93aB410deD50D917EDfE256D45281B95D5'): {
        'name': 'SPAM TOKEN',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xb1A5FEcEBbfB02F6F44d69a4b7f096Af552C486B'): {
        'name': '(lidosr.xyz)',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 6,
    },
    string_to_evm_address('0x6D9541ba0f1039d0f8636b4f39D20A8a7464f357'): {
        'name': 'mdai.io',
        'symbol': 'mdai.io',
        'decimals': 18,
    },
    string_to_evm_address('0x17a10104CBC1eD155D083eaD9FCF5C3440bb50e8'): {
        'name': '$ USDCNotice.com',
        'symbol': '$ USDCNotice.com <- Visit to secure your wallet!',
        'decimals': 18,
    },
    string_to_evm_address('0x219B9040eB7D8d8c2E8E84B87CE9ac1C83071980'): {
        'name': 'Huobi Airdrop HuobiAirdrop.com',
        'symbol': 'HuobiAirdrop.com',
        'decimals': 18,
    },
    string_to_evm_address('0x3b0811f422cF7e9A46e7Ce22B1425A57949b5360'): {
        'name': '(sodefi.tech)',
        'symbol': '[sodefi.tech] Visit and claim rewards',
        'decimals': 6,
    },
    string_to_evm_address('0x471c3A7f132bc94938516CB2Bf6f02C7521D2797'): {
        'name': 'LUNA 2.0 (lunav2.io)',
        'symbol': 'LUNA 2.0 (lunav2.io)',
        'decimals': 18,
    },
    string_to_evm_address('0x4E0b2A80E158f8d28a2007866ab80B7f63bE6076'): {
        'name': 'Owlswap.org',
        'symbol': 'OWLT',
        'decimals': 18,
    },
    string_to_evm_address('0x4f4d22cA77222aE3D51e308C9A8F0E564F98e77A'): {
        'name': 'Bulleon Promo Token',
        'symbol': 'BULLEON-X',
        'decimals': 18,
    },
    string_to_evm_address('0x5D80A8D8CB80696073e82407968600A37e1dd780'): {
        'name': 'aave-sr.xyz',
        'symbol': 'Visit [aave-sr.xyz] and claim special rewards',
        'decimals': 6,
    },
    string_to_evm_address('0x695d4e4936C0DE413267C75ca684fc317e03A819'): {
        'name': 'ApeSnoop.com',
        'symbol': 'Ape Dog Coin',
        'decimals': 18,
    },
    string_to_evm_address('0x7B2f9706CD8473B4F5B7758b0171a9933Fc6C4d6'): {
        'name': 'An Etheal Promo',
        'symbol': 'HEALP',
        'decimals': 18,
    },
    string_to_evm_address('0x7C743517f34daEfc6477D44b0a2a12dE6fA38Ea2'): {
        'name': '! Uniswapv3LP.com !',
        'symbol': 'Uniswapv3LP.com',
        'decimals': 18,
    },
    string_to_evm_address('0x8f5a1Cb27cfeD6A640dE424e9c0abbCeaad0b620'): {
        'name': 'uETH.io',
        'symbol': 'uETH.io',
        'decimals': 18,
    },
    string_to_evm_address('0xAF0b2fBeDd5d1Fda457580FB3DAbAD1F5C8bBC36'): {
        'name': 'LunaV2.io (Luna Token)',
        'symbol': 'LunaV2.io (Luna Token)',
        'decimals': 18,
    },
    string_to_evm_address('0xCf39B7793512F03f2893C16459fd72E65D2Ed00c'): {
        'name': '$ UniswapLP.com',
        'symbol': 'UniswapLP.com',
        'decimals': 18,
    },
    string_to_evm_address('0xD4DE05944572D142fBf70F3f010891A35AC15188'): {
        'name': 'Bulleon Promo Token',
        'symbol': 'BULLEON PROMO',
        'decimals': 18,
    },
    string_to_evm_address('0xF0df09387693690b1E00D71eabF5E98e7955CFf4'): {
        'name': 'ENDO.network Promo Token',
        'symbol': 'ETP',
        'decimals': 18,
    },
    string_to_evm_address('0xc2e39D0Afa884192F2Cc55D841C2C8c5681DbF17'): {
        'name': '(avrc.xyz)',
        'symbol': 'avrc.xyz',
        'decimals': 6,
    },
    string_to_evm_address('0xd202ec9D73d8D66242312495e3F72248e8d08d60'): {
        'name': 'avrc',
        'symbol': 'okchat.io',
        'decimals': 18,
    },
    string_to_evm_address('0xB688d06d858E092EBB145394a1BA08C7a10E1F56'): {
        'name': 'acrone.site',
        'symbol': 'acrone.site',
        'decimals': 18,
    },
    string_to_evm_address('0xA36Ceec605d81aE74268Fda28A5c0Bd10b1D1f7C'): {
        'name': 'AaveLP.com',
        'symbol': 'AaveLP.com',
        'decimals': 18,
    },
    string_to_evm_address('0x0432ca79d0bF2546bC9a29685636e413B137692d'): {
        'name': 'Compound-Claim.com',
        'symbol': 'Compound-Claim.com',
        'decimals': 18,
    },
    string_to_evm_address('0x070C0147884D7CF984aFBC2Eb6F3428A39b5E229'): {
        'name': 'asdai.xyz',
        'symbol': 'https://asdai.xyz',
        'decimals': 18,
    },
    string_to_evm_address('0x2f848B4A2B5dfC3b9e4Eb229551c0887E6348653'): {
        'name': 'ardai.xyz',
        'symbol': 'https://ardai.xyz',
        'decimals': 18,
    },
    string_to_evm_address('0xF5b2C59F6DB42FFCdFC1625999C81fDF17953384'): {
        'name': 'mdai.io',
        'symbol': 'mdai.io',
        'decimals': 18,
    },
    string_to_evm_address('0xe0c230B6DC9a90Cc5F1b8B62e83AF234f108563b'): {
        'name': 'Try Mushrooms Finance',
        'symbol': 'Try Mushrooms Finance',
        'decimals': 18,
    },
    string_to_evm_address('0xf5dF66B06DFf95226F1e8834EEbe4006420D295F'): {
        'name': 'https://alpaca.markets/',
        'symbol': 'ALPACA',
        'decimals': 18,
    },
    string_to_evm_address('0xac2b43262aE5f3bCD3831EA33A6B5d0f2044C9FB'): {
        'name': 'PiCoreTeam',
        'symbol': 'Pi',
        'decimals': 1,
    },
    string_to_evm_address('0x519475b31653E46D20cD09F9FdcF3B12BDAcB4f5'): {
        'name': 'VIU',
        'symbol': 'VIU',
        'decimals': 18,
    },
    string_to_evm_address('0xaF47ebBd460F21c2b3262726572CA8812d7143B0'): {
        'name': 'Promodl',
        'symbol': 'PMOD',
        'decimals': 18,
    },
    string_to_evm_address('0x1C3BB10dE15C31D5DBE48fbB7B87735d1B7d8c32'): {
        'name': 'BLONDCOIN',
        'symbol': 'BLO',
        'decimals': 18,
    },
    string_to_evm_address('0x2630997aAB62fA1030a8b975e1AA2dC573b18a13'): {
        'name': 'HYPE Token',
        'symbol': 'HYPE',
        'decimals': 18,
    },
    string_to_evm_address('0x2e91E3e54C5788e9FdD6A181497FDcEa1De1bcc1'): {
        'name': 'Hercules',
        'symbol': 'HERC',
        'decimals': 18,
    },
    string_to_evm_address('0x4E546b4A29E2De365aE16BC7B69812Ce3fd943A7'): {
        'name': 'VKTToken',
        'symbol': 'VKT',
        'decimals': 18,
    },
    string_to_evm_address('0x5C406D99E04B8494dc253FCc52943Ef82bcA7D75'): {
        'name': 'cUSD Currency',
        'symbol': 'cUSD',
        'decimals': 18,
    },
    string_to_evm_address('0x68e14bb5A45B9681327E16E528084B9d962C1a39'): {
        'name': 'BitClave - Consumer Activity Token',
        'symbol': 'CAT',
        'decimals': 18,
    },
    string_to_evm_address('0x6ff313FB38d53d7A458860b1bf7512f54a03e968'): {
        'name': 'Mero Currency',
        'symbol': 'MRO',
        'decimals': 18,
    },
    string_to_evm_address('0x75EfC1111f98f2d5DCeC9851c8abC77cd5E6CED8'): {
        'name': 'dappcatalog',
        'symbol': 'DAP',
        'decimals': 18,
    },
    string_to_evm_address('0x7d3E7D41DA367b4FDCe7CBE06502B13294Deb758'): {
        'name': 'SSS',
        'symbol': 'SSS',
        'decimals': 8,
    },
    string_to_evm_address('0xc1F5ba8bab3ca299F9817876a6715627F9e2B11a'): {
        'name': 'FIFA.win',
        'symbol': 'FIFAmini',
        'decimals': 18,
    },
    string_to_evm_address('0xc2B62022A90ab4132479c94b609723CF4C56e89C'): {
        'name': 'MIGRATE REP',
        'symbol': 'MREP',
        'decimals': 18,
    },
    string_to_evm_address('0x5EaC95ad5b287cF44E058dCf694419333b796123'): {
        'name': 'AICRYPTO',
        'symbol': 'AIC',
        'decimals': 18,
    },
    string_to_evm_address('0x94d6b4fB35fB08Cb34Aa716ab40049Ec88002079'): {
        'name': 'Cryptonex (CNX) - Global Blockchain Acquiring',
        'symbol': 'CNX',
        'decimals': 8,
    },
    string_to_evm_address('0xBDDab785b306BCD9fB056Da189615Cc8eCE1D823'): {
        'name': 'Ebakus',
        'symbol': 'EBK',
        'decimals': 18,
    },
    string_to_evm_address('0xaC9Bb427953aC7FDDC562ADcA86CF42D988047Fd'): {
        'name': 'Scatter.cx',
        'symbol': 'STT',
        'decimals': 18,
    },
    string_to_evm_address('0xd037a81B22e7F814bC6f87D50e5bd67d8c329Fa2'): {
        'name': 'EMO tokens',
        'symbol': 'EMO',
        'decimals': 18,
    },
    string_to_evm_address('0xdb455c71C1bC2de4e80cA451184041Ef32054001'): {
        'name': 'Jury.Online Token',
        'symbol': 'JOT',
        'decimals': 18,
    },
    string_to_evm_address('0x9B11EFcAAA1890f6eE52C6bB7CF8153aC5d74139'): {
        'name': 'ATMChain',
        'symbol': 'ATM',
        'decimals': 8,
    },
    string_to_evm_address('0x04ad70466A79Dd1251F22Ad426248088724ff32B'): {
        'name': 'Time-Honored Brand Chain',
        'symbol': 'THBC',
        'decimals': 4,
    },
    string_to_evm_address('0x06e0feB0D74106c7adA8497754074D222Ec6BCDf'): {
        'name': 'BitBall',
        'symbol': 'BTB',
        'decimals': 18,
    },
    string_to_evm_address('0x15E4Cf1950FFA338cE5bc59456b3E579Ed1bead3'): {
        'name': 'ALFA NTOK',
        'symbol': 'aNTOK',
        'decimals': 18,
    },
    string_to_evm_address('0x22a39C2DD54b71aC884657bb3e37308ABe2D02E1'): {
        'name': 'USD',
        'symbol': 'USD',
        'decimals': 18,
    },
    string_to_evm_address('0x249f71F8D9dA86c60f485E021b509A206667A079'): {
        'name': 'Singular Japan',
        'symbol': 'SNGJ',
        'decimals': 18,
    },
    string_to_evm_address('0x322f4f6a48329690957a3BCBd1301516C2B83c1F'): {
        'name': 'MesChain',
        'symbol': 'MES',
        'decimals': 8,
    },
    string_to_evm_address('0x3A4A0D5b8dfAcd651EE28ed4fFEBf91500345489'): {
        'name': 'BerryXToken',
        'symbol': 'BRX',
        'decimals': 18,
    },
    string_to_evm_address('0x4C6112F9652463F5bdCB954ff6B650aCb64e47Cc'): {
        'name': 'DMTS',
        'symbol': 'DMTS',
        'decimals': 8,
    },
    string_to_evm_address('0x4d829f8C92a6691c56300D020c9e0dB984Cfe2BA'): {
        'name': 'CoinCrowd',
        'symbol': 'XCC',
        'decimals': 18,
    },
    string_to_evm_address('0x515669d308f887Fd83a471C7764F5d084886D34D'): {
        'name': 'MUXE Token',
        'symbol': 'MUXE',
        'decimals': 18,
    },
    string_to_evm_address('0x5245789633B5D0eBD21e393c3d7eAD22d5Ad1517'): {
        'name': 'Shaggy Coin',
        'symbol': 'SHAG',
        'decimals': 5,
    },
    string_to_evm_address('0x708B63545467a9bCFB67aF92299102c650E34a0e'): {
        'name': 'Vital  Ethereum',
        'symbol': 'VETH',
        'decimals': 18,
    },
    string_to_evm_address('0x77FE30b2cf39245267C0a5084B66a560f1cF9E1f'): {
        'name': 'Azbit',
        'symbol': 'AZ',
        'decimals': 18,
    },
    string_to_evm_address('0x7Bd7e0BbED7d672eede693445a0fb94e11D879FA'): {
        'name': 'ICO 2018 (https://safe.ad) - 1 year gift tokens',
        'symbol': 'SAFE.AD',
        'decimals': 18,
    },
    string_to_evm_address('0x8E4fbe2673e154fe9399166E03e18f87A5754420'): {
        'name': 'Universal Bonus Token | t.me/bubbletonebot',
        'symbol': 'UBT',
        'decimals': 18,
    },
    string_to_evm_address('0xeeB69Fca351cfd49a8b977b28868D7E6EdB9cD02'): {
        'name': 'ApolloSeptem',
        'symbol': 'APO',
        'decimals': 18,
    },
    string_to_evm_address('0x78774D1C3277B83459C730921bfF11019017B233'): {
        'name': 'SingularX',
        'symbol': 'SNGX',
        'decimals': 18,
    },
    string_to_evm_address('0x9eC251401eAfB7e98f37A1D911c0AEA02CB63A80'): {
        'name': 'Bitcratic',
        'symbol': 'BCT',
        'decimals': 18,
    },
    string_to_evm_address('0xAD1Cd0a72676dbb08848f5d4119a5F4B2e91E82E'): {
        'name': 'www.dfw.vc零成本大富翁最高赚8000eth',
        'symbol': 'www.dfw.vc零成本大富翁最高赚8000eth',
        'decimals': 18,
    },
    string_to_evm_address('0xAE66d00496Aaa25418f829140BB259163c06986E'): {
        'name': 'Super Wallet Token',
        'symbol': 'SW',
        'decimals': 8,
    },
    string_to_evm_address('0xB7FbE91752Dd926a5EA103f1b2E8b6FD2cEe4d91'): {
        'name': 'Global Environment Fund',
        'symbol': 'GEF',
        'decimals': 6,
    },
    string_to_evm_address('0xBa7A6156ff985a119B5a0B35B20ABeF5300A55E9'): {
        'name': 'Superblue',
        'symbol': 'SPB',
        'decimals': 18,
    },
    string_to_evm_address('0xCdc7FaA3a06733d50D4Bf86b5C7cd9460c35691E'): {
        'name': 'TOPBTC',
        'symbol': 'TOPBTC',
        'decimals': 8,
    },
    string_to_evm_address('0xDa63A8F9b33e3C927E8ce66606913bE1821f67de'): {
        'name': 'YunJiaMi.Com 免费交易 Free Exchange',
        'symbol': 'YunJiaMi.Com 免费交易 Free Exchange',
        'decimals': 18,
    },
    string_to_evm_address('0xEA5E4A7a1F29bD8357f1817ff0e873Be83f1FC7D'): {
        'name': '万国链(WGBC) ',
        'symbol': 'WGBC',
        'decimals': 18,
    },
    string_to_evm_address('0xEd6cA9522FdA3b9Cd93025780A2939bd04a7ECD6'): {
        'name': 'https://www.yidaibi.me/ 最佳一键发币解决方案 Create tokens easily',
        'symbol': 'www.yidaibi.me一键发币CreateTokens',
        'decimals': 18,
    },
    string_to_evm_address('0xF6317DD9B04097a9E7B016cd23DCAa7CfE19D9c6'): {
        'name': 'TOPBTC TOKEN',
        'symbol': 'TOPB',
        'decimals': 18,
    },
    string_to_evm_address('0xb679aFD97bCBc7448C1B327795c3eF226b39f0E9'): {
        'name': 'Win Last Mile',
        'symbol': 'WLM',
        'decimals': 6,
    },
    string_to_evm_address('0xd4AE0807740dF6FbaA7a258907132a2ac8d52Fbc'): {
        'name': 'KEOSToken',
        'symbol': 'KEOS',
        'decimals': 18,
    },
    string_to_evm_address('0xb1CD6e4153B2a390Cf00A6556b0fC1458C4A5533'): {
        'name': 'BNT Smart Token Relay',
        'symbol': 'ETHBNT',
        'decimals': 18,
    },
    string_to_evm_address('0xF6276830c265A779A2225B9d2FCbAb790CBEb92B'): {
        'name': 'XCELTOKEN',
        'symbol': 'XCEL',
        'decimals': 18,
    },
    string_to_evm_address('0xE94327D07Fc17907b4DB788E5aDf2ed424adDff6'): {
        'name': 'Reputation',
        'symbol': 'REP',
        'decimals': 18,
    },
    string_to_evm_address('0x49E033122C8300a6d5091ACf667494466eE4a9D2'): {
        'name': 'MEET.ONE',
        'symbol': 'MEET.ONE',
        'decimals': 18,
    },
    string_to_evm_address('0x86Fa049857E0209aa7D9e616F7eb3b3B78ECfdb0'): {
        'name': '',
        'symbol': 'EOS',
        'decimals': 18,
    },
    string_to_evm_address('0xA0fEbbd88651CcCa6180BEEFb88e3B4cf85Da5be'): {
        'name': 'ARCoin',
        'symbol': 'ARCoin',
        'decimals': 18,
    },
    string_to_evm_address('0xB31C219959E06f9aFBeB36b388a4BaD13E802725'): {
        'name': 'ONOT',
        'symbol': 'ONOT',
        'decimals': 18,
    },
    string_to_evm_address('0xBA5F00A28F732f23Ba946C594716496EBDC9aef5'): {
        'name': 'BKEX.COM Token',
        'symbol': 'bkex.com',
        'decimals': 18,
    },
    string_to_evm_address('0x08130635368AA28b217a4dfb68E1bF8dC525621C'): {
        'name': 'AfroDex',
        'symbol': 'AfroX',
        'decimals': 4,
    },
    string_to_evm_address('0x663085225320c7Afae10f3f1982EAA7324eA55DA'): {
        'name': 'Qualified Quality Block ',
        'symbol': 'QQB',
        'decimals': 8,
    },
    string_to_evm_address('0x0EA5Da303c9Ad00c8A2740c0cA8c44F12c7DA790'): {
        'name': 'NobelAcme',
        'symbol': 'NBAT',
        'decimals': 18,
    },
    string_to_evm_address('0x2F141Ce366a2462f02cEA3D12CF93E4DCa49e4Fd'): {
        'name': 'Free Coin',
        'symbol': 'FREE',
        'decimals': 18,
    },
    string_to_evm_address('0x12565fd1436926bEb0FFf522D63be551240a4594'): {
        'name': 'GOLD',
        'symbol': 'GOLD',
        'decimals': 18,
    },
    string_to_evm_address('0x1B5855d39E0a79a9f282478BD7191212a49B53a2'): {
        'name': 'GENES',
        'symbol': 'GENES',
        'decimals': 8,
    },
    string_to_evm_address('0x2d1E23144B89fC7364eD3efCd5Af04093F7d9a3D'): {
        'name': 'Ethereum Asset Split Token',
        'symbol': 'EAST',
        'decimals': 18,
    },
    string_to_evm_address('0x303014CE11Eed977B3Fb26fe9ca9d2Afe1dDCfF7'): {
        'name': 'Soundeon Token',
        'symbol': 'Soundeon',
        'decimals': 18,
    },
    string_to_evm_address('0x31Ea2a265020eCd892956C8E54DBdad9CAAAAA98'): {
        'name': 'Cryptics.tech Airdrop Token',
        'symbol': 'cryptics.tech',
        'decimals': 18,
    },
    string_to_evm_address('0x48c7CDADB1313076EfDac3Fdfb8427B4F58c5b7F'): {
        'name': 'DA$',
        'symbol': 'DA$',
        'decimals': 18,
    },
    string_to_evm_address('0x5783862cef49094bE4DE1fe31280B2E33cF87416'): {
        'name': 'KredX Token',
        'symbol': 'KRT',
        'decimals': 4,
    },
    string_to_evm_address('0x7D266ed871f24D7b47b5a8B80abB391178C48Bac'): {
        'name': 'StakeIt',
        'symbol': 'STAKE',
        'decimals': 8,
    },
    string_to_evm_address('0x7f6a47B85a9425c813b1cD191D730054BdF6235D'): {
        'name': 'dfw.vc8000eth+Profit',
        'symbol': 'www.dfw.vc零成本大富翁最高赚8000eth',
        'decimals': 18,
    },
    string_to_evm_address('0xB2e4B6eA88C4836d9F710484b08a9c0327e7412D'): {
        'name': 'QQ微信231799955',
        'symbol': '通缉FUS骗子陈煜维权QQ微信231799955',
        'decimals': 18,
    },
    string_to_evm_address('0xD443454DFD477e1D689F2Bb0baC578e9D8d4EF2c'): {
        'name': 'qunfaba.com免费空投',
        'symbol': 'qunfaba.com免费空投FreeBulksender',
        'decimals': 18,
    },
    string_to_evm_address('0xDB74865fF14D7045EE1723ffDa9E4B33C0DD0968'): {
        'name': 'Love Chain',
        'symbol': 'LC',
        'decimals': 18,
    },
    string_to_evm_address('0xd20bcBD56d9D551CAc10a6bC2a83635BFb72F3F4'): {
        'name': 'FUND',
        'symbol': 'FUND',
        'decimals': 6,
    },
    string_to_evm_address('0xeF1344bDf80BEf3Ff4428d8bECEC3eea4A2cF574'): {
        'name': 'Era Swap',
        'symbol': 'ES',
        'decimals': 18,
    },
    string_to_evm_address('0xf45B778E53d858c79BF4DFBDD5c1bfDB426bb891'): {
        'name': 'MFCC',
        'symbol': 'MFCC',
        'decimals': 18,
    },
    string_to_evm_address('0xf485C5E679238f9304D986bb2fC28fE3379200e5'): {
        'name': 'UG Coin',
        'symbol': 'UGC',
        'decimals': 18,
    },
    string_to_evm_address('0x754938ED5e966D5794AF6Dd3B3c2bBd43af65Ebe'): {
        'name': '(lidosr.xyz)',
        'symbol': '[lidosr.xyz] Claim your special rewards.',
        'decimals': 6,
    },
    string_to_evm_address('0x39cf57b4dECb8aE3deC0dFcA1E2eA2C320416288'): {
        'name': '$ AaveReward.com',
        'symbol': '$ AaveReward.com',
        'decimals': 18,
    },
    string_to_evm_address('0x67542502245eb5DF64eF7Ea776199CeB79401058'): {
        'name': '$ UniswapLR.com',
        'symbol': '$ UniswapLR.com @ 5.75',
        'decimals': 18,
    },
    string_to_evm_address('0x54fd62228C6e1234fd5Fded28555CA963Dcf6d26'): {
        'name': '$ NFTButerin.com',
        'symbol': 'NFTButerin.com',
        'decimals': 18,
    },
    string_to_evm_address('0xe72c7D093Ac50C57e47f4f2674243A4FfF68F0F2'): {
        'name': 'stDai.xyz',
        'symbol': 'https://stdai.xyz',
        'decimals': 18,
    },
    string_to_evm_address('0x1883A07C429E84AcA23b041c357e1d21A2B645f3'): {
        'name': 'LooksDrop.com',
        'symbol': 'LOOKSDROP.COM',
        'decimals': 18,
    },
    string_to_evm_address('0x062032F5a8FfafBde4D513237071f450C270b764'): {
        'name': 'VoteFork.com',
        'symbol': 'VOTEFORK.COM',
        'decimals': 18,
    },
    string_to_evm_address('0xF511123fdf2F13811abf4edDb493860101471729'): {
        'name': 'aave-sr.xyz',
        'symbol': 'Visit [aave-sr.xyz] and claim special rewards',
        'decimals': 6,
    },
    string_to_evm_address('0xe3C6F9D0d731C2Eb6B6D3eBFb6732fCd26a365d0'): {
        'name': 'ClaimSLP.com',
        'symbol': '[ https://ClaimSLP.com] Visit and claim rewards',
        'decimals': 18,
    },
    string_to_evm_address('0x0bF377fb3b5F1dD601e693B8fAF6b0bD249f37D3'): {
        'name': '(apum.xyz)',
        'symbol': 'Invitation token. Please Visit https://apum.xyz and claim rewards.',
        'decimals': 18,
    },
    string_to_evm_address('0xb0B1d4732eFE32AEA466ED6BC3c79181eD4810c4'): {
        'name': 'ApeCoinV2.com',
        'symbol': 'ApeCoinV2.com',
        'decimals': 18,
    },
    string_to_evm_address('0x2F87445C3c81a5b268adAB1915235a94aA27bF54'): {
        'name': 'as-uni.org',
        'symbol': '[https://as-uni.org] Visit and claim rewards',
        'decimals': 18,
    },
    string_to_evm_address('0xFBcf72e38325a9fA14d4d4D6eC3a7471A312fcEe'): {
        'name': '$',
        'symbol': 'LPLido.com',
        'decimals': 18,
    },
    string_to_evm_address('0x1f068a896560632a4d2E05044BD7F03834f1A465'): {
        'name': 'EthFork2.com',
        'symbol': 'EthFork2.com',
        'decimals': 18,
    },
    string_to_evm_address('0x70c18F2fDcb00d27494f767503874788e35c9940'): {
        'name': 'lenusd.shop',
        'symbol': 'Claim at [lenusd.shop]',
        'decimals': 6,
    },
    string_to_evm_address('0xc9dA518dB3AbdB90A82c4d1838B7Cf9b0C945E7e'): {
        'name': '(apord.site)',
        'symbol': 'This token holders can claim reward token. Please Visit https://apord.site and claim rewards.',  # noqa: E501
        'decimals': 18,
    },
    string_to_evm_address('0xCdC94877E4164D2e915fC5E8310155D661A995F1'): {
        'name': 'spingame.me',
        'symbol': 'Enjoy [https://spingame.me]',
        'decimals': 6,
    },
    string_to_evm_address('0x38715Ab4b9d4e00890773D7338d94778b0dFc0a8'): {
        'name': 'ausd.shop',
        'symbol': 'Visit [ausd.shop] and supply or borrow USDT',
        'decimals': 6,
    },
}


def query_token_spam_list(db: 'DBHandler', make_remote_query: bool) -> Set[EvmToken]:
    """Generate a set of assets that can be ignored combining information of cryptoscamdb
    and the list of spam assets KNOWN_ETH_SPAM_TOKENS. This function also makes sure to get the
    bad assets in the list of cryptoscamdb and ensures that they exists in the globaldb before
    trying to add them.

    If `make_remote_query` is False then only the KNOWN_ETH_SPAM_TOKENS are added as
    ignored assets.

    TODO
    This function tries to add as assets to the globaldb the tokens listed in
    KNOWN_ETH_SPAM_TOKENS and not the ones coming from cryptoscamdb. The reason is that until the
    v2 of the API the response contains both spam addresses and tokens and there is no way to know
    if the address is for a contract or not. Checking if the address is a contract takes too much
    time. When V2 gets released this can be fixed.
    May raise:
    - RemoteError
    """
    tokens_to_ignore = set()
    if make_remote_query is True:
        try:
            response = requests.get(
                url='https://api.cryptoscamdb.org/v1/addresses',
                timeout=DEFAULT_TIMEOUT_TUPLE,
            )
            data = response.json()
            success, tokens_info = data['success'], data['result']
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to retrieve information from cryptoscamdb. {str(e)}') from e
        except (DeserializationError, JSONDecodeError) as e:
            raise RemoteError(f'Failed to deserialize data from cryptoscamdb. {str(e)}') from e
        except KeyError as e:
            raise RemoteError(
                f'Response from cryptoscamdb doesn\'t contain expected key. {str(e)}',
            ) from e

        if success is False:
            log.error(f'Failed to deserialize data from cryptoscamdb. {data}')
            raise RemoteError(
                'Failed to deserialize data from cryptoscamdb. Check the logs '
                'to get more information',
            )

        for token_addr, token_data in tokens_info.items():
            if not token_addr.startswith('0x') or token_data[0]['type'] != 'scam':
                continue
            try:
                checksumed_address = to_checksum_address(token_addr)
            except ValueError as e:
                log.debug(f'Failed to read address from cryptoscamdb. {str(e)}')
                continue
            try:
                token = EvmToken(ethaddress_to_identifier(checksumed_address))
            except UnknownAsset:
                continue
            if token is not None:
                tokens_to_ignore.add(token)

    # Try to add custom list
    for token_address, info in KNOWN_ETH_SPAM_TOKENS.items():
        try:
            own_token = get_or_create_evm_token(
                userdb=db,
                evm_address=token_address,
                chain=ChainID.ETHEREUM,
                protocol=SPAM_PROTOCOL,
                form_with_incomplete_data=True,
                decimals=info.get('decimals', 18),
                name=info.get('name', MISSING_NAME_SPAM_TOKEN),
                symbol=info.get('symbol', MISSING_SYMBOL_SPAM_TOKEN),
            )
        except (RemoteError, NotERC20Conformant) as e:
            log.debug(f'Skipping {checksumed_address} due to {str(e)}')
            continue
        if own_token is not None:
            tokens_to_ignore.add(own_token)

    return tokens_to_ignore


def update_spam_assets(write_cursor: 'DBCursor', db: 'DBHandler', make_remote_query: bool) -> int:
    """
    Update the list of ignored assets using query_token_spam_list and avoiding
    the addition of duplicates. It returns the amount of assets that were added
    to the ignore list
    """
    spam_tokens = query_token_spam_list(db=db, make_remote_query=make_remote_query)
    # order matters here. Make sure ignored_assets are queried after spam tokens creation
    # since it's possible for a token to exist in ignored assets but not global DB.
    # and in that case query_token_spam_list add it to the global DB
    with db.conn.read_ctx() as cursor:
        ignored_assets = {asset.identifier for asset in db.get_ignored_assets(cursor)}
    assets_added = 0
    for token in spam_tokens:
        if token.identifier in ignored_assets:
            continue

        db.add_to_ignored_assets(write_cursor=write_cursor, asset=token)
        assets_added += 1
    return assets_added
