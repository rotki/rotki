# This python file was generated automatically by
# /Users/eniola/work/rotki/tools/scripts/generate_constant_assets.py at 15/09/2022 09:51:02.
# Do not edit manually!

from typing import List, Union

from rotkehlchen.assets.asset import AssetWithSymbol, CryptoAsset, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.types import ChainID, EvmTokenKind, Timestamp

CONSTANT_ASSETS: List[Union[AssetWithSymbol, CryptoAsset, EvmToken]] = []

A_USD = AssetWithSymbol.initialize(
    identifier='USD',
    asset_type=AssetType.FIAT,
    name="United States Dollar",
    symbol='USD',
)
CONSTANT_ASSETS.append(A_USD)
A_EUR = AssetWithSymbol.initialize(
    identifier='EUR',
    asset_type=AssetType.FIAT,
    name="Euro",
    symbol='EUR',
)
CONSTANT_ASSETS.append(A_EUR)
A_BTC = CryptoAsset.initialize(
    identifier='BTC',
    asset_type=AssetType.OWN_CHAIN,
    name="Bitcoin",
    symbol='BTC',
    started=Timestamp(1231006505),
    forked=None,
    swapped_for=None,
    coingecko='bitcoin',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_BTC)
A_BCH = CryptoAsset.initialize(
    identifier='BCH',
    asset_type=AssetType.OWN_CHAIN,
    name="Bitcoin Cash",
    symbol='BCH',
    started=Timestamp(1501593374),
    forked=A_BTC,
    swapped_for=None,
    coingecko='bitcoin-cash',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_BCH)
A_BSV = CryptoAsset.initialize(
    identifier='BSV',
    asset_type=AssetType.OWN_CHAIN,
    name="Bitcoin Satoshi's Vision",
    symbol='BSV',
    started=Timestamp(1542300000),
    forked=A_BCH,
    swapped_for=None,
    coingecko='bitcoin-cash-sv',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_BSV)
A_ETH = CryptoAsset.initialize(
    identifier='ETH',
    asset_type=AssetType.OWN_CHAIN,
    name="Ethereum",
    symbol='ETH',
    started=Timestamp(1438214400),
    forked=None,
    swapped_for=None,
    coingecko='ethereum',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_ETH)
A_ETH2 = CryptoAsset.initialize(
    identifier='ETH2',
    asset_type=AssetType.OWN_CHAIN,
    name="Staked ETH in Phase 0",
    symbol='ETH',
    started=Timestamp(1602667372),
    forked=None,
    swapped_for=None,
    coingecko='ethereum',
    cryptocompare='ETH',
)
CONSTANT_ASSETS.append(A_ETH2)
A_ETC = CryptoAsset.initialize(
    identifier='ETC',
    asset_type=AssetType.OWN_CHAIN,
    name="Ethereum classic",
    symbol='ETC',
    started=Timestamp(1469020840),
    forked=A_ETH,
    swapped_for=None,
    coingecko='ethereum-classic',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_ETC)
A_KSM = CryptoAsset.initialize(
    identifier='KSM',
    asset_type=AssetType.OWN_CHAIN,
    name="Kusama",
    symbol='KSM',
    started=Timestamp(1576142353),
    forked=None,
    swapped_for=None,
    coingecko='kusama',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_KSM)
A_AVAX = CryptoAsset.initialize(
    identifier='AVAX',
    asset_type=AssetType.OWN_CHAIN,
    name="Avalanche",
    symbol='AVAX',
    started=Timestamp(1600646400),
    forked=None,
    swapped_for=None,
    coingecko='avalanche-2',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_AVAX)
A_DOGE = CryptoAsset.initialize(
    identifier='DOGE',
    asset_type=AssetType.OWN_CHAIN,
    name="Dogecoin",
    symbol='DOGE',
    started=Timestamp(1386325540),
    forked=None,
    swapped_for=None,
    coingecko='dogecoin',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_DOGE)
A_BSQ = CryptoAsset.initialize(
    identifier='BSQ',
    asset_type=AssetType.OTHER,
    name="Bisq DAO Token",
    symbol='BSQ',
    started=Timestamp(1555286400),
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_BSQ)
A_KFEE = CryptoAsset.initialize(
    identifier='KFEE',
    asset_type=AssetType.OWN_CHAIN,
    name="Kraken fees",
    symbol='KFEE',
    started=Timestamp(1377993600),
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_KFEE)
A_SOL = CryptoAsset.initialize(
    identifier='SOL-2',
    asset_type=AssetType.OWN_CHAIN,
    name="Solana",
    symbol='SOL',
    started=Timestamp(1586494758),
    forked=None,
    swapped_for=None,
    coingecko='solana',
    cryptocompare='SOL',
)
CONSTANT_ASSETS.append(A_SOL)


