import logging
import os
from json.decoder import JSONDecodeError
from typing import Any, Dict

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath
from rotkehlchen.utils import request_get, rlk_jsondumps, rlk_jsonloads, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


WORLD_TO_CRYPTOCOMPARE = {
    'RDN': 'RDN*',
    'DATAcoin': 'DATA',
    'IOTA': 'IOT',
    'BQX': 'ETHOS',
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
)


class Cryptocompare():

    def __init__(self, data_directory: FilePath):
        self.prefix = 'https://min-api.cryptocompare.com/data/'
        self.data_directory = data_directory

    def _api_query(self, path: str) -> Dict[str, Any]:
        querystr = f'{self.prefix}{path}'
        log.debug('Querying cryptocompare', url=querystr)
        resp = request_get(querystr)
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
            with open(coinlist_cache_path, 'rb') as f:
                try:
                    data = rlk_jsonloads(f.read())
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

        return data
