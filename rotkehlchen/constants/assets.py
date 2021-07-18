# This python file was generated automatically by
# tools/scripts/generate_constant_assets.py at 08/07/2021 21:43:30.
# Do not edit manually!

from typing import List

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.typing import Timestamp
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address

CONSTANT_ASSETS: List[Asset] = []

A_USD = Asset.initialize(
    identifier='USD',
    asset_type=AssetType.FIAT,
    name="United States Dollar",
    symbol='USD',
    started=None,
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_USD)
A_EUR = Asset.initialize(
    identifier='EUR',
    asset_type=AssetType.FIAT,
    name="Euro",
    symbol='EUR',
    started=Timestamp(915148800),
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_EUR)
A_BTC = Asset.initialize(
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
A_BCH = Asset.initialize(
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
A_BSV = Asset.initialize(
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
A_ETH = Asset.initialize(
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
A_ETH2 = Asset.initialize(
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
A_ETC = Asset.initialize(
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
A_KSM = Asset.initialize(
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

A_BAL = EthereumToken.initialize(
    address=string_to_ethereum_address('0xba100000625a3754423978a60c9317c58a424e3D'),
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
A_BAT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'),
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
A_UNI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'),
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
A_1INCH = EthereumToken.initialize(
    address=string_to_ethereum_address('0x111111111117dC0aa78b770fA6A738034120C302'),
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
A_DAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
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
A_SAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
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
A_YFI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'),
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
A_USDT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
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
A_USDC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
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
A_TUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0000000000085d4780B73119b644AE5ecd22b376'),
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

A_AAVE = EthereumToken.initialize(
    address=string_to_ethereum_address('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'),
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
A_GUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd'),
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
A_CRV = EthereumToken.initialize(
    address=string_to_ethereum_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
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
A_KNC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xdd974D5C2e2928deA5F71b9825b8b646686BD200'),
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
A_WBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
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
A_WETH = EthereumToken.initialize(
    address=string_to_ethereum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
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
A_ZRX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xE41d2489571d322189246DaFA5ebDe1F4699F498'),
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
A_MANA = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942'),
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
A_PAX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x8E870D67F660D95d5be530380D0eC0bd388289E1'),
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
A_COMP = EthereumToken.initialize(
    address=string_to_ethereum_address('0xc00e94Cb662C3520282E6f5717214004A7f26888'),
    decimals=18,
    name="Compound",
    symbol='COMP',
    started=Timestamp(1583323735),
    swapped_for=None,
    coingecko='compound-governance-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_COMP)
A_LRC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD'),
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
A_LINK = EthereumToken.initialize(
    address=string_to_ethereum_address('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
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
A_ADX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'),
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
A_TORN = EthereumToken.initialize(
    address=string_to_ethereum_address('0x77777FeDdddFfC19Ff86DB637967013e6C6A116C'),
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
A_CORN = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa456b515303B2Ce344E9d2601f91270f8c2Fea5E'),
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
A_GRAIN = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6589fe1271A0F29346796C6bAf0cdF619e25e58e'),
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
A_COMBO = EthereumToken.initialize(
    address=string_to_ethereum_address('0xfFffFffF2ba8F66D4e51811C5190992176930278'),
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
A_LDO = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
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
A_RENBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D'),
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
A_BNB = EthereumToken.initialize(
    address=string_to_ethereum_address('0xB8c77482e45F1F44dE1745F52C74426C631bDD52'),
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
A_REP = EthereumToken.initialize(
    address=string_to_ethereum_address('0x221657776846890989a759BA2973e427DfF5C9bB'),
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
A_BZRX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x56d811088235F11C8920698a204A5010a788f4b3'),
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
A_STAKE = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0Ae055097C6d159879521C384F1D2123D1f195e6'),
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
A_DPI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b'),
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
A_YFII = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa1d0E215a23d7030842FC67cE582a6aFa3CCaB83'),
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
A_MCB = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4e352cF164E64ADCBad318C3a1e222E9EBa4Ce42'),
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

# used as underlying assets of aave v1 tokens
A_ENJ = EthereumToken.initialize(
    address=string_to_ethereum_address('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'),
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
A_SUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51'),
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
A_BUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
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
A_LEND = EthereumToken.initialize(
    address=string_to_ethereum_address('0x80fB784B7eD66730e8b1DBd9820aFD29931aab03'),
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
A_MKR = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
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
A_REN = EthereumToken.initialize(
    address=string_to_ethereum_address('0x408e41876cCCDC0F92210600ef50372656052a38'),
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
A_SNX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
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

A_ALINK_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84'),
    decimals=18,
    name="Aave Interest bearing LINK",
    symbol='aLINK',
    started=Timestamp(1578501727),
    swapped_for=None,
    coingecko='aave-link',
    cryptocompare='LINK',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ALINK_V1)
A_AETH_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x3a3A65aAb0dd2A17E3F1947bA16138cd37d08c04'),
    decimals=18,
    name="Aave Interest bearing ETH",
    symbol='aETH',
    started=Timestamp(1578501678),
    swapped_for=None,
    coingecko='aave-eth-v1',
    cryptocompare='ETH',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AETH_V1)
A_AENJ_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x712DB54daA836B53Ef1EcBb9c6ba3b9Efb073F40'),
    decimals=18,
    name="Aave Interest bearing ENJ",
    symbol='aENJ',
    started=Timestamp(1594921488),
    swapped_for=None,
    coingecko='aave-enj',
    cryptocompare='ENJ',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AENJ_V1)
A_ADAI_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d'),
    decimals=18,
    name="Aave Interest bearing DAI",
    symbol='aDAI',
    started=Timestamp(1578501167),
    swapped_for=None,
    coingecko='aave-dai',
    cryptocompare='DAI',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ADAI_V1)
A_AUSDC_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9bA00D6856a4eDF4665BcA2C2309936572473B7E'),
    decimals=6,
    name="Aave Interest bearing USDC",
    symbol='aUSDC',
    started=Timestamp(1578501407),
    swapped_for=None,
    coingecko='aave-usdc',
    cryptocompare='USDC',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AUSDC_V1)
A_ASUSD_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x625aE63000f46200499120B906716420bd059240'),
    decimals=18,
    name="Aave Interest bearing SUSD",
    symbol='aSUSD',
    started=Timestamp(1578501472),
    swapped_for=None,
    coingecko='aave-susd',
    cryptocompare='sUSD',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ASUSD_V1)
A_ATUSD_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4DA9b813057D04BAef4e5800E36083717b4a0341'),
    decimals=18,
    name="Aave Interest bearing TUSD",
    symbol='aTUSD',
    started=Timestamp(1578501282),
    swapped_for=None,
    coingecko='aave-tusd',
    cryptocompare='TUSD',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ATUSD_V1)
A_AUSDT_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x71fc860F7D3A592A4a98740e39dB31d25db65ae8'),
    decimals=6,
    name="Aave Interest bearing USDT",
    symbol='aUSDT',
    started=Timestamp(1578501450),
    swapped_for=None,
    coingecko='aave-usdt',
    cryptocompare='USDT',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AUSDT_V1)
A_ABUSD_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6Ee0f7BB50a54AB5253dA0667B0Dc2ee526C30a8'),
    decimals=18,
    name="Aave Interest bearing Binance USD",
    symbol='aBUSD',
    started=Timestamp(1585230197),
    swapped_for=None,
    coingecko='aave-busd',
    cryptocompare='BUSD',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ABUSD_V1)
A_ABAT_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xE1BA0FB44CCb0D11b80F92f4f8Ed94CA3fF51D00'),
    decimals=18,
    name="Aave Interest bearing BAT",
    symbol='aBAT',
    started=Timestamp(1578501629),
    swapped_for=None,
    coingecko='aave-bat',
    cryptocompare='BAT',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ABAT_V1)
A_AKNC_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9D91BE44C06d373a8a226E1f3b146956083803eB'),
    decimals=18,
    name="Aave Interest bearing KNC",
    symbol='aKNC',
    started=Timestamp(1578501790),
    swapped_for=None,
    coingecko='aave-knc',
    cryptocompare='KNC',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AKNC_V1)
A_ALEND_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x7D2D3688Df45Ce7C552E19c27e007673da9204B8'),
    decimals=18,
    name="Aave Interest bearing LEND",
    symbol='aLEND',
    started=Timestamp(1578501530),
    swapped_for=None,
    coingecko='aave-lend',
    cryptocompare='LEND',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ALEND_V1)
A_AMANA_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6FCE4A401B6B80ACe52baAefE4421Bd188e76F6f'),
    decimals=18,
    name="Aave Interest bearing MANA",
    symbol='aMANA',
    started=Timestamp(1578502029),
    swapped_for=None,
    coingecko='aave-mana',
    cryptocompare='MANA',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AMANA_V1)
A_AMKR_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x7deB5e830be29F91E298ba5FF1356BB7f8146998'),
    decimals=18,
    name="Aave Interest bearing MKR",
    symbol='aMKR',
    started=Timestamp(1578502011),
    swapped_for=None,
    coingecko='aave-mkr',
    cryptocompare='MKR',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AMKR_V1)
A_AREP_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x71010A9D003445aC60C4e6A7017c1E89A477B438'),
    decimals=18,
    name="Aave Interest bearing REP",
    symbol='aREP',
    started=Timestamp(1578501835),
    swapped_for=None,
    coingecko='aave-rep',
    cryptocompare='REP',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AREP_V1)
A_AREN_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x69948cC03f478B95283F7dbf1CE764d0fc7EC54C'),
    decimals=18,
    name="Aave Interest bearing REN",
    symbol='aREN',
    started=Timestamp(1594923128),
    swapped_for=None,
    coingecko='aave-ren',
    cryptocompare='REN',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AREN_V1)
A_ASNX_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x328C4c80BC7aCa0834Db37e6600A6c49E12Da4DE'),
    decimals=18,
    name="Aave Interest bearing SNX",
    symbol='aSNX',
    started=Timestamp(1578502126),
    swapped_for=None,
    coingecko='aave-snx',
    cryptocompare='SNX',
    protocol=None,
)
CONSTANT_ASSETS.append(A_ASNX_V1)
A_AWBTC_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xFC4B8ED459e00e5400be803A9BB3954234FD50e3'),
    decimals=8,
    name="Aave Interest bearing WBTC",
    symbol='aWBTC',
    started=Timestamp(1578503540),
    swapped_for=None,
    coingecko='aave-wbtc',
    cryptocompare='WBTC',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AWBTC_V1)
A_AYFI_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x12e51E77DAAA58aA0E9247db7510Ea4B46F9bEAd'),
    decimals=18,
    name="Aave Interest bearing YFI",
    symbol='aYFI',
    started=Timestamp(1598605878),
    swapped_for=None,
    coingecko='ayfi',
    cryptocompare='YFI',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AYFI_V1)
A_AZRX_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6Fb0855c404E09c47C3fBCA25f08d4E41f9F062f'),
    decimals=18,
    name="Aave Interest bearing ZRX",
    symbol='aZRX',
    started=Timestamp(1578502051),
    swapped_for=None,
    coingecko='aave-zrx',
    cryptocompare='ZRX',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AZRX_V1)
A_AAAVE_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xba3D9687Cf50fE253cd2e1cFeEdE1d6787344Ed5'),
    decimals=18,
    name="Aave Interest bearing Aave Token",
    symbol='aAAVE',
    started=Timestamp(1603204313),
    swapped_for=None,
    coingecko='aave',
    cryptocompare='AAVE',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AAAVE_V1)
A_AUNI_V1 = EthereumToken.initialize(
    address=string_to_ethereum_address('0xB124541127A0A657f056D9Dd06188c4F1b0e5aab'),
    decimals=18,
    name="Aave Interest bearing Uniswap",
    symbol='aUNI',
    started=Timestamp(1603718736),
    swapped_for=None,
    coingecko='uniswap',
    cryptocompare='UNI',
    protocol=None,
)
CONSTANT_ASSETS.append(A_AUNI_V1)

# compound tokens -- TODO: Can also be handled programmatically
A_CDAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643'),
    decimals=8,
    name="Compound DAI",
    symbol='cDAI',
    started=Timestamp(1574471013),
    swapped_for=None,
    coingecko='cdai',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CDAI)
