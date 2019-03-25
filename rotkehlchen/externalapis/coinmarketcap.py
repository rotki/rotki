import logging
import os
import sys
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath
from rotkehlchen.utils import rlk_jsondumps, rlk_jsonloads, rlk_jsonloads_dict, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_BACKOFF = 5


KNOWN_TO_MISS_FROM_CMC = (
    'VEN',
    '1CR',
    'DAO',
    'KFEE',
    'AC',
    'ACH',
    'ADN',
    'AERO',
    'AM',
    'AIR-2',
    'AIR',
    'APH-2',
    'ARCH',
    # Missing from API but is in website: https://coinmarketcap.com/currencies/bitcoindark/
    'BTCD',
    # Missing from API but is in website: https://coinmarketcap.com/currencies/cachecoin/
    'CACH',
    # Missing from API is in website https://coinmarketcap.com/currencies/caix/
    'CAIX',
    # Missing from API is in website https://coinmarketcap.com/currencies/cannacoin/
    'CCN-2',
    # Missing from API is in website https://coinmarketcap.com/currencies/cryptographic-anomaly/
    'CGA',
    # Missing from API, is in website https://coinmarketcap.com/currencies/cinni/
    'CINNI',
    # Missing from API, is in website https://coinmarketcap.com/currencies/concealcoin/
    'CNL',
    # Missing from API, is in website https://coinmarketcap.com/currencies/coinomat/
    'CNMT',
    # Missing from API, is in website https://coinmarketcap.com/currencies/communitycoin/
    'COMM',
    # Missing from API, is in website https://coinmarketcap.com/currencies/cryptcoin/
    'CRYPT',
    # Missing from API, is in https://coinmarketcap.com/currencies/conspiracycoin/
    'CYC',
    # Missing from API, is in https://coinmarketcap.com/currencies/diem/
    'DIEM',
    # Missing from API, is in https://coinmarketcap.com/currencies/darkcash/
    'DRKC',
    # Missing from API, is in https://coinmarketcap.com/currencies/dashcoin/
    'DSH',
    # Missing from API, is in https://coinmarketcap.com/currencies/earthcoin/
    'EAC',
    # Missing from API, is in https://coinmarketcap.com/currencies/execoin/
    'EXE',
    # Missing from API, is in https://coinmarketcap.com/currencies/fantomcoin/
    'FCN',
    # Missing from API, is in https://coinmarketcap.com/currencies/fibre/
    'FIBRE',
    # Missing from API, is in https://coinmarketcap.com/currencies/flappycoin/
    'FLAP',
    # Missing from API, is in https://coinmarketcap.com/currencies/fluttercoin/
    'FLT',
    # Missing from API, is in https://coinmarketcap.com/currencies/fractalcoin/
    'FRAC',
    # Missing from API, is in https://coinmarketcap.com/currencies/franko/
    'FRK',
    # Missing from API, is in https://coinmarketcap.com/currencies/gapcoin/
    'GAP',
    # Missing from API, is in https://coinmarketcap.com/currencies/gems/
    'GEMZ',
    # Missing from API, is in https://coinmarketcap.com/currencies/gameleaguecoin/
    'GML',
    # Missing from API, is in https://coinmarketcap.com/currencies/gpucoin/
    'GPUC',
    # Missing from API, is in https://coinmarketcap.com/currencies/guerillacoin/
    'GUE',
    # Missing from API, is in https://coinmarketcap.com/currencies/bigcoin/
    'HUGE',
    # Missing from API, is in https://coinmarketcap.com/currencies/heavycoin/
    'HVC',
    # Missing from API, is in https://coinmarketcap.com/currencies/next-horizon/
    'HZ',
    # Missing from API, is in https://coinmarketcap.com/currencies/klondikecoin/
    'KDC',
    # Missing from API, is in https://coinmarketcap.com/currencies/keycoin/
    'KEY-3',
    # Missing from API, is in https://coinmarketcap.com/currencies/leafcoin/
    'LEAF',
    # Missing from API, is in https://coinmarketcap.com/currencies/ltbcoin/
    'LTBC',
    # Missing from API, is in https://coinmarketcap.com/currencies/litecoinx/
    'LTCX',
    # Missing from API, is in https://coinmarketcap.com/currencies/monetaverde/
    'MCN',
    # Missing from API, is in https://coinmarketcap.com/currencies/minerals/
    'MIN',
    # Missing from API, is in https://coinmarketcap.com/currencies/memorycoin/
    'MMC',
    # Missing from API, is in https://coinmarketcap.com/currencies/mmnxt/
    'MMNXT',
    # Missing from API, is in https://coinmarketcap.com/currencies/mmxiv/
    'MMXIV',
    # Missing from API, is in https://coinmarketcap.com/currencies/marscoin/
    'MARS',
    # Missing from API, is in https://coinmarketcap.com/currencies/mazacoin/
    'MAZA',
    # Missing from API, is in https://coinmarketcap.com/currencies/nautiluscoin/
    'NAUT',
    # Missing from API, is in https://coinmarketcap.com/currencies/noblecoin/
    'NOBL',
    # Missing from API, is in https://coinmarketcap.com/currencies/noirshares/
    'NRS',
    # Missing from API, is in https://coinmarketcap.com/currencies/nxtinspect/
    'NXTI',
    # Missing from API is https://coinmarketcap.com/currencies/polybit/
    'POLY-2',
    # Missing from API is https://coinmarketcap.com/currencies/prospercoin/
    'PRC',
    # Missing from API is https://coinmarketcap.com/currencies/prcoin/
    'PRC-2',
    # Missing from API is https://coinmarketcap.com/currencies/qubitcoin/
    'Q2C',
    # Missing from API is https://coinmarketcap.com/currencies/qibuck/
    # and https://coinmarketcap.com/currencies/qibuck-asset/
    'QBK',
    # Missing from API is https://coinmarketcap.com/currencies/quazarcoin-old/
    # There is also a new one but we don't support the symbol yet
    # https://coinmarketcap.com/currencies/quasarcoin/ (QAC)
    'QCN',
    # Missing from API is https://coinmarketcap.com/currencies/qora/
    'QORA',
    # Missing from API is https://coinmarketcap.com/currencies/quatloo/
    'QTL',
    # Missing from API is https://coinmarketcap.com/currencies/riecoin/
    'RIC',
    # Missing from API is https://coinmarketcap.com/currencies/razor/
    'RZR',
    # Missing from API is https://coinmarketcap.com/currencies/shadowcash/
    'SDC',
    # Missing from API is https://coinmarketcap.com/currencies/silkcoin/
    'SILK',
    # Missing from API is https://coinmarketcap.com/currencies/spaincoin/
    'SPA',
    # Squallcoin. Completely missing ... but is in cryptocompare
    'SQL',
    # Missing from API is https://coinmarketcap.com/currencies/sonicscrewdriver/
    'SSD',
    # Missing from API is https://coinmarketcap.com/currencies/swarm/
    'SWARM',
    # Missing from API is https://coinmarketcap.com/currencies/sync/
    'SYNC',
    # Missing from API is https://coinmarketcap.com/currencies/torcoin-tor/
    'TOR',
    # Missing from API is https://coinmarketcap.com/currencies/trustplus/
    'TRUST',
    # Missing from API is https://coinmarketcap.com/currencies/unitus/
    'UIS',
    # Missing from API is https://coinmarketcap.com/currencies/umbrella-ltc/
    'ULTC',
    # Missing from API is https://coinmarketcap.com/currencies/supernet-unity/
    'UNITY',
    # Missing from API is https://coinmarketcap.com/currencies/uro/
    'URO',
    # Missing from API is https://coinmarketcap.com/currencies/usde/
    'USDE',
    # Missing from API is https://coinmarketcap.com/currencies/utilitycoin/
    'UTIL',
    # Missing from API is https://coinmarketcap.com/currencies/vootcoin/
    'VOOT',
    # InsanityCoin (WOLF). Completely missing ... but is in cryptocompare
    'WOLF',
    # Missing from API is https://coinmarketcap.com/currencies/sapience-aifx/
    'XAI',
    # Missing from API is https://coinmarketcap.com/currencies/crypti/
    'XCR',
    # Missing from API is https://coinmarketcap.com/currencies/dogeparty/
    'XDP',
    # Missing from API is https://coinmarketcap.com/currencies/libertycoin/
    'XLB',
    # Missing from API is https://coinmarketcap.com/currencies/pebblecoin/
    'XPB',
    # Missing from API is https://coinmarketcap.com/currencies/stabilityshares/
    'XSI',
    # Missing from API is https://coinmarketcap.com/currencies/vcash/
    'XVC',
    # Missing from API is https://coinmarketcap.com/currencies/yaccoin/
    'YACC',
    # GlobalCoin. Missing from API is https://coinmarketcap.com/currencies/globalcoin/
    'GLC-2',
    # Bytecent. Missing from API is https://coinmarketcap.com/currencies/bytecent/
    'BYC',
    # Bytecent. Missing from API is https://coinmarketcap.com/currencies/apx/
    'APX',
    # RCoin. Missing from API is https://coinmarketcap.com/currencies/rcoin/
    'RCN-2',
    # Blazecoin. Missing from API is https://coinmarketcap.com/currencies/blazecoin/
    'BLZ-2',
    # Bitgem. Missing from API is https://coinmarketcap.com/currencies/bitgem/
    'BTG-2',
    # Harvest Masternode coin. Missing from API but is in
    # https://coinmarketcap.com/currencies/harvest-masternode-coin/
    'HC-2',
    # Triggers. Missing from API but is in
    # https://coinmarketcap.com/currencies/triggers/
    'TRIG',
)


