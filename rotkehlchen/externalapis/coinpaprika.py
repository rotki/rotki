import re
import sys
from typing import Any, Dict, List, Optional

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import EthAddress
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsonloads_list

KNOWN_TO_MISS_FROM_PAPRIKA = (
    'ADADOWN',
    'ADAUP',
    'BTCDOWN',
    'BTCUP',
    'ETHDOWN',
    'ETHUP',
    'LINKDOWN',
    'LINKUP',
    'ALGO',
    'DAO',
    'KFEE',
    'BAL',
    'BTXCRD',
    'BTE',
    'BIDR',
    '1CR',
    'ACH',
    'AERO',
    'AM',
    'AR',
    'AIR-2',
    'APH-2',
    'ARCH',
    'BCHBEAR',
    'BCHBULL',
    'BEAR',  # The 3x BTC short
    'BULL',  # The 3x BTC long
    'BNBBEAR',  # The 3x BNB short
    'BNBBULL',  # The 3x BNB long
    'BSVBEAR',
    'BSVBULL',
    'BKRW',  # https://www.cryptocompare.com/coins/bkrw/overview
    'BZRX',
    'CAIX',
    'CGA',
    'CELO',
    'CGLD',
    'CINNI',
    'CNL',
    'CNMT',
    'CNTM',
    'COMM',
    'CTSI',
    'DAWN',
    'DEC-2',
    'DEP',
    'DIEM',
    'DRKC',
    'DUSK',
    'ELAMA',
    'ETHBEAR',  # The 3x ETH short
    'ETHBULL',  # The 3x ETH long
    'EXE',
    'ERD',
    'EOSBEAR',  # The 3x EOS short
    'EOSBULL',  # The 3x EOS long
    'FIBRE',
    'FRAC',
    'GEMZ',
    'GPUC',
    'GUE',
    'HBD',
    'HDAO',
    'HIVE',
    'HNS',
    'HUGE',
    'HVC',
    'HZ',
    'JST',
    'KEY-3',  # KeyCoin
    'KSM',
    'LOON',
    'LTBC',
    'LTCX',
    'LUCY',
    'MCN',
    'ME',
    'MMC',
    'MMNXT',
    'MMXIV',
    'MTA',
    'NAUT',
    'NRS',
    'NXTI',
    'PLT',
    'POLY-2',  # Polybit
    'RING',
    'RZR',
    'SPA',
    'SQL',
    'SRM',
    'SSD',
    'STMX',
    'SUKU',
    'SWARM',  # Swarmcoin  https://coinmarketcap.com/currencies/swarm/
    'SWAP',
    'SUTER',
    'SYNC',
    'TEND',
    'TRADE',
    'TRXBEAR',  # The 3x TRX short
    'TRXBULL',  # The 3x TRX long
    'TNC',  # TNC token
    'ULTC',
    'UTIL',
    'VOOT',
    'WOLF',
    'XAI',
    'XCR',
    'XDP',
    'XLB',
    'XPB',
    'XSI',
    'YACC',
    'AMIS',
    'AVA-2',
    'BITCAR',
    'BMT',
    'BOU',
    'BTCE',
    'BTH',
    'BTR-2',
    'CET-2',
    'CFTY',
    'CO2',
    'CRGO',
    'DEPO',
    'DIP',
    'DPP',
    'EMT',
    'ENTRP',
    'ETHB',
    'FIH',
    'FORK-2',
    'HKG',
    'JOY',
    'ITM',
    'KDAG',
    'KUE',
    'LGR',
    'MILC',
    'MNT',
    'MRP',
    'MRV',
    'OAK',
    'OCC-2',
    'OXT',
    'OGN',
    'REA',
    'REDC',
    'RIPT',
    'RNDR',
    'SKR',
    'SKYM',
    'SPICE',
    'SOL-2',
    'SSH',
    'STP',
    'TAN',
    'TBT',
    'TROY',
    'URB',
    'UTI',
    'USDJ',
    'VENUS',
    'WMK',
    'WLK',
    'WRX',
    'XTP',
    'ZIX',
)


INITIAL_BACKOFF = 3