A_CUSDC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x39AA39c021dfbaE8faC545936693aC917d5E7563'),
    decimals=8,
    name="Compound USD Coin",
    symbol='cUSDC',
    started=Timestamp(1557192331),
    swapped_for=None,
    coingecko='compound-usd-coin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CUSDC)
A_CUSDT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9'),
    decimals=8,
    name="Compound USDT",
    symbol='cUSDT',
    started=Timestamp(1586985186),
    swapped_for=None,
    coingecko='compound-usdt',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CUSDT)
A_CBAT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E'),
    decimals=8,
    name="Compound BAT",
    symbol='cBAT',
    started=Timestamp(1557192085),
    swapped_for=None,
    coingecko='compound-basic-attention-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CBAT)
A_CETH = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
    decimals=8,
    name="Compound ETH",
    symbol='cETH',
    started=Timestamp(1557192318),
    swapped_for=None,
    coingecko='compound-ether',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CETH)
A_CREP = EthereumToken.initialize(
    address=string_to_ethereum_address('0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1'),
    decimals=8,
    name="Compound Augur",
    symbol='cREP',
    started=Timestamp(1557192288),
    swapped_for=None,
    coingecko='compound-augur',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CREP)
A_CWBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xC11b1268C1A384e55C48c2391d8d480264A3A7F4'),
    decimals=8,
    name="Compound Wrapped BTC",
    symbol='cWBTC',
    started=Timestamp(1563263257),
    swapped_for=None,
    coingecko='compound-wrapped-btc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CWBTC)
