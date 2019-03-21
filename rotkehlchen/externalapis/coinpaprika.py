import sys
from typing import Any, Dict, List, Optional

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.utils import rlk_jsonloads_dict, rlk_jsonloads_list

KNOWN_TO_MISS_FROM_PAPRIKA = (
    'DAO',
    'KFEE',
    '1CR',
    'ACH',
    'AERO',
    'AM',
    'AIR-2',
    'APH-2',
    'ARCH',
    'CAIX',
    'CGA',
    'CINNI',
    'CNL',
    'CNMT',
    'COMM',
    'DIEM',
    'DRKC',
    'EXE',
    'FIBRE',
    'FRAC',
    'GEMZ',
    'GPUC',
    'GUE',
    'HUGE',
    'HVC',
    'HZ',
    'KEY-3',  # KeyCoin
    'LTBC',
    'LTCX',
    'MCN',
    'MMC',
    'MMNXT',
    'MMXIV',
    'NAUT',
    'NRS',
    'NXTI',
    'POLY-2',  # Polybit
    'RZR',
    'SPA',
    'SQL',
    'SSD',
    'SWARM',  # Swarmcoin  https://coinmarketcap.com/currencies/swarm/
    'SYNC',
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
)


INITIAL_BACKOFF = 3

# Some symbols in coin paprika exists multiple times with different ids each time.
# This requires manual intervention and a lock in of the id mapping by hand
WORLD_TO_PAPRIKA_ID = {
    # ICN has both icn-iconomi and icn-icoin. The correct one appears to be the first
    'ICN': 'icn-iconomi',
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
    # For Rotkehlchen MIN is Minerals coin but in paprika it's known
    # as Mindol 'min-mindol', so mark it as unknown mapping
    'MIN': None,
    # For Rotkehlchen PRC is ProsperCoin and PRC-2 PRcoin
    # In paprika there is data only for PRcoin
    'PRC-2': 'prc-prcoin',
    'PRC': None,
    # For Rotkehlchen SILK is SilkCoin. In Paprika the only SILK is Silkchain
    # which we don't support
    'SILK': None,
    # For Rotkehlchen GLC is GoldCoin, and GLC-2 is GlobalCoin
    'GLC': 'gld-goldcoin',
    'GLC-2': 'glc-globalcoin',
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
    # For Rotkehlchen ONG is Ontology gas and ONG-2 is SoMee.Social
    'ONG': 'ong-ong',
    'ONG-2': 'ong-someesocial',
    # For Rotkehlchen SLT is SmartLands and SLT-2 is Social Lending Network
    'SLT': 'slt-smartlands',
    'SLT-2': 'slt-social-lending-token',
    # For Rotkehlchen PAI is Project Pai and PAI-2 is PCHAIN
    'PAI': 'pai-project-pai',
    'PAI-2': 'pai-pchain',
}


def find_paprika_coin_id(
        asset_symbol: str,
        paprika_coins_list: List[Dict[str, Any]],
) -> Optional[str]:
    """Given an asset's symbol find the paprika coin id from the paprika coins list"""
    found_coin_id = None
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

            found_coin_id = coin['id']

    if not found_coin_id:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in coin "
            f"coinpaprika's coin list",
        )
        sys.exit(1)

    return found_coin_id


class CoinPaprika():

    def __init__(self):
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
            elif response.status_code != 200:
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