# Some symbols in coin paprika exists multiple times with different ids each time.
# This requires manual intervention and a lock in of the id mapping by hand
WORLD_TO_PAPRIKA_ID = {
    'ALQO': 'xlq-alqo',
    # ICN has both icn-iconomi and icn-icoin. The correct one appears to be the firest
    'ICN': 'icn-iconomi',
    # In Rotkehlchen BCHC means bitcherry. Paprika also has bchc-bcash-classic-token
    'BCHC': 'bchc-bitcherry',
    # In Rotkehlchen BAT means the basic attention token and not bat-batcoin
    'BAT': 'bat-basic-attention-token',
    # For Rotkehlchen BITS is Bitstars and not Bitswift
    'BITS': 'bits-bitstar',
    # And then naturally BITS-2 is Bitswift
    'BITS-2': 'bits-bitswift',
    # For Rotkehlchen BTCS is BitcoinScrypt
    'BTCS': 'btcs-bitcoin-scrypt',
    # For Rotkehlchen BTM is Bitmark
    'BTM': 'btm-bitmark',
    # For Rotkehlchen BTM-2 is Bytom
    'BTM-2': 'btm-bytom',
    # For Rotkehlchen CCN is CustomContractNetwork
    'CCN': 'ccn-customcontractnetwork',
    # For Rotkehlchen CCN-2 is Cannacoin
    'CCN-2': 'ccn-cannacoin',
    # For Rotkehlchen CYC is conspiracy coin, but in paprika it's
    # known as cycling coin, so mark it as unknown mapping
    'CYC': None,
    # For Rotkehlchen FAIR is FairCoin
    'FAIR': 'fair-faircoin',
    # For Rotkehlchen FAIR-2 is FairGame
    'FAIR-2': 'fair-fairgame',
    # For Rotkehlchen KEY is SelfKey
    'KEY': 'key-selfkey',
    # For Rotkehlchen KEY-2 is KEY
    'KEY-2': 'key-key',
    # For Rotkehlchen KNC is KyberNetwork
    'KNC': 'knc-kyber-network',
    # For Rotkehlchen KNC-2 is Kingn coin
    'KNC-2': 'knc-kingn-coin',
    # For Rotkehlchen Luna Coin is LUNA
    # and Terra Luna is LUNA-2
    'LUNA': 'luna-luna-coin',
    'LUNA-2': 'luna-terra',
    # For Rotkehlchen MIN is Minerals coin but in paprika it's known
    # as Mindol 'min-mindol', so mark it as unknown mapping
    'MIN': None,
    # For Rotkehlchen PRC is ProsperCoin and PRC-2 PRcoin
    # In paprika there is data only for PRcoin
    'PRC-2': 'prc-prcoin',
    'PRC': None,
    # For Rotkehlchen PNT is pNetwork and PNT-2 Penta
    'PNT': 'pnt-pnetwork',
    'PNT-2': 'pnt-penta',
    # For Rotkehlchen SILK is SilkCoin. In Paprika the only SILK is Silkchain
    # which we don't support
    'SILK': None,
    # For Rotkehlchen GLC is GoldCoin, and GLC-2 is GlobalCoin
    'GLC': 'gld-goldcoin',
    'GLC-2': 'glc-globalcoin',
    # For Rotki MBL is Movieblock
    'MBL': 'mbl-moviebloc',
    # For Rotkehlchen MORE is More coin and MORE-2 is Mithril Ore token
    'MORE': 'more-more-coin',
    'MORE-2': 'more-mithril-ore',
    # For Rotkehlchen FUN is FunFair token. We don't support Tron fun token
    # which is fun-tronfun-token in paprika
    'FUN': 'fun-funfair',
    # For Rotkehlchen RCN is Ripio Credit Network and RCN-2 is Rcoin
    'RCN': 'rcn-ripio-credit-network',
    'RCN-2': 'rcn-rcoin',
    # For Rotkehlchen AID is Aid Coin and AID-2 is Aidus Token
    'AID': 'aid-aidcoin',
    'AID-2': 'aid-aidus-token',
    # For Rotkehlchen CBC is Cashbet Coin and CBC-2 is Cashbery coin
    'CBC': 'cbc-cashbet-coin',
    'CBC-2': 'cbc-cashbery-coin',
    # For rotkehlchen COS is Contentos
    'COS': 'cos-contentos',
    # For Rotkehlchen CMCT is Crown machine token and CMCT-2 is Cyber movie chain token
    'CMCT': 'cmct-crowd-machine',
    'CMCT-2': 'cmct-cyber-movie-chain',
    # For Rotkehlchen EDR is Endor Protocol and EDR-2 is E-Dinar coin
    'EDR': 'edr-endor-protocol',
    'EDR-2': 'edr-e-dinar-coin',
    # For Rotkehlchen USDS is Stable USD and USDS-2 is stronghold usd
    'USDS': 'usds-stableusd',
    'USDS-2': 'usds-stronghold-usd',
    # For Rotkehlchen BTT is BitTorrent and BTT-2 is blocktrade token
    'BTT': 'btt-bittorrent',
    'BTT-2': 'btt-blocktrade-token',
    # For Rotkehlchen ONE is Menlo One and ONE-2 is Harmony
    'ONE': 'one-menlo-one',
    'ONE-2': 'one-harmony',
    # For Rotkehlchen ONG is Ontology gas and ONG-2 is SoMee.Social
    'ONG': 'ong-ong',
    'ONG-2': 'ong-someesocial',
    # For Rotkehlchen SLT is SmartLands and SLT-2 is Social Lending Network
    'SLT': 'slt-smartlands',
    'SLT-2': 'slt-social-lending-token',
    # For Rotkehlchen PAI is Project Pai and PAI-2 is PCHAIN
    'PAI': 'pai-project-pai',
    'PAI-2': 'pai-pchain',
    # For Rotkehlchen BLZ is Bluezelle and BLZ-2 BlazeCoin
    'BLZ': 'blz-bluzelle',
    'BLZ-2': 'blz-blazecoin',
    # For Rotkehlchen BTG is Bitcoin Gold and BTG-2 BitGem
    'BTG': 'btg-bitcoin-gold',
    'BTG-2': 'btg-bitgem',
    # For Rotkehlchen CMT is CyberMiles and CMT-2 is CometCoin
    'CMT': 'cmt-cybermiles',
    'CMT-2': 'cmt-comet',
    # For Rotkehlchen HC is Hypercash and HC-2 is Harvest Masternode Coin
    'HC': 'hc-hypercash',
    'HC-2': 'hc-harvest-masternode-coin',
    # For Rotkehlchen HOT is Holochain and HOT-2 is Hydro Protocol
    'HOT': 'hot-holo',
    'HOT-2': 'hot-hydro-protocol',
    # For Rotkehlchen IOTA is IOTA but in paprika it's MIOTA
    'IOTA': 'miota-iota',
    # Paprika has two identical entries for OpenANX:
    # oax-oax and oax-openanx. Choosing the one with the most recent details.
    'OAX': 'oax-oax',
    # YOYOW is known as YOYOW in CoinPaprika
    'YOYOW': 'yoyow-yoyow',
    # For Rotkehlchen ACC is AdCoin, ACC-2 is ACChain and ACC-3 is Accelerator network
    'ACC': 'acc-adcoin',
    'ACC-2': 'acc-acchain',
    'ACC-3': 'acc-accelerator-network',
    # For Rotkehlchen ARB is Arbitrage coin and ARB-2 is ARbit
    'ARB': 'arb-arbitrage',
    'ARB-2': 'arb-arbit',
    # For Rotkehlchen ARC is Advanced Technology Coin (Arctic) and ARC-2 is ArcadeCity
    'ARC': 'arc-advanced-technology-coin',
    'ARC-2': 'arc-arcade-token',
    # For Rotkehlchen ATX is Astoin Coin and ATX-2 is ArtexCoin
    'ATX': 'atx-aston',
    'ATX-2': 'atx-artex-coin',
    # For Rotkehlcen ATOM is Cosmos and ATOM-2 is Atomic coin
    'ATOM': 'atom-cosmos',
    'ATOM-2': 'atom-atomic-coin',
    # For Rotkehlchen B2BX is B2BX but in paprika it's B2B
    'B2BX': 'b2b-b2bx',
    # For Rotkehlchen BBK is BrickBlock and BBK-2 is Bitblocks
    'BBK': 'bbk-brickblock',
    'BBK-2': 'bbk-bitblocks',
    # For Rotkehlchen BET is Dao.Casino and BET-2 is BetaCoin
    'BET': 'bet-daocasino',
    'BET-2': 'bet-betacoin',
    # For Rotkehlcen BHPCash is BHPC but in Paprika it's BHP
    'BHPC': 'bhpc-bhpcash',
    # For Rotkehlcen BITPARK is BITPARK but in Paprika it's BPC
    'BITPARK': 'bpc-bitpark-coin',
    # For Rotkehlchen BLOC is BlockCloud and BLOC-2 is Bloc.Money
    'BLOC': 'bloc-blockcloud',
    'BLOC-2': 'bloc-blocmoney',
    # For Rotkehlchen BOX is BoxToken and BOX-2 is ContentBox
    'BOX': 'box-box-token',
    'BOX-2': 'box-contentbox',
    # For Rotkehlchen BTR is Bitether and BTR-2 is Bither. Paprika does not have Bither
    'BTR': 'btr-bitether',
    # For Rotkehlchen CAN is CanYaCoin and CAN-2 is Content And Ad Network
    'CAN': 'can-canyacoin',
    'CAN-2': 'can-content-and-ad-network',
    # For Rotkehlchen CAT is Bitclave and CAT-2 is BlockCAT
    'CAT': 'cat-bitclave',
    'CAT-2': 'cat-blockcat',
    # For Rotkehlchen CBT is Commerceblock
    'CBT': 'cbt-commerceblock',
    # For Rotkehlchen CDX is CDX Network
    'CDX': 'cdx-network',
    # For Rotkehlchen CET is CoinEx Token and CET-2 Dice Money
    'CET': 'cet-coinex-token',
    # For Rotkehlchen CPC is CPChain and CPC-2 is CapriCoin
    'CPC': 'cpc-cpchain',
    'CPC-2': 'cpc-capricoin',
    # For Rotkehlchen CRC is CryCash and CRC-2 is CrowdCoin
    'CRC': 'crc-crycash',
    'CRC-2': 'crc-crowdcoin',
    # For Rotkehlchen CTX is Centauri and CTX-2 is CarTaxi
    'CTX': 'ctx-centauri',
    'CTX-2': 'ctx-cartaxi-token',
    # For Rotkehlchen DAV is DAV Coin
    'DAV': 'dav-dav-coin',
    # For Rotkehlchen DICE is Etheroll Dice
    'DICE': 'dice-etheroll',
    # For Rotkehlchen DTX is DataBroker DAO's DigitalExchange token and DTX-2
    # is Digital Ticks
    'DTX': 'dtx-data-exchange',
    'DTX-2': 'dtx-digital-ticks',
    # For Rotkehlchen EDU is Educoin and EDU-2 is opensource university
    'EDU': 'edu-educoin',
    'EDU-2': 'edu-open-source-university',
    # For Rotkehlchen EVN is Envion and EVN-2 is EvenCoin
    'EVN': 'evn-envion',
    'EVN-2': 'evn-evencoin',
    # For Rotkehlchen EXC is ExcaliburCoin and EXC-2 is EximChain Token
    'EXC': 'exc-excaliburcoin',
    'EXC-2': 'exc-eximchain',
    # For Rotkehlchen FID is Fidelium
    'FID': 'fid-fidelium',
    # For Rotkehlchen FORK is ForkCoin and FORK-2 is GastroAdvisor. For
    # coinpaprika only ForkCoin exists as FORK.
    'FORK': 'fork-forkcoin',
    # For Rotkehlchen FOR is Force protocol. In paprika also force network
    # exists but we don't yet support it
    'FOR': 'for-force-protocol',
    # For Rotkehlchen FT is Fabric Token and FT-2 is FCoin
    'FT': 'ft-fabric-token',
    'FT-2': 'ft-fcoin-token',
    # For Rotkehlchen GBX is GoByte and GBX-2 is Globitex
    'GBX': 'gbx-gobyte',
    'GBX-2': 'gbx-globitex',
    # For Rotkehlchen GENE is ParkGene and GENE-2 is Gene Source Code Chain
    'GENE': 'gene-parkgene',
    'GENE-2': 'gene-gene-source-code-chain',
    # For Rotkehlchen GET is Guaranteed Entrance Token and GET-2 is Themis
    'GET': 'get-get-protocol',
    'GET-2': 'get-themis',
    # For Rotkehlchen GOT is Go Network Token and GOT-2 is ParkinGo
    'GOT': 'got-gonetwork',
    'GOT-2': 'got-parkingo',
    # For Rotkehlchen GTC is Game.com
    'GTC': 'gtc-gamecom',
    # For Rotkehlchen HMC is Hi Mutual Society and HMC-2 is Harmony Coin
    'HMC': 'hmc-hi-mutual-society',
    'HMC-2': 'hmc-harmonycoin',
    # For Rotkehlchen IPL is InsurePal (for some reason has 2 entires in paprika)
    'IPL': 'ipl-vouchforme',
    # For Rotkehlchen IQ is Everipedia and IQ-2 is IQ.cash
    'IQ': 'iq-everipedia',
    'IQ-2': 'iq-iqcash',
    # For Rotkehlchen KNT is Kora Network Token and KNT-2 is Knekted
    'KNT': 'knt-kora-network-token',
    'KNT-2': 'knt-knekted',
    # For Rotkehlchen LCT is LendConnect and LCT-2 is Liquor-chain
    'LCT': 'lct-lendconnect',
    'LCT-2': 'lct-liquor-chain',
    # For Rotkehlchen LNC is Blocklancer and LNC-2 is Linker Coin
    'LNC': 'lnc-blocklancer',
    'LNC-2': 'lnc-linker-coin',
    # For Rotkehlchen MTC is doc.com Token and MTC-2 is Mesh Network
    'MTC': 'mtc-docademic',
    'MTC-2': 'mtc-mtc-mesh-network',
    # For Rotkehlchen NCC is neurochain and NCC-2 is NeedsCoin
    'NCC': 'ncc-neurochain',
    'NCC-2': 'ncc-needscoin',
    # For Rotkehlchen NTK is Neurotoken and NTK-2 is NetKoin
    'NTK': 'ntk-neurotoken',
    'NTK-2': 'ntk-netkoin',
    # For Rotkehlchen ORS is OriginSport Token and ORS-2 is ORS group
    'ORS': 'ors-origin-sport',
    'ORS-2': 'ors-ors-group',
    # For Rotkehlchen PASS is Blockpass, and PASS-2 is Wisepass
    'PASS': 'pass-blockpass',
    'PASS-2': 'pass-wisepass',
    # For Rotkehlchen PLAY is HeroCoin
    'PLAY': 'play-herocoin',
    # For Rotkehlchen PLA is Plair and PLA-2 is Playchip
    'PLA': 'pla-plair',
    'PLA-2': 'pla-playchip',
    # For Rotkehlchen PLG is Pledgecoin
    'PLG': 'plg-pledge-coin',
    # For Rotkehlchen POP is PopularCoin, and POP-2 is POP Chest Token
    'POP': 'pop-popularcoin',
    'POP-2': 'pop-pop-chest-token',
    # For Rotkehlchen RED is Red token
    'RED': 'red-red',
    'REV': 'r-revain',
    # For Rotkehlchen RMC is RemiCoin
    'RMC': 'rmc-remicoin',
    # For Rotkehlchen SAC is SmartApplicationChain
    'SAC': 'sac-smart-application-chain',
    # For Rotkehlchen SMART is SmartCash, and SMART-2 is SmartBillions
    'SMART': 'smart-smartcash',
    'SMART-2': 'smart-smartbillions',
    # For Rotkehlchen SND is SandCoin
    'SND': 'snd-sand-coin',
    # For Rotkehlchen SOUL is Phantasma and SOUL-2 is CryptoSoul
    'SOUL': 'soul-phantasma',
    'SOUL-2': 'soul-cryptosoul',
    # For Rotkehlchen SPD is Spindle and SPD-2 is Stipend
    'SPD': 'spd-spindle',
    'SPD-2': 'spd-stipend',
    # For Rotkehlchen STR is Staken
    'STR': 'str-staker',
    # For Rotkehlchen TCH is ThoreCash and TCH-2 is TigerCash
    'TCH': 'tch-thore-cash',
    'TCH-2': 'tch-tigercash',
    # For Rotkehlchen TEAM is TokenStars Team
    'TEAM': 'team-team-tokenstars',
    # For Rotkehlchen TOK is Tokok
    'TOK': 'tok-tokok',
    # For Rotkehlchen VIT is Vice Industry Token
    'VIT': 'vit-vice-industry-token',
    # For Rotkehlchen WBTC is Wrapped Bitcoin
    'WBTC': 'wbtc-wrapped-bitcoin',
    # For Rotkehlchen WEB is Webcoin and WEB-2 Webchain
    'WEB': 'web-webcoin',
    'WEB-2': 'web-webchain',
    # For Rotkehlchen WIN is Winchain Token and WIN-2 WCoin
    'WIN': 'win-wintoken',
    'WIN-2': 'win-wcoin',
    # For Rotkehlchen XID is Sphre Air
    'XID': 'xid-sphre-air',
    # For Rotkehlchen XSR is Xensor
    'XSR': 'xsr-xensor',
    # For Paprika PHX has not been updated to PHB
    'PHB': 'phx-red-pulse-phoenix',
}


