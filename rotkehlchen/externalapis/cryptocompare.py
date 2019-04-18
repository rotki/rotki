import glob
import logging
import os
import re
import time
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, NamedTuple, NewType

from rotkehlchen.assets import Asset
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.errors import PriceQueryUnknownFromAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath, Price, Timestamp
from rotkehlchen.utils import (
    convert_to_int,
    request_get_dict,
    rlk_jsondumps,
    rlk_jsonloads,
    rlk_jsonloads_dict,
    ts_now,
    tsToDate,
    write_history_data_in_file,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


WORLD_TO_CRYPTOCOMPARE = {
    'RDN': 'RDN*',
    'DATAcoin': 'DATA',
    'IOTA': 'IOT',
    'XRB': 'NANO',
    'AIR-2': 'AIR*',
    'BITS-2': 'BITS*',
    'BTM-2': 'BTM*',
    # In Rotkehlchen CCN-2 is Cannacoin and CCN is CustomContractNetwork
    'CCN-2': 'CCN',
    # In Rotkehlchen FAIR-2 is FairGame and FAIR is FairCoin
    'FAIR-2': 'FAIR*',
    # Almosst 100% certain that GPUC (https://coinmarketcap.com/currencies/gpucoin/)
    # is GPU in cryptocompare (https://www.cryptocompare.com/coins/gpu/overview)
    'GPUC': 'GPU',
    # In Rotkehlchen we got 3 coins with KEY symbol. Cryptocompare does not have
    # data for KEY-2
    # KEY -> Selfkey
    # KEY-2 -> KEY
    # KEY-3 -> KeyCoin
    'KEY-3': 'KEY*',
    # In Rotkehlchen KNC is KyberNetwork and KNC-2 is KingN coin. In cryptocompare
    # KNC** is KingN coin
    'KNC-2': 'KNC**',
    # Liquidity network is LQD in Rotkehlchen but LQDN in Cryptocompare
    'LQD': 'LQDN',
    # Monetaverde is as MNV in cryptocompare while it should be MCN
    # https://www.cryptocompare.com/coins/mnv/overview
    'MCN': 'MNV',
    # Marscoin is as MRS in cryptocompare
    # https://www.cryptocompare.com/coins/mrs/overview
    'MARS': 'MRS',
    # Marginless is not in cryptocompare. Asking for MRS will return MARScoin
    'MRS': None,
    # Mazacoin is as MZC in cryptocompare
    'MAZA': 'MZC',
    # NuBits is NBT in cryptocompare
    'USNBT': 'NBT',
    # Polymath is POLY in Rotkehlchen and POLY* in cryptocompare
    'POLY': 'POLY*',
    # Polybit is POLY-2 in Rotkehlchen and POLY in cryptocompare
    'POLY-2': 'POLY',
    # Steem dollars are SBD* in cryptocompare
    'SBD': 'SBD*',
    # YacCoin is YAC in cryptocompare
    'YACC': 'YAC',
    # GoldCoin is GLD in cryptocompare, but GLC in most other places including Rotkehlcen
    'GLC': 'GLD',
    # In Rotkehlchen we have GlobalCoin as GLC-2. In Cryptocompare it's GLC
    'GLC-2': 'GLC',
    # In Rotkehlchen and everywhere else Bitbean is BITB but in cryptocompare BEAN
    'BITB': 'BEAN',
    # For Rotkehlchen RCN is Ripio Credit Network and RCN-2 is Rcoin
    # Rcoin is RCN* in cryptocompare
    'RCN-2': 'RCN*',
    # Metronome is MET in Rotkehlchen and MET* in cryptocompare
    'MET': 'MET*',
    # EDR is Endor Protocol in Rotkehlchen and EDR* in cryptocompare
    'EDR': 'EDR*',
    # EDR-2 is E-Dinar coin in Rotkehlchen and EDR in cryptocompare
    'EDR-2': 'EDR',
    # SPC is Spacechain in Rotkehlchen but SPC* in cryptocompare.
    'SPC': 'SPC*',
    # Blocktrade is BTT-2 in Rotkehlchen but BKT in cryptocompare.
    'BTT-2': 'BKT',
    # Ontology gas is ONG in Rotkehlchen but ONGAS in cryptocompare
    'ONG': 'ONGAS',
    # SoMee.Social is ONG-2 in Rotkehlchen but ONG in cryptocompare
    'ONG-2': 'ONG',
    # SLT is Smartlands in Rotkehlchen but SLST in cryptocompare
    'SLT': 'SLST',
    # SLT-2 is Social Lending Network in Rotkehlchen but SLT in cryptocompare
    'SLT-2': 'SLT',
    # PAI is Project Pai in Rotkehlchen but PAI* in cryptocompare
    'PAI': 'PAI*',
    # PAI-2 is PCHAIN in Rotkehlchen but PAI in cryptocompare
    'PAI-2': 'PAI',
    # CMT-2 is CometCoin in Rotkehlchen but CMTC in cryptocompare
    'CMT-2': 'CMTC',
    # GXChain is GXC in Rotkehlcen and GXS in cryptocompare
    'GXC': 'GXS',
    # Harvest Masternode Coin is in HC-2 in Rotkehlchen and HMN in cryptocompare
    'HC-2': 'HMN',
    # For Rotkehlchen HOT is Holochain and HOT-2 is Hydro Protocol
    # But for cryptocompare HOT is Hydro Protocol and HOT* is HoloChain
    'HOT': 'HOT*',
    'HOT-2': 'HOT',
    # For Rotkehlchen RDN is Raiden Network Token but it's RDN* in cryptocompare
    'RDN': 'RDN*',
    # For Rotkehlchen YOYO is YOYOW but it's YOYOW in cryptocompare
    'YOYOW': 'YOYOW',
    # For Rotkehlchen 0xBTC is 0xBTC but in cryptocompare it's capitalized
    '0xBTC': '0XBTC',
    # For Rotkehlchen ACC is AdCoin, ACC-2 is ACChain and ACC-3 is Accelerator network
    # In cryptocompare Accelerator Network is ACC*
    'ACC-3': 'ACC*',
    # For Rotkehlchen ARB is Arbitrage coin and ARB-2 is ARbit but in cryptocompare
    # ARB* is arbitrage and ARB is ARbit
    'ARB': 'ARB*',
    'ARB-2': 'ARB',
    # For Rotkehlchen ARC is Advanced Technology Coin (Arctic) and ARC-2 is ArcadeCity
    # In Cryptocompare ARC* is ArcadeCity
    'ARC-2': 'ARC*',
    # For Rotkehlchen ATX is Astoin Coin and ATX-2 is ArtexCoin but in
    # cryptocompare ATX* is Astoin Coin and ATX is ArtexCoin
    'ATX': 'ATX*',
    'ATX-2': 'ATX',
    # For Rotkehlchen AVA is Travala and AVA-2 is Avalon but in
    # cryptocompare AVALA is Travala and AVA is Avalon
    'AVA': 'AVALA',
    'AVA-2': 'AVA',
    # Symbol for B2BX is B2B is cryptocompare so we need to specify it
    'B2BX': 'B2B',
    # For Rotkehlchen BBK is BrickBlock and BBK-2 is Bitblocks but in cryptocompare
    # BrickBlock is XBB and Bitblocks is BBK
    'BBK': 'XBB',
    'BBK-2': 'BBK',
    # For Rotkehlchen BBN is Banyan Network but in cryptocompare it's BBN*
    'BBN': 'BBN*',
    # For Rotkehlchen BET is Dao.Casino and BET-2 is BetaCoin but in cryptocompare
    # Dao.Caisno is BET* and BetaCoin is BET
    'BET': 'BET*',
    'BET-2': 'BET',
    # Bollenum (https://coinmarketcap.com/currencies/bolenum/) is BLN
    # in rotkehlchen but BLN* in cryptocompare
    'BLN': 'BLN*',
    # ContentBox (https://coinmarketcap.com/currencies/contentbox/) is BOX-2
    # in rotkehlchen but BOX in cryptocompare
    'BOX-2': 'BOX',
    # Bytether (https://www.cryptocompare.com/coins/byther/overview) is BTH
    # in rotkehlchen but BYTHER in cryptocompare
    'BTH': 'BYTHER',
    # Bither (https://www.cryptocompare.com/coins/btr/overview) is BTR-2
    # in rotkehlchen but BTR in cryptocompare
    'BTR-2': 'BTR',
    # For Rotkehlchen CAN is CanYaCoin and CAN-2 is Content And Ad Network
    # In cryptocompare, it's CAN and CAN*
    'CAN-2': 'CAN*',
    # For Rotkehlchen CAT is Bitclave and CAT-2 is BlockCAT but in cryptocompare
    # Bitclave is CAT* and BlockCAT is BCAT
    'CAT': 'CAT*',
    'CAT-2': 'BCAT',
    # For Rotkehlchen CET is CoinEX and CET-2 is DiceMoney but in cryptocompare
    # CoinEX is CET and DiceMoney is CET*
    'CET-2': 'CET*',
    # For Rotkehlchen CPC is CPChain and CPC-2 is CapriCoin but in cryptocompare
    # CPChain is CPC* and CapriCoin is CPC
    'CPC': 'CPC*',
    'CPC-2': 'CPC',
    # For Rotkehlchen CRC is CryCash and CRC-2 is CrowdCoin but in cryptocompare
    # Crycash is CRC** and CrowdCoin is CRC***
    'CRC': 'CRC**',
    'CRC-2': 'CRC***',
    # For Rotkehlchen CS is Credits but it's CS* in cryptocompare
    'CS': 'CS*',
    # For Rotkehlchen CTX-2 is CarTaxi but it's CTX in cryptocompare
    'CTX-2': 'CTX',
    # For Rotkehlchen DAV is DAV Token  but it's DAV* in cryptocompare
    'DAV': 'DAV*',
    # For Rotkehlchen DCC is Distributed Credit Chain but it's DCC* in cryptocompare
    'DCC': 'DCC*',
    # For Rotkehlchen DOW is DOW Coin Chain but it's Dow in cryptocompare
    'DOW': 'Dow',
    # For Rotkehlchen EPY is Emphy Coin but it's EPY* in cryptocompare
    'EPY': 'EPY*',
    # For Rotkehlchen ERT is Eristica Coin but it's ERT* in cryptocompare
    'ERT': 'ERT*',
    # For Rotkehlchen EVN is Envion and EVN-2 is EvenCoin, but in cryptocompare
    # Evencoin is EVN*
    'EVN-2': 'EVN*',
    # For Rotkehlchen EXC is ExcaliburCoin and EXC-2 is EximChain Token but in
    # cryptocompare EXC is EximChain Token ans ExcaliburCoin is not supported
    'EXC-2': 'EXC',
    # For Rotkehlchen FLX is Bitflux but it's FLX* in cryptocompare
    'FLX': 'FLX*',
    # For Rotkehlchen FORK is ForkCoin and FORK-2 is GastroAdvisor. For
    # cryptocompare only GastroAdvisor exists as FORK.
    'FORK-2': 'FORK',
    # For Rotkehlchen GBX is GoByte and GBX-2 is Globitex but in cryptocompare
    # Globitex is GBXT
    'GBX-2': 'GBXT',
    # For Rotkehlchen GEN is Daostack but it's GEN* in cryptocompare
    'GEN': 'GEN*',
    # For Rotkehlchen GENE is ParkGene and GENE-2 is Gene Source Code Chain,
    # in cryptocompare GENE-2 is GENE*
    'GENE-2': 'GENE*',
    # For Rotkehlchen GOT is Go Network Token and GOT-2 is ParkinGo, cryptocompare
    # does not have ParkinGO and Go Network Token is GOT*
    'GOT': 'GOT*',
    # For Rotkehlchen HMC is Hi Mutual Society and HMC-2 is Harmony Coin, in
    # cryptocompare HMC is the same but HMC* is (perhaps) Harmony Coin
    'HMC-2': 'HMC*',
    # For Rotkehlchen INV is Invacio but it's INV* in cryptocompare
    'INV': 'INV*',
    # For Rotkehlchen JOY is Joy but it's INV* in cryptocompare
    'JOY': 'JOY*',
    # For Rotkehlchen LNC is Blocklancer  and LNC-2 is Linker Coin, but for
    # cryptocompare linker coin is LNC*
    'LNC-2': 'LNC*',
    # For Rotkehlchen LOC is LockTrip but in cryptocompare it's LOC*
    'LOC': 'LOC*',
    # For Rotkehlchen MAN is Matrix AI Network but in cryptocompare it's MAN*
    'MAN': 'MAN*',
    # For Rotkehlchen MDT is Measurable Data Token but in cryptocompare it's MDT*
    'MDT': 'MDT*',
    # For Rotkehlchen MNT is Media Network Token but in cryptocompare it's MNT*
    'MNT': 'MNT*',
    # For Rotkehlchen MRP is MoneyReel but in cryptocompare it's MRP*
    'MRP': 'MRP*',
    # For Rotkehlchen MTC is doc.com Token and MTC-2 is Mesh Network but in
    # cryptocompare Mesh Network is MTCMN
    'MTC-2': 'MTCMN',
    # For Rotkehlchen MTN is Medical Token but it's MTN* in cryptocompare
    'MTN': 'MTN*',
    # For Rotkehlchen NEC is Ethfinex Nectar Token but it's NEC* in cryptocompare
    'NEC': 'NEC*',
    # For Rotkehlchen NIO is Autonio but it's NIO* in cryptocompare
    'NIO': 'NIO*',
    # For Rotkehlchen OCC-2 is Original Cryptocoin but it's OCC in cryptocompare
    'OCC-2': 'OCC',
    # For Rotkehlchen ORS is OriginSport Token and ORS-2 is ORS group, but in
    # cryptocompare OriginSport Token is ORS* and ORS Group is ORS
    'ORS': 'ORS*',
    'ORS-2': 'ORS',
    # For Rotkehlchen PRE is Presearch but it's PRE* in cryptocompare
    'PRE': 'PRE*',
    # For Rotkehlchen RDN is Raiden Network but it's RDN* in cryptocompare
    'RDN': 'RDN*',
    # For Rotkehlchen Sharpe Platform Token is SHP but it's SHP* in cryptocompare
    'SHP': 'SHP*',
    # For Rotkehlchen SKB is SakuraBloom but it's SKB* in cryptocompare
    'SKB': 'SKB*',
    # For Rotkehlchen SKR is SkrillaToken but it's SKR* in cryptocompare
    'SKR': 'SKR*',
    # For Rotkehlchen SMART is SmartCash, and SMART-2 is SmartBillions, but in
    # cryptocompare SmartBillions is SMART*
    'SMART-2': 'SMART*',
    # For Rotkehlchen SMT is SmartMesh but it's SMT* in cryptocompare
    'SMT': 'SMT*',
    # For Rotkehlchen SOUL is Phantasma and SOUL-2 is CryptoSoul. But cryptocompare
    # only has Phantasma as SOUL*
    'SOUL': 'SOUL*',
    # For Rotkehlchen SPD is Spindle and SPD-2 is Stipend, but in cryptocompare
    # Spindle is SPD* and Stipend is SPD
    'SPD': 'SPD*',
    'SPD-2': 'SPD',
    # For Rotkehlchen SPN is Sapien Network but it's SPN* in cryptocompare
    'SPN': 'SPN*',
    # For Rotkehlchen SPX is Sp8de Token but it's SPX* in cryptocompare
    'SPX': 'SPX*',
    # For Rotkehlchen STRC is Star Credits but it's SRC* in cryptocompare
    'STRC': 'SRC*',
    # For Rotkehlchen TCH is ThoreCash and TCH-2 is TigerCash but cryptocompare
    # only has TigerCash as TCH
    'TCH-2': 'TCH',
    # For Rotkehlchen TEAM is TokenStars Team but cryptocompare has it as TEAMT
    'TEAM': 'TEAMT',
    # For Rotkehlchen TMT is Traxia Membership Token but it's TMT** in cryptocompare
    'TMT': 'TMT**',
    # For Rotkehlchen VSF is Verisafe but it's CPLO in cryptocompare (the old name)
    'VSF': 'CPLO',
    # For Rotkehlchen WEB is Webcoin and WEB-2 Webchain, but in cryptocompare
    # Webchain is WEB*
    'WEB-2': 'WEB*',
    # For Rotkehlchen WIN is Winchain Token and WIN-2 WCoin, but in cryptocompare
    # Wcoin is WIN and there is no Winchain Token
    'WIN-2': 'WIN',
    # For Rotkehlchen BlitzPredict is XBP  but it's XBP* in cryptocompare
    'XBP': 'XBP*',
}

# TODO: For the ones missing from cryptocompare make sure to also
# disallow price queries to cryptocompare for these assets
KNOWN_TO_MISS_FROM_CRYPTOCOMPARE = (
    # This is just kraken's internal fee token
    'KFEE',
    # For us ACH is the Altcoin Herald token. For cryptocompare it's
    # Achievecoin
    # https://www.cryptocompare.com/coins/ach/overview
    'ACH',
    # We got APH as Aphelion and APH-2 as a very shortlived Aphrodite coin
    # Cryptocompare has no data for Aphrodite coin
    'APH-2',
    # BTCTalkCoin is not in cryptocompare but it's in coin paprika
    # https://api.coinpaprika.com/v1/coins/talk-btctalkcoin and in coinmarketcap
    # https://coinmarketcap.com/currencies/btctalkcoin/#charts
    'TALK',
    # CCN is CustomContractNetwork in Rotkehlchen but Cannacoin in cryptocompare
    # and cryptocompare does not have data for CustomContractNetwork
    'CCN',
    # Dreamcoin (https://coinmarketcap.com/currencies/dreamcoin/#charts) is not
    # in cryptocompare.
    'DRM',
    # KEY (bihu) (https://coinmarketcap.com/currencies/key/) is not in
    # cryptocompare. But it's in paprika
    'KEY-2',
    # MRS (Marginless) is not in cryptocompare. There is a coin with that
    # symbol there, but it's the MARScoin
    'MRS',
    # PRcoin, known as PRC-2 in Rotkehlcen has no data in cryptocompare
    'PRC-2',
    # Wiki coin/token is not in cryptocompare but is in paprika wiki-wiki-token
    'WIKI',
    # More token (https://coinmarketcap.com/currencies/more-coin/) is not in
    # cryptocompare but is in paprika
    'MORE',
    # Mithril Ore token (https://coinmarketcap.com/currencies/mithril-ore/) is not in
    # cryptocompare but is in paprika
    'MORE-2',
    # Aidus Token (https://coinmarketcap.com/currencies/aidus-token/) is not in
    # cryptocompare but is in paprika
    'AID-2',
    # Cashbery coin (https://coinmarketcap.com/currencies/cashbery-coin/) is not
    # in cryptocompare but is in paprika
    'CBC-2',
    # Cyber movie chain (https://coinmarketcap.com/currencies/cyber-movie-chain/)
    # is not in cryptocompare but is in paprika
    'CMCT-2',
    # BOXX (https://coinmarketcap.com/currencies/blockparty-boxx-token/)
    # is not in cryptocompare but is in paprika
    'BOXX',
    # Moss (https://coinmarketcap.com/currencies/moss-coin/)
    # is not in cryptocompare but is in paprika
    'MOC',
    # Solve.care (https://coinmarketcap.com/currencies/solve/) is not
    # in cryptocompare but is in paprika
    'SOLVE',
    # Stronghold USD (https://coinmarketcap.com/currencies/stronghold-usd/)
    # is not in cryptocompare but is in paprika
    'USDS-2',
    # HXRO (https://coinmarketcap.com/currencies/hxro/)
    # is not in cryptocompare but is in paprika
    'HXRO',
    # SERV (https://coinmarketcap.com/currencies/serve/)
    # is not in cryptocompare but is in paprika
    'SERV',
    # TTC (https://coinmarketcap.com/currencies/ttc-protocol/)
    # is not in cryptocompare but is in paprika
    # There is a "titcoin" as TTC in cryptocompare but that is wrong
    # https://www.cryptocompare.com/coins/ttc/overview
    'TTC',
    # BlazeCoin (https://coinmarketcap.com/currencies/blazecoin/)
    # is not in cryptocompare but is in paprika
    'BLZ-2',
    # Bitgem (https://coinmarketcap.com/currencies/bitgem/)
    # is not in cryptocompare but is in paprika
    'BTG-2',
    # 1SG (https://coinmarketcap.com/currencies/1sg/)
    # is not in cryptocompare but is in paprika
    '1SG',
    # ACChain (https://coinmarketcap.com/currencies/acchain/)
    # is not in cryptocompare but is in paprika
    'ACC-2',
    # PolyAI (https://coinmarketcap.com/currencies/poly-ai/)
    # is not in cryptocompare but is in paprika
    'AI',
    # AiLink token (https://coinmarketcap.com/currencies/ailink-token/)
    # is not in cryptocompare but is in paprika
    'ALI',
    # Bankcoin BCash (https://bankcoinbcash.com/)
    # is not in cryptocompare but is in paprika
    'BCASH',
    # BitcapitalVendor (https://coinmarketcap.com/currencies/bitcapitalvendor/)
    # is not in cryptocompare but is in paprika
    'BCV',
    # BitPark (https://coinmarketcap.com/currencies/bitpark-coin/)
    # is not in cryptocompare but is in paprika
    'BITPARK',
    # BankCoin Cash (https://bankcoin-cash.com/)
    # is not in cryptocompare but is in paprika
    'BKC',
    # Bionic (https://coinmarketcap.com/currencies/bionic/)
    # is not in cryptocompare but is in paprika
    'BNC',
    # BrokerNekoNetwork (https://coinmarketcap.com/currencies/brokernekonetwork/)
    # is not in cryptocompare but is in paprika
    'BNN',
    # BoxToken (https://coinmarketcap.com/currencies/contentbox/)
    # is not in cryptocompare but is in paprika
    'BOX',
    # BitcoinOne (https://coinmarketcap.com/currencies/bitcoin-one/)
    # is not in cryptocompare but is in paprika
    'BTCONE',
    # BitcoinToken (https://coinmarketcap.com/currencies/bitcoin-token/)
    # is not in cryptocompare but is in paprika
    'BTK',
    # Bitether (https://coinmarketcap.com/currencies/bitether/)
    # is not in cryptocompare but is in paprika
    'BTR',
    # Blue whale token (https://coinmarketcap.com/currencies/blue-whale-token/)
    # is not in cryptocompare but is in paprika
    'BWX',
    # Carboneum (https://coinmarketcap.com/currencies/carboneum-c8-token/)
    # is not in cryptocompare but is in paprika
    'C8',
    # Cloudbrid (https://www.cloudbric.io/)
    # is not in cryptocompare but is in paprika
    'CLB',
    # CruiseBit (https://coinmarketcap.com/currencies/cruisebit/)
    # is not in cryptocompare but is in paprika
    'CRBT',
    # Cryptosolartech (https://coinmarketcap.com/currencies/cryptosolartech/)
    # is not in cryptocompare but is in paprika
    'CST',
    # Centauri (https://coinmarketcap.com/currencies/centauri/)
    # is not in cryptocompare but is in paprika
    'CTX',
    # CyberFM (https://coinmarketcap.com/currencies/cyberfm/)
    # is not in cryptocompare but is in paprika
    'CYFM',
    # CyberMusic (https://coinmarketcap.com/currencies/cybermusic/)
    # is not in cryptocompare but is in paprika
    'CYMT',
    # CanonChain (https://coinmarketcap.com/currencies/cononchain/)
    # is not in cryptocompare but is in paprika
    'CZR',
    # DACSEE (https://coinmarketcap.com/currencies/dacsee/)
    # is not in cryptocompare but is in paprika
    'DACS',
    # Dalecoin (https://coinmarketcap.com/currencies/dalecoin/)
    # is not in cryptocompare but is in paprika
    'DALC',
    # Digital Assets Exchange token
    # (https://coinmarketcap.com/currencies/digital-asset-exchange-token/)
    # is not in cryptocompare but is in paprika
    'DAXT',
    # Deltachain (https://coinmarketcap.com/currencies/delta-chain/)
    # is not in cryptocompare but is in paprika
    'DELTA',
    # Dew (https://coinmarketcap.com/currencies/dew/)
    # is not in cryptocompare but is in paprika
    'DEW',
    # DEX (https://coinmarketcap.com/currencies/dex/)
    # is not in cryptocompare but is in paprika
    'DEX',
    # DragonGlass (https://coinmarketcap.com/currencies/dragonglass/)
    # is not in cryptocompare but is in paprika
    'DGS',
    # DigitalInsuranceToken (https://coinmarketcap.com/currencies/digital-insurance-token/)
    # is not in cryptocompare but is in paprika
    'DIT',
    # DigitalTicks (https://www.coingecko.com/en/coins/digital-ticks) is not in
    # cryptocompate but is in paprika
    'DTX-2',
    # E4Row (https://coinmarketcap.com/currencies/ether-for-the-rest-of-the-world/) is not in
    # cryptocompare but is in paprika
    'E4ROW',
    # EAGLE (https://coinmarketcap.com/currencies/eaglecoin/) is not in
    # cryptocompare but is in paprika
    'EAGLE',
    # OpenSource university (https://os.university/) is not in
    # cryptocompare but is in paprika
    'EDU-2',
    # ExcaliburCoin  (https://coinmarketcap.com/currencies/excaliburcoin/) is not
    # in cryptocompare but is in paprika
    'EXC',
    # Fingerprint  (https://fingerprintcoin.org/) is not
    # in cryptocompare but is in paprika
    'FGP',
    # Formosa Fincial Token  (https://coinmarketcap.com/currencies/formosa-financial/)
    # is not in cryptocompare but is in paprika
    'FMF',
    # Fcoin token  (https://coinmarketcap.com/currencies/ftoken/)
    # is not in cryptocompare but is in paprika
    'FT-2',
    # Futurax (https://coinmarketcap.com/currencies/futurax/)
    # is not in cryptocompare but is in paprika
    'FTXT',
    # Flexacoin (https://coinmarketcap.com/currencies/flexacoin/)
    # is not in cryptocompare but is in paprika
    'FXC',
    # Themis GET (https://coinmarketcap.com/currencies/themis/)
    # is not in cryptocompare but is in paprika
    'GET-2',
    # ParkinGO (https://coinmarketcap.com/currencies/parkingo/)
    # is not in cryptocompare but is in paprika
    'GOT-2',
    # GSENetwork (https://coinmarketcap.com/currencies/gsenetwork/)
    # is not in cryptocompare but is in paprika
    'GSE',
    # Jury.Online Token (https://coinmarketcap.com/currencies/jury-online-token/)
    # is not in cryptocompare but is in paprika
    'JOT',
    # KanadeCoin (https://coinmarketcap.com/currencies/kanadecoin/)
    # is not in cryptocompare but is in paprika
    'KNDC',
    # KoraNetworkToken (https://coinmarketcap.com/currencies/kora-network-token/)
    # is not in cryptocompare but is in paprika
    'KNT',
    # Knekted (https://coinmarketcap.com/currencies/knekted/)
    # is not in cryptocompare but is in paprika
    'KNT-2',
    # 4NEW KWATT (https://coinmarketcap.com/currencies/4new/)
    # is not in cryptocompare but is in paprika
    'KWATT',
    # Liquorchain Token (https://etherscan.io/address/0x4A37A91eec4C97F9090CE66d21D3B3Aadf1aE5aD)
    # is not in cryptocompare but is in paprika
    'LCT-2',
    # LemoChain (https://coinmarketcap.com/currencies/lemochain/)
    # is not in cryptocompare but is in paprika
    'LEMO',
    # Linkey (https://coinmarketcap.com/currencies/linkey/)
    # is not in cryptocompare but is in paprika
    'LKY',
    # Lisk Machine Learning (https://coinmarketcap.com/currencies/lisk-machine-learning/)
    # is not in cryptocompare but is in paprika
    'LML',
    # Locus Chain (https://etherscan.io/address/0xC64500DD7B0f1794807e67802F8Abbf5F8Ffb054)
    # is not in cryptocompare but is in paprika
    'LOCUS',
    # Midas Protocol (https://coinmarketcap.com/currencies/midasprotocol/)
    # is not in cryptocompare but is in paprika
    'MAS',
    # Meshbox (https://coinlib.io/coin/MESH/MeshBox)
    # is not in cryptocompare but is in paprika
    'MESH',
    # Nami ICO (https://etherscan.io/address/0x8d80de8A78198396329dfA769aD54d24bF90E7aa)
    # is not in cryptocompate but is in paprika
    'NAC',
    # For Rotkehlchen NCC is neurochain and NCC-2 is NeedsCoin and neither of them
    # is in cryptocompare but they are both in paprika
    'NCC',
    'NCC-2',
    # NDEX (https://coinmarketcap.com/currencies/ndex/)
    # is not in cryptocompare but is in paprika
    'NDX',
    # NetKoin (https://coinmarketcap.com/currencies/netkoin/)
    # is not in cryptocompare but is in paprika
    'NTK-2',
    # Nuggets (https://coinmarketcap.com/currencies/nuggets/)
    # is not in cryptocompare but is in paprika
    'NUG',
    # OCtoin (https://coinmarketcap.com/currencies/octoin-coin/)
    # is not in cryptocompare but is in paprika
    'OCC',
    # OptiToken (https://coinmarketcap.com/currencies/optitoken/)
    # is not in cryptocompare but is in paprika
    'OPTI',
    # Wisepass (https://coinmarketcap.com/currencies/wisepass/)
    # is not in cryptocompare but is in paprika
    'PASS-2',
    # Kleros (https://coinmarketcap.com/currencies/kleros/)
    # is not in cryptocompare but is in paprika
    # Note: Cryptocompare has SteamPunk as PNK ...
    'PNK',
    # For Rotkehlchen POP is PopularCoin, and POP-2 is POP Chest Token, but in
    # cryptocompare POP Chest appears also as POP so I can only assume it's not
    # supported https://www.cryptocompare.com/coins/popc/overview
    'POP-2',
    # Foresting (https://coinmarketcap.com/currencies/pton/)
    # is not in cryptocompare but is in paprika
    'PTON',
    # Proton (https://coinmarketcap.com/currencies/proton-token/)
    # is not in cryptocompare but is in paprika. Cryptocompare has
    # Pink Taxi Token as PTT.
    'PTT',
    # Rublix (https://coinmarketcap.com/currencies/rublix/)
    # is not in cryptocompare but is in paprika
    'RBLX',
    # Red Token (https://coinmarketcap.com/currencies/red/)
    # is not in cryptocompare but is in paprika
    'RED',
    # Rusgas (https://coinmarketcap.com/currencies/rusgas/)
    # is not in cryptocompare but is in paprika
    'RGS',
    # RemiCoin (https://coinmarketcap.com/currencies/remicoin/)
    # is not in cryptocompare but is in paprika
    'RMC',
    # Rotharium (https://coinmarketcap.com/currencies/rotharium/)
    # is not in cryptocompare but is in paprika
    'RTH',
    # SmartApplicationChain (https://coinmarketcap.com/currencies/smart-application-chain/)
    # is not in cryptocompare but is in paprika
    'SAC',
    # snowball (https://etherscan.io/address/0x198A87b3114143913d4229Fb0f6D4BCb44aa8AFF)
    # is not in cryptocompare but is in paprika
    'SNBL',
    # Soniq (https://coinmarketcap.com/currencies/soniq/)
    # is not in cryptocompare but is in paprika
    'SONIQ',
    # CryptoSoul (https://coinmarketcap.com/currencies/cryptosoul/)
    # is not in cryptocompare but is in paprika
    'SOUL-2',
    # Staker (https://coinmarketcap.com/currencies/staker/)
    # is not in cryptocompare but is in paprika
    'STR',
    # TigerCash (https://coinmarketcap.com/currencies/tigercash/)
    # is not in cryptocompare but is in paprika
    'TCH',
    # TercetNetwork (https://etherscan.io/address/0x28d7F432d24ba6020d1cbD4f28BEDc5a82F24320)
    # is not in cryptocompare but is in paprika
    'TCNX',
    # ThingsChain (https://coinmarketcap.com/currencies/thingschain/)
    # is not in cryptocompare but is in paprika
    'TIC',
    # Tokok (https://coinmarketcap.com/currencies/tokok/)
    # is not in cryptocompare but is in paprika
    'TOK',
    # Uchain (https://coinmarketcap.com/currencies/uchain/)
    # is not in cryptocompare but is in paprika
    'UCN',
    # Bitcoin Card (https://etherscan.io/address/0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D)
    # is not in cryptocompare but is in paprika
    'VD',
    # VeriDocGlobal (https://coinmarketcap.com/currencies/veridocglobal/)
    # is not in cryptocompare but is in paprika
    'VDG',
    # Vikky Token (https://coinmarketcap.com/currencies/vikkytoken/)
    # is not in cryptocompare but is in paprika
    'VIKKY',
    # Wibson (https://coinmarketcap.com/currencies/wibson/)
    # is not in cryptocompare but is in paprika
    'WIB',
    # Winchain Token (https://coinmarketcap.com/currencies/wintoken/)
    # is not in cryptocompare but is in paprika
    'WIN',
    # Yggdrash (https://coinmarketcap.com/currencies/yeed/)
    # is not in cryptocompare but is in paprika
    'YEED',
    # ZeusNetwork (https://coinmarketcap.com/currencies/zeusnetwork/)
    # is not in cryptocompare but is in paprika
    'ZEUS',
)

T_PairCacheKey = str
PairCacheKey = NewType('PairCacheKey', T_PairCacheKey)


class PriceHistoryEntry(NamedTuple):
    time: Timestamp
    low: Price
    high: Price


class PriceHistoryData(NamedTuple):
    data: List[PriceHistoryEntry]
    start_time: Timestamp
    end_time: Timestamp


class NoPriceForGivenTimestamp(Exception):
    def __init__(self, from_asset, to_asset, timestamp):
        super(NoPriceForGivenTimestamp, self).__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset, to_asset, timestamp,
            ),
        )