# There can be multiple ids for the same symbol and for cases such as this
# we use this mapping to manually map Rotkehlchen symbols to CMC IDs
WORLD_TO_CMC_ID = {
    # Bitstars
    'BITS': 276,
    # Bitswift
    'BITS-2': 659,
    # Bitmark
    'BTM': 543,
    # Bytom
    'BTM-2': 1866,
    # FairCoin
    'FAIR': 224,
    # FairGame
    'FAIR-2': 2366,
    # Selfkey
    'KEY': 2398,
    # KEY (bihu)
    'KEY-2': 2713,
    # KyberNetwork
    'KNC': 1982,
    # KingN Coin
    'KNC-2': 1743,
    # Goldcoind (GLC in Rotkehlcen) is in coinmarketcap with ID 25
    # and symbol GLD. Symbol discrepancy is the same as in cryptocompare
    'GLC': 25,
    # For Rotkehlchen MORE is More coin and MORE-2 is Mithril Ore token
    'MORE': 1722,
    'MORE-2': 3206,
    # For Rotkehlchen AID is AidCoin and AID-2 is Aidus token
    'AID': 2462,
    'AID-2': 3785,
    # For Rotkehlchen CBC is Cashbet Coin and CBC-2 is Cashbery coin
    'CBC': 2855,
    'CBC-2': 3199,
    # For Rotkehlcen CMCT is Crown machine token and CMCT-2 is Cyber movie chain token
    'CMCT': 2708,
    'CMCT-2': 3429,
    # For Rotkehlchen EDR is Endor Protocol and EDR-2 is E-Dinar coin
    'EDR': 2835,
    'EDR-2': 1358,
    # For Rotkehlchen USDS is Stable USD and USDS-2 is stronghold usd
    'USDS': 3719,
    'USDS-2': 3641,
    # For Rotkehlchen BTT is BitTorrent and BTT-2 is blocktrade token
    'BTT': 3718,
    'BTT-2': 3084,
    # For Rotkehlchen ONG is Ontology gas and ONG-2 is SoMee.Social
    'ONG': 3217,
    'ONG-2': 2240,
    # For Rotkehlchen SLT is SmartLands and SLT-2 is Social Lending Network
    'SLT': 2471,
    'SLT-2': 3117,
    # For Rotkehlchen PAI is Project Pai and PAI-2 is PCHAIN
    'PAI': 2900,
    'PAI-2': 2838,
    # For Rotkehlchen CMT is CyberMiles and CMT-2 is CometCoin
    'CMT': 2246,
    'CMT-2': 1291,
    # For Rotkehlchen HOT is Holochain and HOT-2 is Hydro Protocol
    'HOT': 2682,
    'HOT-2': 2430,
    # For Rotkehlchen IOTA is IOTA but in coimarketcap it's MIOTA
    'IOTA': 1720,
}