def find_paprika_coin_id(
        asset_symbol: str,
        paprika_coins_list: List[Dict[str, Any]],
) -> Optional[str]:
    """Given an asset's symbol find the paprika coin id from the paprika coins list"""
    found_coin_id: Optional[str] = None
    if asset_symbol in WORLD_TO_PAPRIKA_ID:
        return WORLD_TO_PAPRIKA_ID[asset_symbol]

    if asset_symbol in KNOWN_TO_MISS_FROM_PAPRIKA:
        return None

    for coin in paprika_coins_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_id:
                print(
                    f'Asset with symbol {asset_symbol} was found in coin paprika both '
                    f'with id {found_coin_id} and {coin["id"]}',
                )
                sys.exit(1)

            assert isinstance(coin['id'], str)
            found_coin_id = coin['id']

    if not found_coin_id:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in coin "
            f"coinpaprika's coin list",
        )
        sys.exit(1)

    return found_coin_id


def get_paprika_data_eth_token_address(
        paprika_data: Dict[str, Any],
        asset_symbol: str,
) -> Optional[EthAddress]:
    """If the coin paprika entry is an ethereum token get its ethereum address if possible"""

    if 'parent' not in paprika_data:
        return None

    if paprika_data['parent']['id'] != 'eth-ethereum':
        return None

    if 'links' not in paprika_data or 'explorer' not in paprika_data['links']:
        return None

    links = paprika_data['links']['explorer']
    if len(links) == 0:
        return None

    match = re.search('https://etherscan.io/token/(.*)', links[0])
    if not match:
        return None

    if match:
        address = match.group(1)

    if not address.startswith('0x'):
        print(f'Paprika etherscan link for {asset_symbol} did not contain an address')
        return None

    return address