A_CZRX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407'),
    decimals=8,
    name="Compound 0x",
    symbol='cZRX',
    started=Timestamp(1557192054),
    swapped_for=None,
    coingecko='compound-0x',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_CZRX)


# Special tokens for defi price inquiry -- these should end up in programmatic rules
# after being upgraded to include, protocol (to identify the program to run on them)
# and underlying assets
A_3CRV = EthereumToken.initialize(
    address=string_to_ethereum_address('0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
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
A_YV1_DAIUSDCTBUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x2994529C0652D127b7842094103715ec5299bBed'),
    decimals=18,
    name="yearn Curve.fi yDAI/yUSDC/yUSDT/yBUSD",
    symbol='yyDAI+yUSDC+yUSDT+yBUSD',
    started=Timestamp(1598095312),
    swapped_for=None,
    coingecko='lp-bcurve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_DAIUSDCTBUSD)
A_CRVP_DAIUSDCTBUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x3B3Ac5386837Dc563660FB6a0937DFAa5924333B'),
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
A_YV1_DAIUSDCTTUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'),
    decimals=18,
    name="yearn Curve.fi yDAI/yUSDC/yUSDT/yTUSD",
    symbol='yyDAI+yUSDC+yUSDT+yTUSD',
    started=Timestamp(1596091760),
    swapped_for=None,
    coingecko='yvault-lp-ycurve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_DAIUSDCTTUSD)
A_CRVP_DAIUSDCTTUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
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
A_CRVP_RENWSBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3'),
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
A_YV1_RENWSBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6'),
    decimals=18,
    name="yearn Curve.fi renBTC/wBTC/sBTC",
    symbol='ycrvRenWSBTC',
    started=Timestamp(1598421792),
    swapped_for=None,
    coingecko='lp-renbtc-curve',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_RENWSBTC)
A_CRV_RENWBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x49849C98ae39Fff122806C06791Fa73784FB3675'),
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
A_CRV_YPAX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xD905e2eaeBe188fc92179b6350807D8bd91Db0D8'),
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
A_CRV_GUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0xD2967f45c4f384DEEa880F807Be904762a3DeA07'),
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
A_CRV_3CRV = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),
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
A_YV1_3CRV = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9cA85572E6A3EbF24dEDd195623F188735A5179f'),
    decimals=18,
    name="yearn Curve.fi DAI/USDC/USDT",
    symbol='y3Crv',
    started=Timestamp(1602322413),
    swapped_for=None,
    coingecko='curve-dao-token',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_3CRV)