def find_cmc_coin_data(
        asset_symbol: str,
        cmc_list: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Given an asset's symbol find its data in the coinmarketcap list"""
    if not cmc_list:
        return None

    if asset_symbol in WORLD_TO_CMC_ID:
        coin_id = WORLD_TO_CMC_ID[asset_symbol]
        for coin in cmc_list:
            if coin['id'] == coin_id:
                return coin

        assert False, 'The CMC id should alway be correct. Is our data corrupt?'

    if asset_symbol in KNOWN_TO_MISS_FROM_CMC:
        return None

    found_coin_data = None
    for coin in cmc_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_data:
                print(
                    f'Asset with symbol {asset_symbol} was found in coinmarketcap '
                    f'both as {found_coin_data["id"]} - {found_coin_data["name"]} '
                    f'and {coin["id"]} - {coin["name"]}',
                )
                sys.exit(1)
            found_coin_data = coin

    if not found_coin_data:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in "
            f"coinmarketcap's coin list",
        )
        sys.exit(1)

    return found_coin_data


class Coinmarketcap():

    def __init__(self, data_directory: FilePath, api_key: str):
        self.prefix = 'https://pro-api.coinmarketcap.com/'
        self.backoff_limit = 180
        self.data_directory = data_directory
        self.session = requests.session()
        # As per coinmarketcap's API
        self.session.headers.update({
            'User-Agent': 'rotkehlchen',
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json',
            'Accept-Encoding': 'deflate, gzip',
        })

    def _query(self, path: str) -> str:
        backoff = INITIAL_BACKOFF
        while True:
            response = self.session.get(f'{self.prefix}{path}')
            if response.status_code == 429 and backoff < self.backoff_limit:
                gevent.sleep(backoff)
                backoff *= 2
                continue
            elif response.status_code != 200:
                raise RemoteError(
                    f'Coinpaprika API request {response.url} for {path} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            return response.text

    def _get_cryptocyrrency_map(self) -> List[Dict[str, Any]]:
        start = 1
        limit = 5000
        result = []
        while True:
            response_data = rlk_jsonloads_dict(
                self._query(f'v1/cryptocurrency/map?start={start}&limit={limit}'),
            )
            result.extend(response_data['data'])
            if len(response_data['data']) != limit:
                break

        return result

    def get_cryptocyrrency_map(self) -> List[Dict[str, Any]]:
        # TODO: Both here and in cryptocompare the cache funcionality is the same
        # Extract the caching part into its own function somehow and abstract it
        # away
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cmc_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found coinmarketcap coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'rb') as f:
                try:
                    data = rlk_jsonloads(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery coinmarketcap
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Coinmarketcap coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._get_cryptocyrrency_map()
            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinmarketcap coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        return data