def _dict_history_to_entries(data: List[Dict[str, Any]]) -> List[PriceHistoryEntry]:
    """Turns a list of dict of history entries to a list of proper objects"""
    return [
        PriceHistoryEntry(
            time=Timestamp(entry['time']),
            low=Price(entry['low']),
            high=Price(entry['high']),
        ) for entry in data
    ]


def _dict_history_to_data(data: Dict[str, Any]) -> PriceHistoryData:
    """Turns a price history data dict entry into a proper object"""
    return PriceHistoryData(
        data=_dict_history_to_entries(data['data']),
        start_time=Timestamp(data['start_time']),
        end_time=Timestamp(data['end_time']),
    )


def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


def _check_hourly_data_sanity(data, from_asset, to_asset):
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['time'] - n1['time']
        if diff != 3600:
            print(
                "Problem at indices {} and {} of {}_to_{} prices. Time difference is: {}".format(
                    index, index + 1, from_asset, to_asset, diff),
            )
            return False

        index += 2
    return True


class Cryptocompare():

    def __init__(self, data_directory: FilePath) -> None:
        self.prefix = 'https://min-api.cryptocompare.com/data/'
        self.data_directory = data_directory
        self.price_history: Dict[PairCacheKey, ] = dict()
        self.price_history_file: Dict[PairCacheKey, FilePath] = dict()

        # Check the data folder and remember the filenames of any cached history
        prefix = os.path.join(self.data_directory, 'price_history_')
        prefix = prefix.replace('\\', '\\\\')
        regex = re.compile(prefix + r'(.*)\.json')
        files_list = glob.glob(prefix + '*.json')

        for file_ in files_list:
            file_ = file_.replace('\\\\', '\\')
            match = regex.match(file_)
            assert match
            cache_key = match.group(1)
            self.price_history_file[cache_key] = file_

    def _api_query(self, path: str) -> Dict[str, Any]:
        querystr = f'{self.prefix}{path}'
        log.debug('Querying cryptocompare', url=querystr)
        resp = request_get_dict(querystr)
        if 'Response' not in resp or resp['Response'] != 'Success':
            error_message = 'Failed to query cryptocompare for: "{}"'.format(querystr)
            if 'Message' in resp:
                error_message += ". Error: {}".format(resp['Message'])

            log.error('Cryptocompare query failure', url=querystr, error=error_message)
            raise ValueError(error_message)

        return resp['Data']

    def query_endpoint_histohour(
            self,
            from_asset: Asset,
            to_asset: Asset,
            limit: int,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        # These two can raise but them raising here is a bug
        cc_from_asset_symbol = from_asset.to_cryptocompare()
        cc_to_asset_symbol = to_asset.to_cryptocompare()
        query_path = (
            f'histohour?fsym={cc_from_asset_symbol}&tsym={cc_to_asset_symbol}'
            f'&limit={limit}&toTs={to_timestamp}'
        )
        result = self._api_query(query_path)
        return result

    def query_endpoint_pricehistorical(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        log.debug(
            'Querying cryptocompare for daily historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        # These two can raise but them raising here is a bug
        cc_from_asset_symbol = from_asset.to_cryptocompare()
        cc_to_asset_symbol = to_asset.to_cryptocompare()
        query_path = (
            f'pricehistorical?fsym={cc_from_asset_symbol}&tsym={cc_to_asset_symbol}'
            f'&ts={timestamp}'
        )
        if to_asset == 'BTC':
            query_path += '&tryConversion=false'
        result = self._api_query(query_path)
        return Price(FVal(result[cc_from_asset_symbol][cc_to_asset_symbol]))

    def got_cached_price(self, cache_key: PairCacheKey, timestamp: Timestamp) -> bool:
        """Check if we got a price history for the timestamp cached"""
        if cache_key in self.price_history_file:
            if cache_key not in self.price_history:
                try:
                    with open(self.price_history_file[cache_key], 'rb') as f:
                        data = rlk_jsonloads(f.read())
                        self.price_history[cache_key] = _dict_history_to_data(data)
                except (OSError, IOError, JSONDecodeError):
                    return False

            in_range = (
                self.price_history[cache_key].start_time <= timestamp and
                self.price_history[cache_key].end_time > timestamp
            )
            if in_range:
                log.debug('Found cached price', cache_key=cache_key, timestamp=timestamp)
                return True

        return False

    def get_historical_data(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            historical_data_start: Timestamp,
    ) -> List[PriceHistoryEntry]:
        """
        Get historical price data from cryptocompare

        Returns a sorted list of price entries.
        """
        log.debug(
            'Retrieving historical price data from cryptocompare',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        cache_key = PairCacheKey(str(from_asset) + '_' + str(to_asset))
        got_cached_value = self.got_cached_price(cache_key, timestamp)
        if got_cached_value:
            return self.price_history[cache_key].data

        now_ts = int(time.time())
        cryptocompare_hourquerylimit = 2000
        calculated_history: List = list()

        if historical_data_start <= timestamp:
            end_date = historical_data_start
        else:
            end_date = timestamp
        while True:
            pr_end_date = end_date
            end_date = end_date + (cryptocompare_hourquerylimit) * 3600

            log.debug(
                'Querying cryptocompare for hourly historical price',
                from_asset=from_asset,
                to_asset=to_asset,
                cryptocompare_hourquerylimit=cryptocompare_hourquerylimit,
                end_date=end_date,
            )

            resp = self.query_endpoint_histohour(
                from_asset=from_asset,
                to_asset=to_asset,
                limit=2000,
                to_timestamp=end_date,
            )

            if pr_end_date != resp['TimeFrom']:
                # If we get more than we needed, since we are close to the now_ts
                # then skip all the already included entries
                diff = pr_end_date - resp['TimeFrom']
                if resp['Data'][diff // 3600]['time'] != pr_end_date:
                    raise ValueError(
                        'Expected to find the previous date timestamp during '
                        'historical data fetching',
                    )
                # just add only the part from the previous timestamp and on
                resp['Data'] = resp['Data'][diff // 3600:]

            if end_date < now_ts and resp['TimeTo'] != end_date:
                raise ValueError('End dates no match')

            # If last time slot and first new are the same, skip the first new slot
            last_entry_equal_to_first = (
                len(calculated_history) != 0 and
                calculated_history[-1]['time'] == resp['Data'][0]['time']
            )
            if last_entry_equal_to_first:
                resp['Data'] = resp['Data'][1:]
            calculated_history += resp['Data']
            if end_date >= now_ts:
                break

        # Let's always check for data sanity for the hourly prices.
        assert _check_hourly_data_sanity(calculated_history, from_asset, to_asset)
        full_history_data = {
            'data': calculated_history,
            'start_time': historical_data_start,
            'end_time': now_ts,
        }
        # and now since we actually queried the data let's also cache them
        filename = os.path.join(self.data_directory, 'price_history_' + cache_key + '.json')
        log.info(
            'Updating price history cache',
            filename=filename,
            from_asset=from_asset,
            to_asset=to_asset,
        )
        write_history_data_in_file(
            data=full_history_data,
            filepath=filename,
            start_ts=historical_data_start,
            end_ts=now_ts,
        )

        # Finally save the objects in memory and return them
        self.price_history_file[cache_key] = filename
        self.price_history[cache_key] = _dict_history_to_data(full_history_data)

        return self.price_history[cache_key].data

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        if from_asset in KNOWN_TO_MISS_FROM_CRYPTOCOMPARE:
            raise PriceQueryUnknownFromAsset(from_asset)

        data = self.get_historical_data(from_asset, to_asset, timestamp)

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        if timestamp >= data[0].time:
            index = convert_to_int((timestamp - data[0].time) / 3600, accept_only_exact=False)
            # print("timestamp: {} index: {} data_length: {}".format(timestamp, index, len(data)))
            diff = abs(data[index].time - timestamp)
            if index + 1 <= len(data) - 1:
                diff_p1 = abs(data[index + 1].time - timestamp)
                if diff_p1 < diff:
                    index = index + 1

            if data[index].high is None or data[index].low is None:
                # If we get some None in the hourly set price to 0 so that we check alternatives
                price = Price(0)
            else:
                price = (data[index].high + data[index].low) / 2
        else:
            # no price found in the historical data from/to asset, try alternatives
            price = Price(0)

        if price == 0:
            if from_asset != 'BTC' and to_asset != 'BTC':
                log.debug(
                    f"Couldn't find historical price from {from_asset} to "
                    f"{to_asset} at timestamp {timestamp}. Comparing with BTC...",
                )
                # Just get the BTC price
                asset_btc_price = self.query_historical_price(from_asset, A_BTC, timestamp)
                btc_to_asset_price = self.query_historical_price(A_BTC, to_asset, timestamp)
                price = asset_btc_price * btc_to_asset_price
            else:
                log.debug(
                    f"Couldn't find historical price from {from_asset} to "
                    f"{to_asset} at timestamp {timestamp} through cryptocompare."
                    f" Attempting to get daily price...",
                )
                price = self.query_endpoint_pricehistorical(from_asset, to_asset, timestamp)

        comparison_to_nonusd_fiat = (
            (to_asset.is_fiat() and to_asset != A_USD) or
            (from_asset.is_fiat() and from_asset != A_USD)
        )
        if comparison_to_nonusd_fiat:
            price = self.adjust_to_cryptocompare_price_incosistencies(
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        if price == 0:
            raise NoPriceForGivenTimestamp(
                from_asset,
                to_asset,
                tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S'),
            )

        log.debug(
            'Got historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            price=price,
        )

        return price

    def adjust_to_cryptocompare_price_incosistencies(
            self,
            price: Price,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> FVal:
        """Doublecheck against the USD rate, and if incosistencies are found
        then take the USD adjusted price.

        This is due to incosistencies in the provided historical data from
        cryptocompare. https://github.com/rotkehlchenio/rotkehlchen/issues/221

        Note: Since 12/01/2019 this seems to no longer be happening, but I will
        keep the code around just in case a regression is introduced on the side
        of cryptocompare.
        """
        from_asset_usd = self.query_historical_price(from_asset, A_USD, timestamp)
        to_asset_usd = self.query_historical_price(to_asset, A_USD, timestamp)

        usd_invert_conversion = from_asset_usd / to_asset_usd
        abs_diff = abs(usd_invert_conversion - price)
        relative_difference = abs_diff / max(price, usd_invert_conversion)
        if relative_difference >= FVal('0.1'):
            log.warning(
                'Cryptocompare historical price data are incosistent.'
                'Taking USD adjusted price. Check github issue #221',
                from_asset=from_asset,
                to_asset=to_asset,
                incosistent_price=price,
                usd_price=from_asset_usd,
                adjusted_price=usd_invert_conversion,
            )
            return usd_invert_conversion
        return price

    def all_coins(self) -> Dict[str, Any]:
        """Gets the list of all the cryptocompare coins"""
        # Get coin list of crypto compare
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cryptocompare_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found cryptocompare coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'r') as f:
                try:
                    data = rlk_jsonloads_dict(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery cryptocompare
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Cryptocompare coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._api_query('all/coinlist')

            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        # As described in the docs
        # https://min-api.cryptocompare.com/documentation?key=Other&cat=allCoinsWithContentEndpoint
        # This is not the entire list of assets in the system, so I am manually adding
        # here assets I am aware of that they already have historical data for in thei
        # cryptocompare system
        data['DAO'] = object()
        data['USDT'] = object()
        data['VEN'] = object()
        data['AIR*'] = object()  # This is Aircoin
        # This is SpendCoin (https://coinmarketcap.com/currencies/spendcoin/)
        data['SPND'] = object()
        # This is eBitcoinCash (https://coinmarketcap.com/currencies/ebitcoin-cash/)
        data['EBCH'] = object()
        # This is Educare (https://coinmarketcap.com/currencies/educare/)
        data['EKT'] = object()
        # This is Fidelium (https://coinmarketcap.com/currencies/fidelium/)
        data['FID'] = object()
        # This is Knoxstertoken (https://coinmarketcap.com/currencies/knoxstertoken/)
        data['FKX'] = object()
        # This is FNKOS (https://coinmarketcap.com/currencies/fnkos/)
        data['FNKOS'] = object()
        # This is FansTime (https://coinmarketcap.com/currencies/fanstime/)
        data['FTI'] = object()
        # This is Gene Source Code Chain
        # (https://coinmarketcap.com/currencies/gene-source-code-chain/)
        data['GENE*'] = object()
        # This is GazeCoin (https://coinmarketcap.com/currencies/gazecoin/)
        data['GZE'] = object()
        # This is probaly HarmonyCoin (https://coinmarketcap.com/currencies/harmonycoin-hmc/)
        data['HMC*'] = object()
        # This is IoTChain (https://coinmarketcap.com/currencies/iot-chain/)
        data['ITC'] = object()
        # This is MFTU (https://coinmarketcap.com/currencies/mainstream-for-the-underground/)
        data['MFTU'] = object()
        # This is Nexxus (https://coinmarketcap.com/currencies/nexxus/)
        data['NXX'] = object()
        # This is Owndata (https://coinmarketcap.com/currencies/owndata/)
        data['OWN'] = object()
        # This is PiplCoin (https://coinmarketcap.com/currencies/piplcoin/)
        data['PIPL'] = object()
        # This is PKG Token (https://coinmarketcap.com/currencies/pkg-token/)
        data['PKG'] = object()
        # This is Quibitica https://coinmarketcap.com/currencies/qubitica/
        data['QBIT'] = object()
        # This is DPRating https://coinmarketcap.com/currencies/dprating/
        data['RATING'] = object()
        # This is RouletteToken https://coinmarketcap.com/currencies/roulettetoken/
        data['RLT'] = object()
        # This is RocketPool https://coinmarketcap.com/currencies/rocket-pool/
        data['RPL'] = object()
        # This is SpeedMiningService (https://coinmarketcap.com/currencies/speed-mining-service/)
        data['SMS'] = object()
        # This is SmartShare (https://coinmarketcap.com/currencies/smartshare/)
        data['SSP'] = object()
        # This is ThoreCoin (https://coinmarketcap.com/currencies/thorecoin/)
        data['THR'] = object()
        # This is Transcodium (https://coinmarketcap.com/currencies/transcodium/)
        data['TNS'] = object()
        # This is XMedChainToken (https://coinmarketcap.com/currencies/xmct/)
        data['XMCT'] = object()
        # This is Xplay (https://coinmarketcap.com/currencies/xpa)
        data['XPA'] = object()

        return data