A_CRV_3CRVSUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0xC25a3A3b969415c80451098fa907EC722572917F'),
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
A_YV1_ALINK = EthereumToken.initialize(
    address=string_to_ethereum_address('0x29E240CFD7946BA20895a7a02eDb25C210f9f324'),
    decimals=18,
    name="yearn Aave Interest bearing LINK",
    symbol='yaLINK',
    started=Timestamp(1596628700),
    swapped_for=None,
    coingecko='aave-link',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_ALINK)
A_YV1_DAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952'),
    decimals=18,
    name="yearn Dai Stablecoin",
    symbol='yDAI',
    started=Timestamp(1597301808),
    swapped_for=None,
    coingecko='dai',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_DAI)
A_YV1_WETH = EthereumToken.initialize(
    address=string_to_ethereum_address('0xe1237aA7f535b0CC33Fd973D66cBf830354D16c7'),
    decimals=18,
    name="yearn Wrapped Ether",
    symbol='yWETH',
    started=Timestamp(1598952738),
    swapped_for=None,
    coingecko='weth',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_WETH)
A_YV1_YFI = EthereumToken.initialize(
    address=string_to_ethereum_address('0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1'),
    decimals=18,
    name="yearn yearn.finance",
    symbol='yYFI',
    started=Timestamp(1597845648),
    swapped_for=None,
    coingecko='yearn-finance',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_YFI)
