import logging
import os
from json.decoder import JSONDecodeError
from typing import Any, Dict

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath
from rotkehlchen.utils import request_get_dict, rlk_jsondumps, rlk_jsonloads_dict, ts_now

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
    'YOYO': 'YOYOW',
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
)


class Cryptocompare():

    def __init__(self, data_directory: FilePath):
        self.prefix = 'https://min-api.cryptocompare.com/data/'
        self.data_directory = data_directory

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

        return data