A_BAL = EvmToken.initialize(
    address=string_to_evm_address('0xba100000625a3754423978a60c9317c58a424e3D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Balancer",
    symbol='BAL',
    started=Timestamp(1592616779),
    swapped_for=None,
    coingecko='balancer',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BAL)
A_BAT = EvmToken.initialize(
    address=string_to_evm_address('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Basic Attention Token",
    symbol='BAT',
    started=Timestamp(1496294094),
    swapped_for=None,
    coingecko='basic-attention-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BAT)
A_UNI = EvmToken.initialize(
    address=string_to_evm_address('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Uniswap",
    symbol='UNI',
    started=Timestamp(1600107086),
    swapped_for=None,
    coingecko='uniswap',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_UNI)
A_1INCH = EvmToken.initialize(
    address=string_to_evm_address('0x111111111117dC0aa78b770fA6A738034120C302'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="1INCH Token",
    symbol='1INCH',
    started=Timestamp(1608747211),
    swapped_for=None,
    coingecko='1inch',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_1INCH)
A_DAI = EvmToken.initialize(
    address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Multi Collateral Dai",
    symbol='DAI',
    started=Timestamp(1573672677),
    swapped_for=None,
    coingecko='dai',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DAI)
A_SAI = EvmToken.initialize(
    address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Single Collateral Dai",
    symbol='SAI',
    started=Timestamp(1513586475),
    swapped_for=None,
    coingecko='sai',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SAI)
A_YFI = EvmToken.initialize(
    address=string_to_evm_address('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn.finance",
    symbol='YFI',
    started=Timestamp(1594972885),
    swapped_for=None,
    coingecko='yearn-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YFI)
A_USDT = EvmToken.initialize(
    address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="Tether",
    symbol='USDT',
    started=Timestamp(1402358400),
    swapped_for=None,
    coingecko='tether',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_USDT)
A_USDC = EvmToken.initialize(
    address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="USD Coin",
    symbol='USDC',
    started=Timestamp(1533324504),
    swapped_for=None,
    coingecko='usd-coin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_USDC)
A_TUSD = EvmToken.initialize(
    address=string_to_evm_address('0x0000000000085d4780B73119b644AE5ecd22b376'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="TrueUSD",
    symbol='TUSD',
    started=Timestamp(1520310861),
    swapped_for=None,
    coingecko='true-usd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TUSD)
A_MATIC = EvmToken.initialize(
    address=string_to_evm_address('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Matic Network",
    symbol='MATIC',
    started=Timestamp(1555718400),
    swapped_for=None,
    coingecko='matic-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MATIC)
A_LQTY = EvmToken.initialize(
    address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="LQTY",
    symbol='LQTY',
    started=Timestamp(1617611590),
    swapped_for=None,
    coingecko='liquity',
    cryptocompare='LQTY',
    protocol=None,
)
CONSTANT_ASSETS.append(A_LQTY)
A_PICKLE = EvmToken.initialize(
    address=string_to_evm_address('0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PickleToken",
    symbol='PICKLE',
    started=Timestamp(1599694316),
    swapped_for=None,
    coingecko='pickle-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PICKLE)
A_BEST = EvmToken.initialize(
    address=string_to_evm_address('0x1B073382E63411E3BcfFE90aC1B9A43feFa1Ec6F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Bitpanda Ecosystem Token",
    symbol='BEST',
    started=Timestamp(1564487711),
    swapped_for=None,
    coingecko='bitpanda-ecosystem-token',
    cryptocompare='BEST',
    protocol=None,
)
CONSTANT_ASSETS.append(A_BEST)
A_GTC = EvmToken.initialize(
    address=string_to_evm_address('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Gitcoin",
    symbol='GTC',
    started=Timestamp(1620856082),
    swapped_for=None,
    coingecko='gitcoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GTC)

A_AAVE = EvmToken.initialize(
    address=string_to_evm_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Aave Token",
    symbol='AAVE',
    started=Timestamp(1600970788),
    swapped_for=None,
    coingecko='aave',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_AAVE)
A_GUSD = EvmToken.initialize(
    address=string_to_evm_address('0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=2,
    name="Gemini Dollar",
    symbol='GUSD',
    started=Timestamp(1536521774),
    swapped_for=None,
    coingecko='gemini-dollar',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GUSD)
A_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve DAO Token",
    symbol='CRV',
    started=Timestamp(1597270648),
    swapped_for=None,
    coingecko='curve-dao-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV)
A_KNC = EvmToken.initialize(
    address=string_to_evm_address('0xdd974D5C2e2928deA5F71b9825b8b646686BD200'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Kyber Network",
    symbol='KNC',
    started=Timestamp(1501545600),
    swapped_for=None,
    coingecko='kyber-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_KNC)
A_WBTC = EvmToken.initialize(
    address=string_to_evm_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Wrapped Bitcoin",
    symbol='WBTC',
    started=Timestamp(1543095952),
    swapped_for=None,
    coingecko='wrapped-bitcoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_WBTC)
A_WETH = EvmToken.initialize(
    address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="WETH",
    symbol='WETH',
    started=Timestamp(1513077455),
    swapped_for=None,
    coingecko='weth',
    cryptocompare='ETH',
    protocol=None,
)
CONSTANT_ASSETS.append(A_WETH)
A_ZRX = EvmToken.initialize(
    address=string_to_evm_address('0xE41d2489571d322189246DaFA5ebDe1F4699F498'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="0x",
    symbol='ZRX',
    started=Timestamp(1502476756),
    swapped_for=None,
    coingecko='0x',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ZRX)
A_MANA = EvmToken.initialize(
    address=string_to_evm_address('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Decentraland",
    symbol='MANA',
    started=Timestamp(1502824689),
    swapped_for=None,
    coingecko='decentraland',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MANA)
A_PAX = EvmToken.initialize(
    address=string_to_evm_address('0x8E870D67F660D95d5be530380D0eC0bd388289E1'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Paxos Standard Token",
    symbol='PAX',
    started=Timestamp(1536537600),
    swapped_for=None,
    coingecko='paxos-standard',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PAX)
A_COMP = EvmToken.initialize(
    address=string_to_evm_address('0xc00e94Cb662C3520282E6f5717214004A7f26888'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Compound",
    symbol='COMP',
    started=Timestamp(1583323735),
    swapped_for=None,
    coingecko='compound-governance-token',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_COMP)
A_LRC = EvmToken.initialize(
    address=string_to_evm_address('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="LoopringCoin V2",
    symbol='LRC',
    started=Timestamp(1500422400),
    swapped_for=None,
    coingecko='loopring',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_LRC)
A_LINK = EvmToken.initialize(
    address=string_to_evm_address('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Chainlink",
    symbol='LINK',
    started=Timestamp(1505520000),
    swapped_for=None,
    coingecko='chainlink',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_LINK)
A_ADX = EvmToken.initialize(
    address=string_to_evm_address('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="AdEx Network",
    symbol='ADX',
    started=Timestamp(1496102400),
    swapped_for=None,
    coingecko='adex',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ADX)
A_TORN = EvmToken.initialize(
    address=string_to_evm_address('0x77777FeDdddFfC19Ff86DB637967013e6C6A116C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="TornadoCash",
    symbol='TORN',
    started=Timestamp(1608260437),
    swapped_for=None,
    coingecko='tornado-cash',
    cryptocompare='TORN',
    protocol=None,
)
CONSTANT_ASSETS.append(A_TORN)
A_CORN = EvmToken.initialize(
    address=string_to_evm_address('0xa456b515303B2Ce344E9d2601f91270f8c2Fea5E'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Cornichon",
    symbol='CORN',
    started=Timestamp(1606603741),
    swapped_for=None,
    coingecko='cornichon',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CORN)
A_GRAIN = EvmToken.initialize(
    address=string_to_evm_address('0x6589fe1271A0F29346796C6bAf0cdF619e25e58e'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="GRAIN Token",
    symbol='GRAIN',
    started=Timestamp(1606500872),
    swapped_for=None,
    coingecko='grain-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GRAIN)
A_COMBO = EvmToken.initialize(
    address=string_to_evm_address('0xfFffFffF2ba8F66D4e51811C5190992176930278'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Furucombo",
    symbol='COMBO',
    started=Timestamp(1609231627),
    swapped_for=None,
    coingecko='furucombo',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_COMBO)
A_LDO = EvmToken.initialize(
    address=string_to_evm_address('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Lido DAO Token",
    symbol='LDO',
    started=Timestamp(1608242396),
    swapped_for=None,
    coingecko='lido-dao',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_LDO)
A_RENBTC = EvmToken.initialize(
    address=string_to_evm_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="renBTC",
    symbol='renBTC',
    started=Timestamp(1585090944),
    swapped_for=None,
    coingecko='renbtc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_RENBTC)
A_BNB = EvmToken.initialize(
    address=string_to_evm_address('0xB8c77482e45F1F44dE1745F52C74426C631bDD52'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Binance Coin",
    symbol='BNB',
    started=Timestamp(1498521600),
    swapped_for=None,
    coingecko='binancecoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BNB)
A_REP = EvmToken.initialize(
    address=string_to_evm_address('0x221657776846890989a759BA2973e427DfF5C9bB'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Augur",
    symbol='REPv2',
    started=Timestamp(1595886655),
    swapped_for=None,
    coingecko='augur',
    cryptocompare='REP',
    protocol=None,
)
CONSTANT_ASSETS.append(A_REP)
A_BZRX = EvmToken.initialize(
    address=string_to_evm_address('0x56d811088235F11C8920698a204A5010a788f4b3'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="bZx Protocol",
    symbol='BZRX',
    started=Timestamp(1594509320),
    swapped_for=None,
    coingecko='bzx-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BZRX)
A_STAKE = EvmToken.initialize(
    address=string_to_evm_address('0x0Ae055097C6d159879521C384F1D2123D1f195e6'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="xDAI STAKE",
    symbol='STAKE',
    started=Timestamp(1586959457),
    swapped_for=None,
    coingecko='xdai-stake',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_STAKE)
A_DPI = EvmToken.initialize(
    address=string_to_evm_address('0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="DefiPulse Index",
    symbol='DPI',
    started=Timestamp(1599694252),
    swapped_for=None,
    coingecko='defipulse-index',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DPI)
A_YFII = EvmToken.initialize(
    address=string_to_evm_address('0xa1d0E215a23d7030842FC67cE582a6aFa3CCaB83'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="YFII.finance",
    symbol='YFII',
    started=Timestamp(1595768700),
    swapped_for=None,
    coingecko='yfii-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YFII)
A_MCB = EvmToken.initialize(
    address=string_to_evm_address('0x4e352cF164E64ADCBad318C3a1e222E9EBa4Ce42'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="MCDEX Token",
    symbol='MCB',
    started=Timestamp(1593849744),
    swapped_for=None,
    coingecko='mcdex',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MCB)
A_LUSD = EvmToken.initialize(
    address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="LUSD Stablecoin",
    symbol='LUSD',
    started=Timestamp(1617611299),
    swapped_for=None,
    coingecko='liquity-usd',
    cryptocompare='LUSD',
    protocol=None,
)
CONSTANT_ASSETS.append(A_LUSD)

# used as underlying assets of aave v1 tokens
A_ENJ = EvmToken.initialize(
    address=string_to_evm_address('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Enjin Coin",
    symbol='ENJ',
    started=Timestamp(1500854400),
    swapped_for=None,
    coingecko='enjincoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ENJ)
A_SUSD = EvmToken.initialize(
    address=string_to_evm_address('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Synth sUSD",
    symbol='sUSD',
    started=Timestamp(1569466541),
    swapped_for=None,
    coingecko='nusd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SUSD)
A_BUSD = EvmToken.initialize(
    address=string_to_evm_address('0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Binance USD",
    symbol='BUSD',
    started=Timestamp(1567641600),
    swapped_for=None,
    coingecko='binance-usd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BUSD)
A_LEND = EvmToken.initialize(
    address=string_to_evm_address('0x80fB784B7eD66730e8b1DBd9820aFD29931aab03'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="ETHLend",
    symbol='LEND',
    started=Timestamp(1502755200),
    swapped_for=A_AAVE,
    coingecko='ethlend',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_LEND)
A_MKR = EvmToken.initialize(
    address=string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Maker",
    symbol='MKR',
    started=Timestamp(1439596800),
    swapped_for=None,
    coingecko='maker',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MKR)
A_REN = EvmToken.initialize(
    address=string_to_evm_address('0x408e41876cCCDC0F92210600ef50372656052a38'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Republic",
    symbol='REN',
    started=Timestamp(1514678400),
    swapped_for=None,
    coingecko='republic-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_REN)
A_SNX = EvmToken.initialize(
    address=string_to_evm_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Synthetix Network Token",
    symbol='SNX',
    started=Timestamp(1515283200),
    swapped_for=None,
    coingecko='havven',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SNX)

# atokens TODO: These can be handled programatically if enough info is in the assets DB
# protocol and underlying asset

A_ALINK_V1 = EvmToken.initialize(
    address=string_to_evm_address('0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Aave Interest bearing LINK",
    symbol='aLINK',
    started=Timestamp(1578501727),
    swapped_for=None,
    coingecko='aave-link',
    cryptocompare='LINK',
    protocol='aave',
)
CONSTANT_ASSETS.append(A_ALINK_V1)
A_AETH_V1 = EvmToken.initialize(
    address=string_to_evm_address('0x3a3A65aAb0dd2A17E3F1947bA16138cd37d08c04'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Aave Interest bearing ETH",
    symbol='aETH',
    started=Timestamp(1578501678),
    swapped_for=None,
    coingecko='aave-eth-v1',
    cryptocompare='ETH',
    protocol='aave',
)
CONSTANT_ASSETS.append(A_AETH_V1)
A_AUSDC_V1 = EvmToken.initialize(
    address=string_to_evm_address('0x9bA00D6856a4eDF4665BcA2C2309936572473B7E'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="Aave Interest bearing USDC",
    symbol='aUSDC',
    started=Timestamp(1578501407),
    swapped_for=None,
    coingecko='aave-usdc',
    cryptocompare='USDC',
    protocol='aave',
)
CONSTANT_ASSETS.append(A_AUSDC_V1)
A_AREP_V1 = EvmToken.initialize(
    address=string_to_evm_address('0x71010A9D003445aC60C4e6A7017c1E89A477B438'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Aave Interest bearing REP",
    symbol='aREP',
    started=Timestamp(1578501835),
    swapped_for=None,
    coingecko='aave-rep',
    cryptocompare='REP',
    protocol='aave',
)
CONSTANT_ASSETS.append(A_AREP_V1)

# compound tokens -- TODO: Can also be handled programmatically
A_CDAI = EvmToken.initialize(
    address=string_to_evm_address('0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound DAI",
    symbol='cDAI',
    started=Timestamp(1574471013),
    swapped_for=None,
    coingecko='cdai',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CDAI)
A_CUSDC = EvmToken.initialize(
    address=string_to_evm_address('0x39AA39c021dfbaE8faC545936693aC917d5E7563'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound USD Coin",
    symbol='cUSDC',
    started=Timestamp(1557192331),
    swapped_for=None,
    coingecko='compound-usd-coin',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CUSDC)
A_CUSDT = EvmToken.initialize(
    address=string_to_evm_address('0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound USDT",
    symbol='cUSDT',
    started=Timestamp(1586985186),
    swapped_for=None,
    coingecko='compound-usdt',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CUSDT)
A_CBAT = EvmToken.initialize(
    address=string_to_evm_address('0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound BAT",
    symbol='cBAT',
    started=Timestamp(1557192085),
    swapped_for=None,
    coingecko='compound-basic-attention-token',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CBAT)
A_CETH = EvmToken.initialize(
    address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound ETH",
    symbol='cETH',
    started=Timestamp(1557192318),
    swapped_for=None,
    coingecko='compound-ether',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CETH)
A_CREP = EvmToken.initialize(
    address=string_to_evm_address('0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound Augur",
    symbol='cREP',
    started=Timestamp(1557192288),
    swapped_for=None,
    coingecko='compound-augur',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CREP)
A_CWBTC = EvmToken.initialize(
    address=string_to_evm_address('0xC11b1268C1A384e55C48c2391d8d480264A3A7F4'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound Wrapped BTC",
    symbol='cWBTC',
    started=Timestamp(1563263257),
    swapped_for=None,
    coingecko='compound-wrapped-btc',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CWBTC)
A_CZRX = EvmToken.initialize(
    address=string_to_evm_address('0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="Compound 0x",
    symbol='cZRX',
    started=Timestamp(1557192054),
    swapped_for=None,
    coingecko='compound-0x',
    cryptocompare=None,
    protocol='compound',
)
CONSTANT_ASSETS.append(A_CZRX)


# Special tokens for defi price inquiry -- these should end up in programmatic rules
# after being upgraded to include, protocol (to identify the program to run on them)
# and underlying assets
A_3CRV = EvmToken.initialize(
    address=string_to_evm_address('0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi aDAI/aUSDC/aUSDT",
    symbol='a3CRV',
    started=Timestamp(1608558126),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_3CRV)
A_YV1_DAIUSDCTBUSD = EvmToken.initialize(
    address=string_to_evm_address('0x2994529C0652D127b7842094103715ec5299bBed'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi yDAI/yUSDC/yUSDT/yBUSD",
    symbol='yyDAI+yUSDC+yUSDT+yBUSD',
    started=Timestamp(1598095312),
    swapped_for=None,
    coingecko='lp-bcurve',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_DAIUSDCTBUSD)
A_CRVP_DAIUSDCTBUSD = EvmToken.initialize(
    address=string_to_evm_address('0x3B3Ac5386837Dc563660FB6a0937DFAa5924333B'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi yDAI/yUSDC/yUSDT/yBUSD",
    symbol='yDAI+yUSDC+yUSDT+yBUSD',
    started=Timestamp(1582828578),
    swapped_for=None,
    coingecko='lp-bcurve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRVP_DAIUSDCTBUSD)
A_YV1_DAIUSDCTTUSD = EvmToken.initialize(
    address=string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi yDAI/yUSDC/yUSDT/yTUSD",
    symbol='yyDAI+yUSDC+yUSDT+yTUSD',
    started=Timestamp(1596091760),
    swapped_for=None,
    coingecko='yvault-lp-ycurve',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_DAIUSDCTTUSD)
A_CRVP_DAIUSDCTTUSD = EvmToken.initialize(
    address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi yDAI/yUSDC/yUSDT/yTUSD",
    symbol='yDAI+yUSDC+yUSDT+yTUSD',
    started=Timestamp(1581620573),
    swapped_for=None,
    coingecko='curve-fi-ydai-yusdc-yusdt-ytusd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRVP_DAIUSDCTTUSD)
A_CRVP_RENWSBTC = EvmToken.initialize(
    address=string_to_evm_address('0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi renBTC/wBTC/sBTC",
    symbol='crvRenWSBTC',
    started=Timestamp(1592306956),
    swapped_for=None,
    coingecko='lp-renbtc-curve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRVP_RENWSBTC)
A_YV1_RENWSBTC = EvmToken.initialize(
    address=string_to_evm_address('0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi renBTC/wBTC/sBTC",
    symbol='ycrvRenWSBTC',
    started=Timestamp(1598421792),
    swapped_for=None,
    coingecko='lp-renbtc-curve',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_RENWSBTC)
A_CRV_RENWBTC = EvmToken.initialize(
    address=string_to_evm_address('0x49849C98ae39Fff122806C06791Fa73784FB3675'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi renBTC/wBTC",
    symbol='crvRenWBTC',
    started=Timestamp(1590630368),
    swapped_for=None,
    coingecko='lp-renbtc-curve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV_RENWBTC)
A_CRV_YPAX = EvmToken.initialize(
    address=string_to_evm_address('0xD905e2eaeBe188fc92179b6350807D8bd91Db0D8'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi DAI/USDC/USDT/PAX",
    symbol='ypaxCrv',
    started=Timestamp(1589148107),
    swapped_for=None,
    coingecko='lp-paxcurve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV_YPAX)
A_CRV_GUSD = EvmToken.initialize(
    address=string_to_evm_address('0xD2967f45c4f384DEEa880F807Be904762a3DeA07'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi GUSD/3Crv",
    symbol='gusd3CRV',
    started=Timestamp(1602032874),
    swapped_for=None,
    coingecko='curve-dao-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV_GUSD)
A_CRV_3CRV = EvmToken.initialize(
    address=string_to_evm_address('0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi DAI/USDC/USDT",
    symbol='3Crv',
    started=Timestamp(1599414946),
    swapped_for=None,
    coingecko='curve-dao-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV_3CRV)
A_YV1_3CRV = EvmToken.initialize(
    address=string_to_evm_address('0x9cA85572E6A3EbF24dEDd195623F188735A5179f'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi DAI/USDC/USDT",
    symbol='y3Crv',
    started=Timestamp(1602322413),
    swapped_for=None,
    coingecko='curve-dao-token',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_3CRV)
A_CRV_3CRVSUSD = EvmToken.initialize(
    address=string_to_evm_address('0xC25a3A3b969415c80451098fa907EC722572917F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi DAI/USDC/USDT/sUSD",
    symbol='crvPlain3andSUSD',
    started=Timestamp(1587348347),
    swapped_for=None,
    coingecko='lp-scurve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CRV_3CRVSUSD)
A_YV1_ALINK = EvmToken.initialize(
    address=string_to_evm_address('0x29E240CFD7946BA20895a7a02eDb25C210f9f324'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Aave Interest bearing LINK",
    symbol='yaLINK',
    started=Timestamp(1596628700),
    swapped_for=None,
    coingecko='aave-link',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_ALINK)
A_YV1_DAI = EvmToken.initialize(
    address=string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Dai Stablecoin",
    symbol='yDAI',
    started=Timestamp(1597301808),
    swapped_for=None,
    coingecko='dai',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_DAI)
A_YV1_WETH = EvmToken.initialize(
    address=string_to_evm_address('0xe1237aA7f535b0CC33Fd973D66cBf830354D16c7'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Wrapped Ether",
    symbol='yWETH',
    started=Timestamp(1598952738),
    swapped_for=None,
    coingecko='weth',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_WETH)
A_YV1_YFI = EvmToken.initialize(
    address=string_to_evm_address('0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn yearn.finance",
    symbol='yYFI',
    started=Timestamp(1597845648),
    swapped_for=None,
    coingecko='yearn-finance',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_YFI)
A_YV1_USDT = EvmToken.initialize(
    address=string_to_evm_address('0x2f08119C6f07c006695E079AAFc638b8789FAf18'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="yearn Tether USD",
    symbol='yUSDT',
    started=Timestamp(1597318993),
    swapped_for=None,
    coingecko='tether',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_USDT)
A_YV1_USDC = EvmToken.initialize(
    address=string_to_evm_address('0x597aD1e0c13Bfe8025993D9e79C69E1c0233522e'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="yearn USD//C",
    symbol='yUSDC',
    started=Timestamp(1595721600),
    swapped_for=None,
    coingecko='usd-coin',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_USDC)
A_YV1_TUSD = EvmToken.initialize(
    address=string_to_evm_address('0x37d19d1c4E1fa9DC47bD1eA12f742a0887eDa74a'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn TrueUSD",
    symbol='yTUSD',
    started=Timestamp(1596678980),
    swapped_for=None,
    coingecko='true-usd',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_TUSD)
A_YV1_GUSD = EvmToken.initialize(
    address=string_to_evm_address('0xec0d8D3ED5477106c6D4ea27D90a60e594693C90'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=2,
    name="yearn Gemini dollar",
    symbol='yGUSD',
    started=Timestamp(1602827638),
    swapped_for=None,
    coingecko='gemini-dollar',
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_GUSD)
A_PSLP = EvmToken.initialize(
    address=string_to_evm_address('0x5Eff6d166D66BacBC1BF52E2C54dD391AE6b1f48'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="pickling SushiSwap LP Token",
    symbol='pSLP',
    started=Timestamp(1612639016),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='pickle_jar',
)
CONSTANT_ASSETS.append(A_PSLP)
CRV_CDAI_CUSDC = EvmToken.initialize(
    address=string_to_evm_address('0x845838DF265Dcd2c412A1Dc9e959c7d08537f8a2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi cDAI/cUSDC",
    symbol='cDAI+cUSDC',
    started=Timestamp(1582652731),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_CDAI_CUSDC)
CRV_MUSD = EvmToken.initialize(
    address=string_to_evm_address('0x1AEf73d49Dedc4b1778d0706583995958Dc862e6'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi MUSD/3Crv",
    symbol='musd3CRV',
    started=Timestamp(1602118991),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_MUSD)
CRV_EURS = EvmToken.initialize(
    address=string_to_evm_address('0x194eBd173F6cDacE046C53eACcE9B953F28411d1'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi EURS/sEUR",
    symbol='eursCRV',
    started=Timestamp(1608157510),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_EURS)
A_MUSD = EvmToken.initialize(
    address=string_to_evm_address('0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="mStable USD",
    symbol='mUSD',
    started=Timestamp(1590585470),
    swapped_for=None,
    coingecko='musd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MUSD)
CRV_USDN = EvmToken.initialize(
    address=string_to_evm_address('0x4f3E8F405CF5aFC05D68142F3783bDfE13811522'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi USDN/3Crv",
    symbol='usdn3CRV',
    started=Timestamp(1602099637),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_USDN)
CRV_UST = EvmToken.initialize(
    address=string_to_evm_address('0x94e131324b6054c0D789b190b2dAC504e4361b53'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi UST/3Crv",
    symbol='ust3CRV',
    started=Timestamp(1608153341),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_UST)
CRV_BBTC_SBTC = EvmToken.initialize(
    address=string_to_evm_address('0x410e3E86ef427e30B9235497143881f717d93c2A'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi bBTC/sbtcCRV",
    symbol='bBTC/sbtcCRV',
    started=Timestamp(1608000599),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_BBTC_SBTC)
CRV_TBTC_SBTC = EvmToken.initialize(
    address=string_to_evm_address('0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi tBTC/sbtcCrv",
    symbol='tbtc/sbtcCrv',
    started=Timestamp(1603235147),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_TBTC_SBTC)
CRV_OBTC_SBTC = EvmToken.initialize(
    address=string_to_evm_address('0x2fE94ea3d5d4a175184081439753DE15AeF9d614'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi oBTC/sbtcCRV",
    symbol='oBTC/sbtcCRV',
    started=Timestamp(1608056620),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_OBTC_SBTC)
CRV_HBTC = EvmToken.initialize(
    address=string_to_evm_address('0xb19059ebb43466C323583928285a49f558E572Fd'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi hBTC/wBTC",
    symbol='hCRV',
    started=Timestamp(1598394687),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_HBTC)
CRV_HUSD = EvmToken.initialize(
    address=string_to_evm_address('0x5B5CFE992AdAC0C9D48E05854B2d91C73a003858'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi HUSD/3Crv",
    symbol='husd3CRV',
    started=Timestamp(1602093636),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_HUSD)
CRV_DUSD = EvmToken.initialize(
    address=string_to_evm_address('0x3a664Ab939FD8482048609f652f9a0B0677337B9'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi DUSD/3Crv",
    symbol='dusd3CRV',
    started=Timestamp(1604447498),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_DUSD)
CRV_AETH = EvmToken.initialize(
    address=string_to_evm_address('0xaA17A236F2bAdc98DDc0Cf999AbB47D47Fc0A6Cf'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi ETH/aETH",
    symbol='ankrCRV',
    started=Timestamp(1612233081),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_AETH)
CRV_ADAI_ASUSD = EvmToken.initialize(
    address=string_to_evm_address('0x02d341CcB60fAaf662bC0554d13778015d1b285C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi aDAI/aSUSD",
    symbol='saCRV',
    started=Timestamp(1612211177),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_ADAI_ASUSD)
CRV_USDP = EvmToken.initialize(
    address=string_to_evm_address('0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Curve.fi USDP/3Crv",
    symbol='usdp3CRV',
    started=Timestamp(1614197821),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='curve_pool',
)
CONSTANT_ASSETS.append(CRV_USDP)

A_YV1_CDAI_CUSD = EvmToken.initialize(
    address=string_to_evm_address('0x629c759D1E83eFbF63d84eb3868B564d9521C129'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi cDAI/cUSDC",
    symbol='yvcDAI+cUSDC',
    started=Timestamp(1604758201),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_CDAI_CUSD)
A_YV1_MSUD_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x0FCDAeDFb8A7DfDa2e9838564c5A1665d856AFDF'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi MUSD/3Crv",
    symbol='yvmusd3CRV',
    started=Timestamp(1607160847),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_MSUD_CRV)
A_YV1_GUSD_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xcC7E70A958917cCe67B4B87a8C30E6297451aE98'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi GUSD/3Crv",
    symbol='yvgusd3CRV',
    started=Timestamp(1607237689),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_GUSD_CRV)
A_YV1_EURS_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x98B058b2CBacF5E99bC7012DF757ea7CFEbd35BC'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi EURS/sEUR",
    symbol='yveursCRV',
    started=Timestamp(1610435041),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_EURS_CRV)
A_YV1_MUSD_VAULT = EvmToken.initialize(
    address=string_to_evm_address('0xE0db48B4F71752C4bEf16De1DBD042B82976b8C7'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn mStable USD",
    symbol='yvmUSD',
    started=Timestamp(1609441345),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_MUSD_VAULT)
A_YV1_RENBT_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi renBTC/wBTC",
    symbol='yvcrvRenWBTC',
    started=Timestamp(1611583752),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_RENBT_CRV)
A_YV1_USDN_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xFe39Ce91437C76178665D64d7a2694B0f6f17fE3'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi USDN/3Crv",
    symbol='yvusdn3CRV',
    started=Timestamp(1611451016),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_USDN_CRV)
A_YV1_UST_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xF6C9E9AF314982A4b38366f4AbfAa00595C5A6fC'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi UST/3Crv",
    symbol='yvust3CRV',
    started=Timestamp(1611444747),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_UST_CRV)
A_YV1_BBTC_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xA8B1Cb4ed612ee179BDeA16CCa6Ba596321AE52D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi bBTC/sbtcCRV",
    symbol='yvbBTC/sbtcCRV',
    started=Timestamp(1611443166),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_BBTC_CRV)
A_YV1_TBTC_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x07FB4756f67bD46B748b16119E802F1f880fb2CC'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi tBTC/sbtcCrv",
    symbol='yvtbtc/sbtcCrv',
    started=Timestamp(1611641883),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_TBTC_CRV)
A_YV1_OBTC_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x7F83935EcFe4729c4Ea592Ab2bC1A32588409797'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi oBTC/sbtcCRV",
    symbol='yvoBTC/sbtcCRV',
    started=Timestamp(1611698586),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_OBTC_CRV)
A_YV1_HBTC_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x46AFc2dfBd1ea0c0760CAD8262A5838e803A37e5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi hBTC/wBTC",
    symbol='yvhCRV',
    started=Timestamp(1611973890),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_HBTC_CRV)
A_YV1_SUSD_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x5533ed0a3b83F70c3c4a1f69Ef5546D3D4713E44'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi DAI/USDC/USDT/sUSD",
    symbol='yvcrvPlain3andSUSD',
    started=Timestamp(1611704712),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_SUSD_CRV)
A_YV1_HUSD_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x39546945695DCb1c037C836925B355262f551f55'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi HUSD/3Crv",
    symbol='yvhusd3CRV',
    started=Timestamp(1611973890),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_HUSD_CRV)
A_YV1_DUSD_3CRV = EvmToken.initialize(
    address=string_to_evm_address('0x8e6741b456a074F0Bc45B8b82A755d4aF7E965dF'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi DUSD/3Crv",
    symbol='yvdusd3CRV',
    started=Timestamp(1611973890),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_DUSD_3CRV)
A_YV1_A3CRV = EvmToken.initialize(
    address=string_to_evm_address('0x03403154afc09Ce8e44C3B185C82C6aD5f86b9ab'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi aDAI/aUSDC/aUSDT",
    symbol='yva3CRV',
    started=Timestamp(1612192629),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_A3CRV)
A_YV1_ETH_ANKER = EvmToken.initialize(
    address=string_to_evm_address('0xE625F5923303f1CE7A43ACFEFd11fd12f30DbcA4'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi ETH/aETH",
    symbol='yvankrCRV',
    started=Timestamp(1613091218),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_ETH_ANKER)
A_YV1_ASUSD_CRV = EvmToken.initialize(
    address=string_to_evm_address('0xBacB69571323575C6a5A3b4F9EEde1DC7D31FBc1'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi aDAI/aSUSD",
    symbol='yvsaCRV',
    started=Timestamp(1613888556),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_ASUSD_CRV)
A_YV1_USDP_CRV = EvmToken.initialize(
    address=string_to_evm_address('0x1B5eb1173D2Bf770e50F10410C9a96F7a8eB6e75'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn Curve.fi USDP/3Crv",
    symbol='yvusdp3CRV',
    started=Timestamp(1614835272),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_USDP_CRV)
A_YV1_PSLP = EvmToken.initialize(
    address=string_to_evm_address('0xbD17B1ce622d73bD438b9E658acA5996dc394b0d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="yearn pSLP",
    symbol='yvpSLP',
    started=Timestamp(1599694464),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol='yearn-v1',
)
CONSTANT_ASSETS.append(A_YV1_PSLP)


A_FARM_USDC = EvmToken.initialize(
    address=string_to_evm_address('0xf0358e8c3CD5Fa238a29301d0bEa3D63A17bEdBE'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="FARM_USDC",
    symbol='fUSDC',
    started=Timestamp(1603116154),
    swapped_for=None,
    coingecko='usd-coin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_USDC)
A_FARM_USDT = EvmToken.initialize(
    address=string_to_evm_address('0x053c80eA73Dc6941F518a68E2FC52Ac45BDE7c9C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="FARM_USDT",
    symbol='fUSDT',
    started=Timestamp(1603116272),
    swapped_for=None,
    coingecko='tether',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_USDT)
A_FARM_DAI = EvmToken.initialize(
    address=string_to_evm_address('0xab7FA2B2985BCcfC13c6D86b1D5A17486ab1e04C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="FARM_DAI",
    symbol='fDAI',
    started=Timestamp(1603116059),
    swapped_for=None,
    coingecko='dai',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_DAI)
A_FARM_TUSD = EvmToken.initialize(
    address=string_to_evm_address('0x7674622c63Bee7F46E86a4A5A18976693D54441b'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="FARM_TUSD",
    symbol='fTUSD',
    started=Timestamp(1601927319),
    swapped_for=None,
    coingecko='true-usd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_TUSD)
A_FARM_WETH = EvmToken.initialize(
    address=string_to_evm_address('0xFE09e53A81Fe2808bc493ea64319109B5bAa573e'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="FARM_WETH",
    symbol='fWETH',
    started=Timestamp(1603115998),
    swapped_for=None,
    coingecko='weth',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_WETH)
A_FARM_WBTC = EvmToken.initialize(
    address=string_to_evm_address('0x5d9d25c7C457dD82fc8668FFC6B9746b674d4EcB'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="FARM_WBTC",
    symbol='fWBTC',
    started=Timestamp(1602866633),
    swapped_for=None,
    coingecko='wrapped-bitcoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_WBTC)
A_FARM_RENBTC = EvmToken.initialize(
    address=string_to_evm_address('0xC391d1b08c1403313B0c28D47202DFDA015633C4'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="FARM_renBTC",
    symbol='frenBTC',
    started=Timestamp(1603116341),
    swapped_for=None,
    coingecko='renbtc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_RENBTC)
A_FARM_CRVRENWBTC = EvmToken.initialize(
    address=string_to_evm_address('0x9aA8F427A17d6B0d91B6262989EdC7D45d6aEdf8'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="FARM_crvRenWBTC",
    symbol='fcrvRenWBTC',
    started=Timestamp(1603116454),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM_CRVRENWBTC)


# Needed by independentreserve
A_XRP = CryptoAsset.initialize(
    identifier='XRP',
    asset_type=AssetType.OWN_CHAIN,
    name="Ripple",
    symbol='XRP',
    started=Timestamp(1364774400),
    forked=None,
    swapped_for=None,
    coingecko='ripple',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_XRP)
A_ADA = CryptoAsset.initialize(
    identifier='ADA',
    asset_type=AssetType.OWN_CHAIN,
    name="Cardano",
    symbol='ADA',
    started=Timestamp(1506643200),
    forked=None,
    swapped_for=None,
    coingecko='cardano',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_ADA)
A_DOT = CryptoAsset.initialize(
    identifier='DOT',
    asset_type=AssetType.OWN_CHAIN,
    name="Polkadot",
    symbol='DOT',
    started=Timestamp(1590451200),
    forked=None,
    swapped_for=None,
    coingecko='polkadot',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_DOT)
A_LTC = CryptoAsset.initialize(
    identifier='LTC',
    asset_type=AssetType.OWN_CHAIN,
    name="Litecoin",
    symbol='LTC',
    started=Timestamp(1317972665),
    forked=None,
    swapped_for=None,
    coingecko='litecoin',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_LTC)
A_EOS = CryptoAsset.initialize(
    identifier='EOS',
    asset_type=AssetType.OWN_CHAIN,
    name="EOS.io",
    symbol='EOS',
    started=Timestamp(1494028800),
    forked=None,
    swapped_for=None,
    coingecko='eos',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_EOS)
A_XLM = CryptoAsset.initialize(
    identifier='XLM',
    asset_type=AssetType.OWN_CHAIN,
    name="Stellar Lumens",
    symbol='XLM',
    started=Timestamp(1374192000),
    forked=None,
    swapped_for=None,
    coingecko='stellar',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_XLM)
A_GRT = EvmToken.initialize(
    address=string_to_evm_address('0xc944E90C64B2c07662A292be6244BDf05Cda44a7'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Graph Token",
    symbol='GRT',
    started=Timestamp(1607890633),
    swapped_for=None,
    coingecko='the-graph',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GRT)
A_PMGT = EvmToken.initialize(
    address=string_to_evm_address('0xAFFCDd96531bCd66faED95FC61e443D08F79eFEf'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=5,
    name="Perth Mint Gold Token",
    symbol='PMGT',
    started=Timestamp(1570681682),
    swapped_for=None,
    coingecko='perth-mint-gold-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PMGT)
A_OMG = EvmToken.initialize(
    address=string_to_evm_address('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="OmiseGO",
    symbol='OMG',
    started=Timestamp(1498176000),
    swapped_for=None,
    coingecko='omisego',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_OMG)

A_AUD = AssetWithSymbol.initialize(
    identifier='AUD',
    asset_type=AssetType.FIAT,
    name="Australian Dollar",
    symbol='AUD',
)
CONSTANT_ASSETS.append(A_AUD)
A_NZD = AssetWithSymbol.initialize(
    identifier='NZD',
    asset_type=AssetType.FIAT,
    name="New Zealand Dollar",
    symbol='NZD',
)
CONSTANT_ASSETS.append(A_NZD)
A_SGD = AssetWithSymbol.initialize(
    identifier='SGD',
    asset_type=AssetType.FIAT,
    name="Singapore Dollar",
    symbol='SGD',
)
CONSTANT_ASSETS.append(A_SGD)

# Needed by cryptocompare.py
A_KRW = AssetWithSymbol.initialize(
    identifier='KRW',
    asset_type=AssetType.FIAT,
    name="Korean won",
    symbol='KRW',
)
CONSTANT_ASSETS.append(A_KRW)

# Needed by airdrops.py
A_CVX = EvmToken.initialize(
    address=string_to_evm_address('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Convex Token",
    symbol='CVX',
    started=Timestamp(1621242525),
    swapped_for=None,
    coingecko='convex-finance',
    cryptocompare='CVX',
    protocol=None,
)
CONSTANT_ASSETS.append(A_CVX)
A_ELFI = EvmToken.initialize(
    address=string_to_evm_address('0x5c6D51ecBA4D8E4F20373e3ce96a62342B125D6d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Element Finance",
    symbol='ELFI',
    started=Timestamp(1642012745),
    swapped_for=None,
    coingecko='element-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ELFI)

# Needed by iconomi
A_AUST = CryptoAsset.initialize(
    identifier='AUST',
    asset_type=AssetType.OTHER,
    name="AnchorUST",
    symbol='AUST',
    started=Timestamp(1638331459),
    forked=None,
    swapped_for=None,
    coingecko='anchorust',
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_AUST)

# Needed by loopring.py
A_HT = EvmToken.initialize(
    address=string_to_evm_address('0x6f259637dcD74C767781E37Bc6133cd6A68aa161'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Huobi Token",
    symbol='HT',
    started=Timestamp(1516579200),
    swapped_for=None,
    coingecko='huobi-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_HT)
A_OKB = EvmToken.initialize(
    address=string_to_evm_address('0x75231F58b43240C9718Dd58B4967c5114342a86c'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="OKB",
    symbol='OKB',
    started=Timestamp(1556264879),
    swapped_for=None,
    coingecko='okb',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_OKB)
A_KEEP = EvmToken.initialize(
    address=string_to_evm_address('0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="KEEP Token ",
    symbol='KEEP',
    started=Timestamp(1588042366),
    swapped_for=None,
    coingecko='keep-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_KEEP)
A_DXD = EvmToken.initialize(
    address=string_to_evm_address('0xa1d65E8fB6e87b60FECCBc582F7f97804B725521'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="DXdao",
    symbol='DXD',
    started=Timestamp(1588752887),
    swapped_for=None,
    coingecko='dxdao',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DXD)
SWAPPEDFOR_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5 = CryptoAsset.initialize(
    identifier='eip155:1/erc20:0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0',
    asset_type=AssetType.EVM_TOKEN,
    name="Tellor",
    symbol='TRB',
    started=Timestamp(1613850551),
    forked=None,
    swapped_for=None,
    coingecko='tellor',
    cryptocompare='TRB',
)
CONSTANT_ASSETS.append(SWAPPEDFOR_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5)
A_TRB = EvmToken.initialize(
    address=string_to_evm_address('0x0Ba45A8b5d5575935B8158a88C631E9F9C95a2e5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Tellor Tributes",
    symbol='TRB',
    started=Timestamp(1564671864),
    swapped_for=SWAPPEDFOR_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5,
    coingecko='tellor',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TRB)
A_AUC = EvmToken.initialize(
    address=string_to_evm_address('0xc12d099be31567add4e4e4d0D45691C3F58f5663'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Auctus",
    symbol='AUC',
    started=Timestamp(1522090240),
    swapped_for=None,
    coingecko='auctus',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_AUC)
A_RPL = EvmToken.initialize(
    address=string_to_evm_address('0xB4EFd85c19999D84251304bDA99E90B92300Bd93'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Rocket Pool",
    symbol='RPL',
    started=Timestamp(1504750041),
    swapped_for=None,
    coingecko='rocket-pool',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_RPL)
A_GNO = EvmToken.initialize(
    address=string_to_evm_address('0x6810e776880C02933D47DB1b9fc05908e5386b96'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Gnosis token",
    symbol='GNO',
    started=Timestamp(1492992000),
    swapped_for=None,
    coingecko='gnosis',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GNO)
A_BNT = EvmToken.initialize(
    address=string_to_evm_address('0x1F573D6Fb3F13d689FF844B4cE37794d79a7FF1C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Bancor",
    symbol='BNT',
    started=Timestamp(1497657600),
    swapped_for=None,
    coingecko='bancor',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BNT)
A_PBTC = EvmToken.initialize(
    address=string_to_evm_address('0x5228a22e72ccC52d415EcFd199F99D0665E7733b'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="pTokens BTC",
    symbol='pBTC',
    started=Timestamp(1583307208),
    swapped_for=None,
    coingecko='ptokens-btc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PBTC)
A_PNT = EvmToken.initialize(
    address=string_to_evm_address('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="pNetwork Token",
    symbol='PNT',
    started=Timestamp(1592411070),
    swapped_for=None,
    coingecko='pnetwork',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PNT)
A_GRID = EvmToken.initialize(
    address=string_to_evm_address('0x12B19D3e2ccc14Da04FAe33e63652ce469b3F2FD'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=12,
    name="Grid+",
    symbol='GRID',
    started=Timestamp(1499817600),
    swapped_for=None,
    coingecko='grid',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GRID)
A_PNK = EvmToken.initialize(
    address=string_to_evm_address('0x93ED3FBe21207Ec2E8f2d3c3de6e058Cb73Bc04d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Kleros",
    symbol='PNK',
    started=Timestamp(1521078220),
    swapped_for=None,
    coingecko='kleros',
    cryptocompare='PNK',
    protocol=None,
)
CONSTANT_ASSETS.append(A_PNK)
A_NEST = EvmToken.initialize(
    address=string_to_evm_address('0x04abEdA201850aC0124161F037Efd70c74ddC74C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="NEST",
    symbol='NEST',
    started=Timestamp(1545191462),
    swapped_for=None,
    coingecko='nest',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_NEST)
A_BTU = EvmToken.initialize(
    address=string_to_evm_address('0xb683D83a532e2Cb7DFa5275eED3698436371cc9f'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="BTU Protocol",
    symbol='BTU',
    started=Timestamp(1525910400),
    swapped_for=None,
    coingecko='btu-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BTU)
A_VBZRX = EvmToken.initialize(
    address=string_to_evm_address('0xB72B31907C1C95F3650b64b2469e08EdACeE5e8F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="bZx Vesting Token",
    symbol='vBZRX',
    started=Timestamp(1594495494),
    swapped_for=None,
    coingecko='vbzrx',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_VBZRX)
A_NMR = EvmToken.initialize(
    address=string_to_evm_address('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Numeraire",
    symbol='NMR',
    started=Timestamp(1496952637),
    swapped_for=None,
    coingecko='numeraire',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_NMR)
A_SNT = EvmToken.initialize(
    address=string_to_evm_address('0x744d70FDBE2Ba4CF95131626614a1763DF805B9E'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Status Network Token",
    symbol='SNT',
    started=Timestamp(1497889273),
    swapped_for=None,
    coingecko='status',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SNT)
A_MTA = EvmToken.initialize(
    address=string_to_evm_address('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Meta",
    symbol='MTA',
    started=Timestamp(1594635836),
    swapped_for=None,
    coingecko='meta',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MTA)
A_ONG = EvmToken.initialize(
    address=string_to_evm_address('0xd341d1680Eeee3255b8C4c75bCCE7EB57f144dAe'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="SoMee.Social",
    symbol='ONG',
    started=Timestamp(1497657600),
    swapped_for=None,
    coingecko='ong-social',
    cryptocompare='ONG',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ONG)
A_GRG = EvmToken.initialize(
    address=string_to_evm_address('0x4FbB350052Bca5417566f188eB2EBCE5b19BC964'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Rigo Token",
    symbol='GRG',
    started=Timestamp(1541876282),
    swapped_for=None,
    coingecko='rigoblock',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_GRG)
A_QCAD = EvmToken.initialize(
    address=string_to_evm_address('0x4A16BAf414b8e637Ed12019faD5Dd705735DB2e0'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=2,
    name="QCAD",
    symbol='QCAD',
    started=Timestamp(1578449585),
    swapped_for=None,
    coingecko='qcad',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_QCAD)
A_TON = EvmToken.initialize(
    address=string_to_evm_address('0x6a6c2adA3Ce053561C2FbC3eE211F23d9b8C520a'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="TONToken",
    symbol='TON',
    started=Timestamp(1597639121),
    swapped_for=None,
    coingecko='tontoken',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TON)
A_BAND = EvmToken.initialize(
    address=string_to_evm_address('0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Band Protocol",
    symbol='BAND',
    started=Timestamp(1567987200),
    swapped_for=None,
    coingecko='band-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BAND)
A_UMA = EvmToken.initialize(
    address=string_to_evm_address('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="UMA Voting Token v1",
    symbol='UMA',
    started=Timestamp(1578581061),
    swapped_for=None,
    coingecko='uma',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_UMA)
A_WNXM = EvmToken.initialize(
    address=string_to_evm_address('0x0d438F3b5175Bebc262bF23753C1E53d03432bDE'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Wrapped Nexus Mutual",
    symbol='wNXM',
    started=Timestamp(1593733266),
    swapped_for=None,
    coingecko='wrapped-nxm',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_WNXM)
A_ENTRP = EvmToken.initialize(
    address=string_to_evm_address('0x5BC7e5f0Ab8b2E10D2D0a3F21739FCe62459aeF3'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Hut34 Entropy Token",
    symbol='ENTRP',
    started=Timestamp(1504742400),
    swapped_for=None,
    coingecko='hut34-entropy',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ENTRP)
A_NIOX = EvmToken.initialize(
    address=string_to_evm_address('0xc813EA5e3b48BEbeedb796ab42A30C5599b01740'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=4,
    name="Autonio",
    symbol='NIOX',
    started=Timestamp(1593134600),
    swapped_for=None,
    coingecko='autonio',
    cryptocompare='AUTON',
    protocol=None,
)
CONSTANT_ASSETS.append(A_NIOX)
A_OGN = EvmToken.initialize(
    address=string_to_evm_address('0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Origin Protocol",
    symbol='OGN',
    started=Timestamp(1538352000),
    swapped_for=None,
    coingecko='origin-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_OGN)
A_HEX = EvmToken.initialize(
    address=string_to_evm_address('0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=8,
    name="HEX",
    symbol='HEX',
    started=Timestamp(1575331200),
    swapped_for=None,
    coingecko='hex',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_HEX)
A_HBTC = EvmToken.initialize(
    address=string_to_evm_address('0x0316EB71485b0Ab14103307bf65a021042c6d380'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Huobi BTC ",
    symbol='HBTC',
    started=Timestamp(1575863326),
    swapped_for=None,
    coingecko='huobi-btc',
    cryptocompare='HBTC',
    protocol=None,
)
CONSTANT_ASSETS.append(A_HBTC)
A_PLTC = EvmToken.initialize(
    address=string_to_evm_address('0x5979F50f1D4c08f9A53863C2f39A7B0492C38d0f'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="pTokens LTC",
    symbol='pLTC',
    started=Timestamp(1595926001),
    swapped_for=None,
    coingecko='ptokens-ltc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_PLTC)
A_FIN = EvmToken.initialize(
    address=string_to_evm_address('0x054f76beED60AB6dBEb23502178C52d6C5dEbE40'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="DeFiner",
    symbol='FIN',
    started=Timestamp(1599618925),
    swapped_for=None,
    coingecko='definer',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FIN)
A_DOUGH = EvmToken.initialize(
    address=string_to_evm_address('0xad32A8e6220741182940c5aBF610bDE99E737b2D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PieDAO DOUGH v2",
    symbol='DOUGH',
    started=Timestamp(1599823243),
    swapped_for=None,
    coingecko='piedao-dough-v2',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DOUGH)
A_DEFI_L = EvmToken.initialize(
    address=string_to_evm_address('0x78F225869c08d478c34e5f645d07A87d3fe8eb78'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PieDAO DEFI Large Cap",
    symbol='DEFI+L',
    started=Timestamp(1602115200),
    swapped_for=None,
    coingecko='piedao-defi-large-cap',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DEFI_L)
A_DEFI_S = EvmToken.initialize(
    address=string_to_evm_address('0xaD6A626aE2B43DCb1B39430Ce496d2FA0365BA9C'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PieDAO DEFI Small Cap",
    symbol='DEFI+S',
    started=Timestamp(1602115200),
    swapped_for=None,
    coingecko='piedao-defi-small-cap',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_DEFI_S)
A_TRYB = EvmToken.initialize(
    address=string_to_evm_address('0x2C537E5624e4af88A7ae4060C022609376C8D0EB'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=6,
    name="BiLira",
    symbol='TRYB',
    started=Timestamp(1563539445),
    swapped_for=None,
    coingecko='bilira',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TRYB)
A_CEL = EvmToken.initialize(
    address=string_to_evm_address('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=4,
    name="Celsius",
    symbol='CEL',
    started=Timestamp(1554810016),
    swapped_for=None,
    coingecko='celsius-degree-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CEL)
A_AMP = EvmToken.initialize(
    address=string_to_evm_address('0xfF20817765cB7f73d4bde2e66e067E58D11095C2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Amp",
    symbol='AMP',
    started=Timestamp(1597148839),
    swapped_for=None,
    coingecko='amp-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_AMP)
A_KP3R = EvmToken.initialize(
    address=string_to_evm_address('0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Keep3rV1",
    symbol='KP3R',
    started=Timestamp(1603871844),
    swapped_for=None,
    coingecko='keep3rv1',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_KP3R)
A_AC = EvmToken.initialize(
    address=string_to_evm_address('0x9A0aBA393aac4dFbFf4333B06c407458002C6183'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="ACoconut ",
    symbol='AC',
    started=Timestamp(1601507639),
    swapped_for=None,
    coingecko='acoconut',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_AC)
A_CVT = EvmToken.initialize(
    address=string_to_evm_address('0xBe428c3867F05deA2A89Fc76a102b544eaC7f772'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="CyberVein",
    symbol='CVT',
    started=Timestamp(1516888006),
    swapped_for=None,
    coingecko='cybervein',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CVT)
A_WOO = EvmToken.initialize(
    address=string_to_evm_address('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Wootrade Network",
    symbol='WOO',
    started=Timestamp(1602855151),
    swapped_for=None,
    coingecko='woo-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_WOO)
A_BEL = EvmToken.initialize(
    address=string_to_evm_address('0xA91ac63D040dEB1b7A5E4d4134aD23eb0ba07e14'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Bella",
    symbol='BEL',
    started=Timestamp(1597392058),
    swapped_for=None,
    coingecko='bella-protocol',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BEL)
A_OBTC = EvmToken.initialize(
    address=string_to_evm_address('0x8064d9Ae6cDf087b1bcd5BDf3531bD5d8C537a68'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="BoringDAO BTC",
    symbol='oBTC',
    started=Timestamp(1605169554),
    swapped_for=None,
    coingecko='boringdao-btc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_OBTC)
A_INDEX = EvmToken.initialize(
    address=string_to_evm_address('0x0954906da0Bf32d5479e25f46056d22f08464cab'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Index",
    symbol='INDEX',
    started=Timestamp(1601964283),
    swapped_for=None,
    coingecko='index-cooperative',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_INDEX)
A_TTV = EvmToken.initialize(
    address=string_to_evm_address('0xa838be6E4b760E6061D4732D6B9F11Bf578f9A76'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="TV-TWO",
    symbol='TTV',
    started=Timestamp(1526568632),
    swapped_for=None,
    coingecko='tv-two',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TTV)
A_FARM = EvmToken.initialize(
    address=string_to_evm_address('0xa0246c9032bC3A600820415aE600c6388619A14D'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Harvest Finance",
    symbol='FARM',
    started=Timestamp(1598895285),
    swapped_for=None,
    coingecko='harvest-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FARM)
A_BOR = EvmToken.initialize(
    address=string_to_evm_address('0x3c9d6c1C73b31c837832c72E04D3152f051fc1A9'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="BoringDAO",
    symbol='BOR',
    started=Timestamp(1603390844),
    swapped_for=None,
    coingecko='boringdao',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BOR)
A_RFOX = EvmToken.initialize(
    address=string_to_evm_address('0xa1d6Df714F91DeBF4e0802A542E13067f31b8262'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="RFOX",
    symbol='RFOX',
    started=Timestamp(1603301829),
    swapped_for=None,
    coingecko='redfox-labs-2',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_RFOX)
A_NEC = EvmToken.initialize(
    address=string_to_evm_address('0xCc80C051057B774cD75067Dc48f8987C4Eb97A5e'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Ethfinex Nectar Token",
    symbol='NEC',
    started=Timestamp(1512086400),
    swapped_for=None,
    coingecko='nectar-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_NEC)
A_RGT = EvmToken.initialize(
    address=string_to_evm_address('0xD291E7a03283640FDc51b121aC401383A46cC623'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Rari Governance Token",
    symbol='RGT',
    started=Timestamp(1603212673),
    swapped_for=None,
    coingecko='rari-governance-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_RGT)
A_VSP = EvmToken.initialize(
    address=string_to_evm_address('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="VesperToken",
    symbol='VSP',
    started=Timestamp(1613051449),
    swapped_for=None,
    coingecko='vesper-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_VSP)
A_SMARTCREDIT = EvmToken.initialize(
    address=string_to_evm_address('0x72e9D9038cE484EE986FEa183f8d8Df93f9aDA13'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="SMARTCREDIT Token",
    symbol='SMARTCREDIT',
    started=Timestamp(1602058612),
    swapped_for=None,
    coingecko='smartcredit-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SMARTCREDIT)
A_RAI = EvmToken.initialize(
    address=string_to_evm_address('0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Rai Reflex Index",
    symbol='RAI',
    started=Timestamp(1613221351),
    swapped_for=None,
    coingecko='rai',
    cryptocompare='RAI',
    protocol=None,
)
CONSTANT_ASSETS.append(A_RAI)
A_TEL = EvmToken.initialize(
    address=string_to_evm_address('0x467Bccd9d29f223BcE8043b84E8C8B282827790F'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=2,
    name="Telcoin",
    symbol='TEL',
    started=Timestamp(1510358400),
    swapped_for=None,
    coingecko='telcoin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TEL)
A_BCP = EvmToken.initialize(
    address=string_to_evm_address('0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PieDAO Balanced Crypto Pie",
    symbol='BCP',
    started=Timestamp(1606733040),
    swapped_for=None,
    coingecko='piedao-balanced-crypto-pie',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BCP)
A_BADGER = EvmToken.initialize(
    address=string_to_evm_address('0x3472A5A71965499acd81997a54BBA8D852C6E53d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Badger",
    symbol='BADGER',
    started=Timestamp(1606584722),
    swapped_for=None,
    coingecko='badger-dao',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_BADGER)
A_SUSHI = EvmToken.initialize(
    address=string_to_evm_address('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="SushiToken",
    symbol='SUSHI',
    started=Timestamp(1598444887),
    swapped_for=None,
    coingecko='sushi',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SUSHI)
A_MASK = EvmToken.initialize(
    address=string_to_evm_address('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Mask Network",
    symbol='MASK',
    started=Timestamp(1613723201),
    swapped_for=None,
    coingecko='mask-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_MASK)
A_YPIE = EvmToken.initialize(
    address=string_to_evm_address('0x17525E4f4Af59fbc29551bC4eCe6AB60Ed49CE31'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="PieDAO Yearn Ecosystem Pie",
    symbol='YPIE',
    started=Timestamp(1608299408),
    swapped_for=None,
    coingecko='piedao-yearn-ecosystem-pie',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YPIE)
A_FUSE = EvmToken.initialize(
    address=string_to_evm_address('0x970B9bB2C0444F5E81e9d0eFb84C8ccdcdcAf84d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Fuse Token",
    symbol='FUSE',
    started=Timestamp(1567507220),
    swapped_for=None,
    coingecko='fuse-network-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FUSE)
A_SX = EvmToken.initialize(
    address=string_to_evm_address('0x99fE3B1391503A1bC1788051347A1324bff41452'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="SportX",
    symbol='SX',
    started=Timestamp(1610747210),
    swapped_for=None,
    coingecko='sx-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SX)
A_RSPT = EvmToken.initialize(
    address=string_to_evm_address('0x016bf078ABcaCB987f0589a6d3BEAdD4316922B0'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Rari Stable Pool Token",
    symbol='RSPT',
    started=Timestamp(1600740632),
    swapped_for=None,
    coingecko='rari-stable-pool-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_RSPT)
A_FOX = EvmToken.initialize(
    address=string_to_evm_address('0xc770EEfAd204B5180dF6a14Ee197D99d808ee52d'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="FOX Token",
    symbol='FOX',
    started=Timestamp(1553639047),
    swapped_for=None,
    coingecko='shapeshift-fox-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_FOX)
A_ENS = EvmToken.initialize(
    address=string_to_evm_address('0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Ethereum Name Service",
    symbol='ENS',
    started=Timestamp(1635800117),
    swapped_for=None,
    coingecko='ethereum-name-service',
    cryptocompare='ENS',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ENS)
A_PSP = EvmToken.initialize(
    address=string_to_evm_address('0xcAfE001067cDEF266AfB7Eb5A286dCFD277f3dE5'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="ParaSwap",
    symbol='PSP',
    started=Timestamp(1636966698),
    swapped_for=None,
    coingecko='paraswap',
    cryptocompare='PSP',
    protocol=None,
)
CONSTANT_ASSETS.append(A_PSP)
A_SDL = EvmToken.initialize(
    address=string_to_evm_address('0xf1Dc500FdE233A4055e25e5BbF516372BC4F6871'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Saddle DAO",
    symbol='SDL',
    started=Timestamp(1637043563),
    swapped_for=None,
    coingecko='saddle-finance',
    cryptocompare='SDL',
    protocol=None,
)
CONSTANT_ASSETS.append(A_SDL)
A_VCOW = EvmToken.initialize(
    address=string_to_evm_address('0xD057B63f5E69CF1B929b356b579Cba08D7688048'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="CoW Protocol Virtual Token",
    symbol='vCOW',
    started=Timestamp(1644609915),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_VCOW)
A_FPIS = EvmToken.initialize(
    address=string_to_evm_address('0xc2544A32872A91F4A553b404C6950e89De901fdb'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Frax Price Index Share",
    symbol='FPIS',
    started=Timestamp(1648578483),
    swapped_for=None,
    coingecko='frax-price-index-share',
    cryptocompare='FPIS',
    protocol=None,
)
CONSTANT_ASSETS.append(A_FPIS)
A_ALETH = EvmToken.initialize(
    address=string_to_evm_address('0x0100546F2cD4C9D97f798fFC9755E47865FF7Ee6'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Alchemix ETH",
    symbol='alETH',
    started=Timestamp(1623421341),
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_ALETH)
A_STETH = EvmToken.initialize(
    address=string_to_evm_address('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="Liquid staked Ether 2.0",
    symbol='stETH',
    started=Timestamp(1608242396),
    swapped_for=None,
    coingecko='staked-ether',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_STETH)
A_SAND = EvmToken.initialize(
    address=string_to_evm_address('0x3845badAde8e6dFF049820680d1F14bD3903a5d0'),
    chain=ChainID(1),
    token_kind=EvmTokenKind(1),
    decimals=18,
    name="The Sandbox",
    symbol='SAND',
    started=Timestamp(1572367723),
    swapped_for=None,
    coingecko='the-sandbox',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SAND)