A_YV1_USDT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x2f08119C6f07c006695E079AAFc638b8789FAf18'),
    decimals=6,
    name="yearn Tether USD",
    symbol='yUSDT',
    started=Timestamp(1597318993),
    swapped_for=None,
    coingecko='tether',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_USDT)
A_YV1_USDC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x597aD1e0c13Bfe8025993D9e79C69E1c0233522e'),
    decimals=6,
    name="yearn USD//C",
    symbol='yUSDC',
    started=Timestamp(1595721600),
    swapped_for=None,
    coingecko='usd-coin',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_USDC)
A_YV1_TUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x37d19d1c4E1fa9DC47bD1eA12f742a0887eDa74a'),
    decimals=18,
    name="yearn TrueUSD",
    symbol='yTUSD',
    started=Timestamp(1596678980),
    swapped_for=None,
    coingecko='true-usd',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_TUSD)
A_YV1_GUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0xec0d8D3ED5477106c6D4ea27D90a60e594693C90'),
    decimals=2,
    name="yearn Gemini dollar",
    symbol='yGUSD',
    started=Timestamp(1602827638),
    swapped_for=None,
    coingecko='gemini-dollar',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_YV1_GUSD)
A_FARM_USDC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xf0358e8c3CD5Fa238a29301d0bEa3D63A17bEdBE'),
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
A_FARM_USDT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x053c80eA73Dc6941F518a68E2FC52Ac45BDE7c9C'),
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
A_FARM_DAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0xab7FA2B2985BCcfC13c6D86b1D5A17486ab1e04C'),
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
A_FARM_TUSD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x7674622c63Bee7F46E86a4A5A18976693D54441b'),
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
A_FARM_WETH = EthereumToken.initialize(
    address=string_to_ethereum_address('0xFE09e53A81Fe2808bc493ea64319109B5bAa573e'),
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
A_FARM_WBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5d9d25c7C457dD82fc8668FFC6B9746b674d4EcB'),
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
A_FARM_RENBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xC391d1b08c1403313B0c28D47202DFDA015633C4'),
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
A_FARM_CRVRENWBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9aA8F427A17d6B0d91B6262989EdC7D45d6aEdf8'),
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
A_XRP = Asset.initialize(
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
A_ADA = Asset.initialize(
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
A_DOT = Asset.initialize(
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
A_LTC = Asset.initialize(
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
A_EOS = Asset.initialize(
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
A_XLM = Asset.initialize(
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
A_GRT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xc944E90C64B2c07662A292be6244BDf05Cda44a7'),
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
A_PMGT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xAFFCDd96531bCd66faED95FC61e443D08F79eFEf'),
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
A_OMG = EthereumToken.initialize(
    address=string_to_ethereum_address('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'),
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

A_AUD = Asset.initialize(
    identifier='AUD',
    asset_type=AssetType.FIAT,
    name="Australian Dollar",
    symbol='AUD',
    started=None,
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_AUD)
A_NZD = Asset.initialize(
    identifier='NZD',
    asset_type=AssetType.FIAT,
    name="New Zealand Dollar",
    symbol='NZD',
    started=None,
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_NZD)
A_SGD = Asset.initialize(
    identifier='SGD',
    asset_type=AssetType.FIAT,
    name="Singapore Dollar",
    symbol='SGD',
    started=None,
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_SGD)

# Needed by cryptocompare.py
A_KRW = Asset.initialize(
    identifier='KRW',
    asset_type=AssetType.FIAT,
    name="Korean won",
    symbol='KRW',
    started=None,
    forked=None,
    swapped_for=None,
    coingecko=None,
    cryptocompare=None,
)
CONSTANT_ASSETS.append(A_KRW)

# Needed by airdrops.py
A_CVX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'),
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

# Needed by loopring.py
A_HT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6f259637dcD74C767781E37Bc6133cd6A68aa161'),
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
A_OKB = EthereumToken.initialize(
    address=string_to_ethereum_address('0x75231F58b43240C9718Dd58B4967c5114342a86c'),
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
A_KEEP = EthereumToken.initialize(
    address=string_to_ethereum_address('0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC'),
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
A_DXD = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa1d65E8fB6e87b60FECCBc582F7f97804B725521'),
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
_CETH_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5_swappedfor = Asset.initialize(
    identifier='_ceth_0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0',
    asset_type=AssetType.ETHEREUM_TOKEN,
    name="Tellor",
    symbol='TRB',
    started=Timestamp(1613850551),
    forked=None,
    swapped_for=None,
    coingecko='tellor',
    cryptocompare='TRB',
)
CONSTANT_ASSETS.append(_CETH_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5_swappedfor)
A_TRB = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0Ba45A8b5d5575935B8158a88C631E9F9C95a2e5'),
    decimals=18,
    name="Tellor Tributes",
    symbol='TRB',
    started=Timestamp(1564671864),
    swapped_for=_CETH_0X0BA45A8B5D5575935B8158A88C631E9F9C95A2E5_swappedfor,
    coingecko='tellor',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_TRB)
A_AUC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xc12d099be31567add4e4e4d0D45691C3F58f5663'),
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
A_RPL = EthereumToken.initialize(
    address=string_to_ethereum_address('0xB4EFd85c19999D84251304bDA99E90B92300Bd93'),
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
A_GNO = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6810e776880C02933D47DB1b9fc05908e5386b96'),
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
A_BNT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1F573D6Fb3F13d689FF844B4cE37794d79a7FF1C'),
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
A_PBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5228a22e72ccC52d415EcFd199F99D0665E7733b'),
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
A_PNT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'),
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
A_GRID = EthereumToken.initialize(
    address=string_to_ethereum_address('0x12B19D3e2ccc14Da04FAe33e63652ce469b3F2FD'),
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
A_PNK = EthereumToken.initialize(
    address=string_to_ethereum_address('0x93ED3FBe21207Ec2E8f2d3c3de6e058Cb73Bc04d'),
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
A_NEST = EthereumToken.initialize(
    address=string_to_ethereum_address('0x04abEdA201850aC0124161F037Efd70c74ddC74C'),
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
A_BTU = EthereumToken.initialize(
    address=string_to_ethereum_address('0xb683D83a532e2Cb7DFa5275eED3698436371cc9f'),
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
A_VBZRX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xB72B31907C1C95F3650b64b2469e08EdACeE5e8F'),
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
A_NMR = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671'),
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
A_SNT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x744d70FDBE2Ba4CF95131626614a1763DF805B9E'),
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
A_MTA = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
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
A_ONG = EthereumToken.initialize(
    address=string_to_ethereum_address('0xd341d1680Eeee3255b8C4c75bCCE7EB57f144dAe'),
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
A_GRG = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4FbB350052Bca5417566f188eB2EBCE5b19BC964'),
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
A_QCAD = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4A16BAf414b8e637Ed12019faD5Dd705735DB2e0'),
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
A_TON = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6a6c2adA3Ce053561C2FbC3eE211F23d9b8C520a'),
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
A_BAND = EthereumToken.initialize(
    address=string_to_ethereum_address('0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55'),
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
A_UMA = EthereumToken.initialize(
    address=string_to_ethereum_address('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'),
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
A_WNXM = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0d438F3b5175Bebc262bF23753C1E53d03432bDE'),
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
A_ENTRP = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5BC7e5f0Ab8b2E10D2D0a3F21739FCe62459aeF3'),
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
A_NIOX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xc813EA5e3b48BEbeedb796ab42A30C5599b01740'),
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
A_OGN = EthereumToken.initialize(
    address=string_to_ethereum_address('0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26'),
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
A_HEX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39'),
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
A_HBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0316EB71485b0Ab14103307bf65a021042c6d380'),
    decimals=18,
    name="Huobi BTC ",
    symbol='HBTC',
    started=Timestamp(1575863326),
    swapped_for=None,
    coingecko='huobi-btc',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_HBTC)
A_PLTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x5979F50f1D4c08f9A53863C2f39A7B0492C38d0f'),
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
A_FIN = EthereumToken.initialize(
    address=string_to_ethereum_address('0x054f76beED60AB6dBEb23502178C52d6C5dEbE40'),
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
A_DOUGH = EthereumToken.initialize(
    address=string_to_ethereum_address('0xad32A8e6220741182940c5aBF610bDE99E737b2D'),
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
A_DEFI_L = EthereumToken.initialize(
    address=string_to_ethereum_address('0x78F225869c08d478c34e5f645d07A87d3fe8eb78'),
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
A_DEFI_S = EthereumToken.initialize(
    address=string_to_ethereum_address('0xaD6A626aE2B43DCb1B39430Ce496d2FA0365BA9C'),
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
A_TRYB = EthereumToken.initialize(
    address=string_to_ethereum_address('0x2C537E5624e4af88A7ae4060C022609376C8D0EB'),
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
A_CEL = EthereumToken.initialize(
    address=string_to_ethereum_address('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d'),
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
A_AMP = EthereumToken.initialize(
    address=string_to_ethereum_address('0xfF20817765cB7f73d4bde2e66e067E58D11095C2'),
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
A_KP3R = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44'),
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
A_AC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x9A0aBA393aac4dFbFf4333B06c407458002C6183'),
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
A_CVT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xBe428c3867F05deA2A89Fc76a102b544eaC7f772'),
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
A_WOO = EthereumToken.initialize(
    address=string_to_ethereum_address('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'),
    decimals=18,
    name="Wootrade Network",
    symbol='WOO',
    started=Timestamp(1602855151),
    swapped_for=None,
    coingecko='wootrade-network',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_WOO)
A_BEL = EthereumToken.initialize(
    address=string_to_ethereum_address('0xA91ac63D040dEB1b7A5E4d4134aD23eb0ba07e14'),
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
A_OBTC = EthereumToken.initialize(
    address=string_to_ethereum_address('0x8064d9Ae6cDf087b1bcd5BDf3531bD5d8C537a68'),
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
A_INDEX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x0954906da0Bf32d5479e25f46056d22f08464cab'),
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
A_TTV = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa838be6E4b760E6061D4732D6B9F11Bf578f9A76'),
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
A_FARM = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa0246c9032bC3A600820415aE600c6388619A14D'),
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
A_BOR = EthereumToken.initialize(
    address=string_to_ethereum_address('0x3c9d6c1C73b31c837832c72E04D3152f051fc1A9'),
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
A_RFOX = EthereumToken.initialize(
    address=string_to_ethereum_address('0xa1d6Df714F91DeBF4e0802A542E13067f31b8262'),
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
A_NEC = EthereumToken.initialize(
    address=string_to_ethereum_address('0xCc80C051057B774cD75067Dc48f8987C4Eb97A5e'),
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
A_RGT = EthereumToken.initialize(
    address=string_to_ethereum_address('0xD291E7a03283640FDc51b121aC401383A46cC623'),
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
A_VSP = EthereumToken.initialize(
    address=string_to_ethereum_address('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421'),
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
A_SMARTCREDIT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x72e9D9038cE484EE986FEa183f8d8Df93f9aDA13'),
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
A_RAI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919'),
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
A_TEL = EthereumToken.initialize(
    address=string_to_ethereum_address('0x467Bccd9d29f223BcE8043b84E8C8B282827790F'),
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
A_BCP = EthereumToken.initialize(
    address=string_to_ethereum_address('0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14'),
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
A_BADGER = EthereumToken.initialize(
    address=string_to_ethereum_address('0x3472A5A71965499acd81997a54BBA8D852C6E53d'),
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
A_SUSHI = EthereumToken.initialize(
    address=string_to_ethereum_address('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2'),
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
A_MASK = EthereumToken.initialize(
    address=string_to_ethereum_address('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'),
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
A_YPIE = EthereumToken.initialize(
    address=string_to_ethereum_address('0x17525E4f4Af59fbc29551bC4eCe6AB60Ed49CE31'),
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
A_FUSE = EthereumToken.initialize(
    address=string_to_ethereum_address('0x970B9bB2C0444F5E81e9d0eFb84C8ccdcdcAf84d'),
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
A_SX = EthereumToken.initialize(
    address=string_to_ethereum_address('0x99fE3B1391503A1bC1788051347A1324bff41452'),
    decimals=18,
    name="SportX",
    symbol='SX',
    started=Timestamp(1610747210),
    swapped_for=None,
    coingecko='sportx',
    cryptocompare=None,
    protocol=None,
)
CONSTANT_ASSETS.append(A_SX)
A_RSPT = EthereumToken.initialize(
    address=string_to_ethereum_address('0x016bf078ABcaCB987f0589a6d3BEAdD4316922B0'),
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