KNOWN_WRONG_PAPRIKA_DATA = (
    'COIN',  # For Coinvest paprika has the old non-migrated contract address
    'DUBI',  # For Decentralized Universal Basic Income paprika has the old contract address
    'LYM',  # For LYMPO paprika has the old contract address
    'TIO',  # For Trade.io paprika has the old contract address
    'VSF',  # For Verisafe paprika has the old contract address
)


def check_paprika_token_address(
        paprika_token_address: Optional[EthAddress],
        given_token_address: Optional[EthAddress],
        asset_symbol: str,
) -> None:
    if asset_symbol in KNOWN_WRONG_PAPRIKA_DATA:
        return

    if not paprika_token_address or not given_token_address:
        return

    address_matches = (
        given_token_address.lower() == paprika_token_address.lower()
    )
    if not address_matches:
        print(
            f'For eth token with symbol {asset_symbol} we have address '
            f'{given_token_address} but coin paprika has {paprika_token_address}',
        )
        sys.exit(1)

    print(f'Verified eth address in paprika for eth token with symbol {asset_symbol}')
    return


class CoinPaprika():

    def __init__(self) -> None:
        self.prefix = 'https://api.coinpaprika.com/v1/'
        self.backoff_limit = 180

    def _query(self, path: str) -> str:
        backoff = INITIAL_BACKOFF
        while True:
            response = requests.get(f'{self.prefix}{path}')
            if response.status_code == 429 and backoff < self.backoff_limit:
                gevent.sleep(backoff)
                backoff *= 2
                continue
            if response.status_code != 200:
                raise RemoteError(
                    f'Coinpaprika API request {response.url} for {path} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            return response.text

    def get_coins_list(self) -> List[Dict[str, Any]]:
        response_data = self._query('coins')
        return rlk_jsonloads_list(response_data)

    def get_coin_by_id(self, coinpaprika_id: str) -> Dict[str, Any]:
        response_data = self._query(f'coins/{coinpaprika_id}')
        return rlk_jsonloads_dict(response_data)
