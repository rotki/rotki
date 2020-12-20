import logging
import os
import sys
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_BACKOFF = 5


KNOWN_TO_MISS_FROM_CMC = (
    'VEN',
    '1CR',
    'DAO',
    'KFEE',
    'BTXCRD',
    'AC',
    'ACH',
    'ADADOWN',
    'ADAUP',
    'BTCDOWN',
    'BTCUP',
    'ETHDOWN',
    'ETHUP',
    'LINKDOWN',
    'LINKUP',
    'ADN',
    'AERO',
    'AM',
    'AIR-2',
    'AIR',
    'APH-2',
    'ARCH',
    # Missing from CMC, is in cryptocompare: https://www.cryptocompare.com/coins/bidr
    'BIDR',
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
    # Missing from CMC, is in cryptocompare: https://www.cryptocompare.com/coins/cntm
    'CNTM',
    'COMM',
    # Missing from API, is in website https://coinmarketcap.com/currencies/cryptcoin/
    'CRYPT',
    # Missing from API, is in https://coinmarketcap.com/currencies/cartesi/
    'CTSI',
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
    # Missing from API, is in https://coinmarketcap.com/currencies/hive-dollar/
    'HBD',
    # Missing from API, is in https://coinmarketcap.com/currencies/hive-blockchain/
    'HIVE',
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
    # Missing from CMC, is in cryptocompare: https://www.cryptocompare.com/coins/loon
    'LOON',
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
    # BTE. Missing from coinmarketcap but is in cryptocompare:
    # https://www.cryptocompare.com/coins/bte/overview
    'BTE',
    # Bitgem. Missing from API is https://coinmarketcap.com/currencies/bitgem/
    'BTG-2',
    # Harvest Masternode coin. Missing from API but is in
    # https://coinmarketcap.com/currencies/harvest-masternode-coin/
    'HC-2',
    # Triggers. Missing from API but is in
    # https://coinmarketcap.com/currencies/triggers/
    'TRIG',
    # 300 token. Missing from API but is in
    # https://coinmarketcap.com/currencies/300-token/
    '300',
    # Accelerator Network. Missing from API but is in
    # https://coinmarketcap.com/currencies/accelerator-network/
    'ACC-3',
    # Amis. Missing from API bus it in
    # https://coinmarketcap.com/currencies/amis/
    'AMIS',
    # ArcadeCity token. Missing from API bus it in
    # https://coinmarketcap.com/currencies/arcade-token/
    'ARC-2',
    # Astronaut token. Missing from API bus it in
    # https://coinmarketcap.com/currencies/astro/
    'ASTRO',
    # Artex coin. Missing from API but is in
    # https://coinmarketcap.com/currencies/artex-coin/
    'ATX-2',
    # Avalon coin. Missing from API but is in cryptocompare
    # https://www.cryptocompare.com/coins/ava/overview
    'AVA-2',
    # BitAsean. Missing from API but is in
    # https://coinmarketcap.com/currencies/bitasean/
    'BAS',
    # BelugaPay. Missing from API but is in
    # https://coinmarketcap.com/currencies/belugapay/
    'BBI',
    # Blockchain.capital. Missing from API but is in
    # https://coinmarketcap.com/currencies/bcap/
    'BCAP',
    # Bankcoin BCash (https://bankcoinbcash.com/)
    # is not in coinmarketcap but is in paprika
    'BCASH',
    # BHPCash is in coinmarketcap only as the new native token BHP
    # https://coinmarketcap.com/currencies/bhp-coin/
    'BHPC',
    # BITCAR (https://www.coingecko.com/en/coins/bitcar)
    # is not in coinmarketcap but is in cryptocompare
    'BITCAR',
    # BITPARK (https://coinmarketcap.com/currencies/bitpark-coin/)
    # is not in coinmarketcap but is in paprika
    'BITPARK',
    # BankCoin Cash (https://bankcoin-cash.com/)
    # is not in coinmarketcap but is in paprika
    'BKC',
    # Blockchain Index (https://coinmarketcap.com/currencies/blockchain-index/)
    # is not in coinmarketcap but is in cryptocompare
    'BLX',
    # BMChain (https://www.cryptocompare.com/coins/bmt/overview)
    # is not in coinmarketcap but is in cryptocompare
    'BMT',
    # Boulle (https://www.cryptocompare.com/coins/bou/overview)
    # is not in coinmarketcap but is in cryptocompare
    'BOU',
    # Bitair (https://coinmarketcap.com/currencies/bitair/)
    # is not in coinmarketcap but is in cryptocompare
    'BTCA',
    # EthereumBitcoin (https://www.cryptocompare.com/coins/btce/overview)
    # is not in coinmarketcap but is in cryptocompare
    'BTCE',
    # Bytether (https://www.cryptocompare.com/coins/byther/overview)
    # is not in coinmarketcap but is in cryptocompare
    'BTH',
    # Bither (https://www.cryptocompare.com/coins/btr/)
    # is not in coinmarketcap but is in cryptocompare
    'BTR-2',
    # Dice Money (https://www.cryptocompare.com/coins/cetstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CET-2',
    # Cofoundit. Missing from API bus it in
    # https://coinmarketcap.com/currencies/cofound-it/
    'CFI',
    # Crafty (https://www.cryptocompare.com/coins/cfty/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CFTY',
    # Climatecoin (https://www.cryptocompare.com/coins/co2/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CO2',
    # CoinPulseToken (https://www.cryptocompare.com/coins/cpex/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CPEX',
    # CrowdCoin (https://www.cryptocompare.com/coins/crcstarstarstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CRC-2',
    # CargoCoin (https://www.cryptocompare.com/coins/crgo/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CRGO',
    # Centra missing from API but is in
    # https://coinmarketcap.com/currencies/centra/
    'CTR',
    # CarTaxi (https://www.cryptocompare.com/coins/ctx/overview)
    # is not in coinmarketcap but is in cryptocompare
    'CTX-2',
    # Digital Developers Fund (https://coinmarketcap.com/currencies/digital-developers-fund/)
    # is not in coinmarketcap but is in cryptocompare
    'DDF',
    # Depository Network (https://www.cryptocompare.com/coins/depo/overview)
    # is not in coinmarketcap but is in cryptocompare
    'DEPO',
    # DigiPulse missing from API but is in
    # https://coinmarketcap.com/currencies/digipulse/
    'DGPT',
    # Etherisc (https://www.cryptocompare.com/coins/dip/overview)
    # is not in coinmarketcap but is in cryptocompare
    'DIP',
    # Divi Exchange Token (https://www.cryptocompare.com/coins/divx/)
    # is not in coinmarketcap but is in cryptocompare
    'DIVX',
    # Digital Assets Power Play (https://www.cryptocompare.com/coins/dpp/)
    # is not in coinmarketcap but is in cryptocompare
    'DPP',
    # DreamTeam Token (https://www.cryptocompare.com/coins/dream/)
    # is not in coinmarketcap but is in cryptocompare
    'DREAM',
    # Dcorp (https://www.cryptocompare.com/coins/drp/)
    # is not in coinmarketcap but is in cryptocompare
    'DRP',
    # DigitalTicks (https://www.coingecko.com/en/coins/digital-ticks)
    # is not in coinmarketcap but is in paprika
    'DTX-2',
    # Decentralized Universal Basic Income (https://www.cryptocompare.com/coins/dubi/)
    # is not in coinmarketcap but is in cryptocompare
    'DUBI',
    # E4ROW missing from API but is in
    # https://coinmarketcap.com/currencies/ether-for-the-rest-of-the-world/
    'E4ROW',
    # EAGLE missing from API but is in
    # https://coinmarketcap.com/currencies/eaglecoin/
    'EAGLE',
    # eBitcoinCash missing from API but is in
    # https://coinmarketcap.com/currencies/ebitcoin-cash/
    'EBCH',
    # OpenSource university (https://os.university/) is not in
    # coinmarketcap but is in paprika
    'EDU-2',
    # EGAS missing from API but is in
    # https://coinmarketcap.com/currencies/ethgas/
    'EGAS',
    # EasyMine (https://www.cryptocompare.com/coins/emt/overview)
    # is not in coinmarketcap but is in cryptocompare
    'EMT',
    # Ethereum Movie Venture missing from API but is in
    # https://coinmarketcap.com/currencies/ethereum-movie-venture/
    'EMV',
    # Hut34 Entropy token (https://www.cryptocompare.com/coins/entrp/overview)
    # is not in coinmarketcap but is in cryptocompare
    'ENTRP',
    # EtherBTC (https://www.cryptocompare.com/coins/ethb/overview)
    # is not in coinmarketcap but is in cryptocompare
    'ETHB',
    # Ethereum Dark missing from API but is in
    # https://coinmarketcap.com/currencies/ethereum-dark/
    'ETHD',
    # EximChain missing from API but is in
    # https://coinmarketcap.com/currencies/eximchain/
    'EXC-2',
    # Fingerprint  (https://fingerprintcoin.org/) is not
    # in coinmarketcap but is in paprika
    'FGP',
    # FidelityHouse (https://www.cryptocompare.com/coins/fih/overview)
    # is not in coinmarketcap but is in cryptocompare
    'FIH',
    # GastroAdvisor (https://www.cryptocompare.com/coins/fork/)
    # is not in coinmarketcap but is in cryptocompare. Note. Coinmarketcap
    # has the same symbol (FORK) for another asset:
    # https://coinmarketcap.com/currencies/forkcoin/#charts
    'FORK-2',
    # Farad missing from API but is in
    # https://coinmarketcap.com/currencies/farad/
    'FRD',
    # Fitrova missing from API but is in
    # https://coinmarketcap.com/currencies/fitrova/
    'FRV',
    # Finally Usable Crypto Karma token (FUCK) missing from API but is in
    # https://coinmarketcap.com/currencies/fucktoken/
    'FUCK',
    # Fund Yourself Now (FYN) missing from API but is in
    # https://coinmarketcap.com/currencies/fundyourselfnow/
    'FYN',
    # Globitex (https://www.cryptocompare.com/coins/gbxt/overview)
    # is not in coinmarketcap but is in cryptocompare
    'GBX-2',
    # Gimli missing from API but is in
    # https://coinmarketcap.com/currencies/gimli/
    'GIM',
    # Gladius token missing from API but is in
    # https://coinmarketcap.com/currencies/gladius-token/
    'GLA',
    # Mercury Protocol missing from API but is in
    # https://coinmarketcap.com/currencies/mercury-protocol/
    'GMT',
    # Hawala exchange token missing from API but is in
    # https://coinmarketcap.com/currencies/hat-exchange/
    'HAT',
    # Hedge token missing from API but is in
    # https://coinmarketcap.com/currencies/hedge/
    'HDG',
    # HackerGold token missing from API but is in
    # https://coinmarketcap.com/currencies/hacker-gold/
    'HKG',
    # iDice token missing from API but is in
    # https://coinmarketcap.com/currencies/idice/
    'ICE',
    # ICOS token missing from API but is in
    # https://coinmarketcap.com/currencies/icos/
    'ICOS',
    # Intimate. Completely missing ... but is in cryptocompare
    'ITM',
    # JOYSO (https://www.cryptocompare.com/coins/joystar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'JOY',
    # Kuende (https://www.cryptocompare.com/coins/kue/overview)
    # is not in coinmarketcap but is in cryptocompare
    'KUE',
    # Lendconnect is missing from API but is in
    # https://coinmarketcap.com/currencies/lendconnect/
    'LCT',
    # Liquorchain (https://etherscan.io/address/0x4A37A91eec4C97F9090CE66d21D3B3Aadf1aE5aD)
    # is not in coinmarketcap but is in paprika
    'LCT-2',
    # Logarithm (https://www.cryptocompare.com/coins/lgr/overview)
    # is not in coinmarketcap but is in cryptocompare
    'LGR',
    # Link Platform missing from API but is in
    # https://coinmarketcap.com/currencies/link-platform/
    'LNK',
    # Live Start missing from API but is in
    # https://coinmarketcap.com/currencies/live-stars/
    'LIVE',
    # Linker Coin  missing from API but is in
    # https://coinmarketcap.com/currencies/linker-coin/
    'LNC-2',
    # Locus Chain (https://etherscan.io/address/0xC64500DD7B0f1794807e67802F8Abbf5F8Ffb054)
    # is not in coinmarketcap but is in paprika
    'LOCUS',
    # Embers (https://coinmarketcap.com/currencies/embers/)
    # is not in coinmarketcap but is in cryptocompare
    'MBRS',
    # Musiconomi (https://coinmarketcap.com/currencies/musiconomi/)
    # is not in coinmarketcap but is in cryptocompare
    'MCI',
    # All.me (https://www.cryptocompare.com/coins/me/overview)
    # is not in coinmarketcap but is in cryptocompare
    'ME',
    # Meshbox (https://coinlib.io/coin/MESH/MeshBox)
    # is not in coinmarketcap but is in paprika
    'MESH',
    # Micro Licensing Coin (https://www.cryptocompare.com/coins/milc/overview)
    # is not in coinmarketcap but is in cryptocompare
    'MILC',
    # Media Network Token (https://www.cryptocompare.com/coins/mntstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'MNT',
    # Money Rebel (https://www.cryptocompare.com/coins/mrpstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'MRP',
    # Macroverse (https://www.cryptocompare.com/coins/mrv/overview)
    # is not in coinmarketcap but is in cryptocompare
    'MRV',
    # Mothership missing from API but is in
    # https://coinmarketcap.com/currencies/mothership/
    'MSP',
    # Nami ICO (https://etherscan.io/address/0x8d80de8A78198396329dfA769aD54d24bF90E7aa)
    # is not in coinmarketcap but is in paprika
    'NAC',
    # NeedsCoin (https://etherscan.io/address/0x9344b383b1d59b5ce3468b234dab43c7190ba735)
    # is not in coimarketcap but is in paprika
    'NCC-2',
    # Newbium missing from API but is in
    # https://coinmarketcap.com/currencies/newbium/
    'NEWB',
    # Nimfamoney missing from API but is in
    # https://coinmarketcap.com/currencies/nimfamoney/
    'NIMFA',
    # Network Token missing from API but is in
    # https://coinmarketcap.com/currencies/network-token/
    'NTWK',
    # Nexxus missing from API but is in
    # https://coinmarketcap.com/currencies/nexxus/
    'NXX',
    # Acorn Collective (https://www.cryptocompare.com/coins/oak/overview)
    # is not in coinmarketcap but is in cryptocompare
    'OAK',
    # Original Crypto coin (https://www.cryptocompare.com/coins/occ/overview)
    # is not in coinmarketcap but is in cryptocompare
    'OCC-2',
    # Wisepass missing from API but is in
    # https://coinmarketcap.com/currencies/wisepass/
    'PASS-2',
    # Publica missing from API but is in
    # https://coinmarketcap.com/currencies/publica/
    'PBL',
    # POP Chest Token (https://www.cryptocompare.com/coins/popc/overview)
    # is not in coinmarketcap but is in cryptocompare
    'POP-2',
    # Oyster missing from API but is in
    # https://coinmarketcap.com/currencies/oyster/
    'PRL',
    # Purpose missing from API but is in
    # https://coinmarketcap.com/currencies/purpose/
    'PRPS',
    # Quantum missing from API but is in
    # https://coinmarketcap.com/currencies/quantum/
    'QAU',
    # Qvolta missing from API but is in
    # https://coinmarketcap.com/currencies/qvolta/
    'QVT',
    # Realisto (https://www.cryptocompare.com/coins/rea/overview)
    # is not in coinmarketcap but is in cryptocompare
    'REA',
    # Red Cab (https://www.cryptocompare.com/coins/redc/overview)
    # is not in coinmarketcap but is in cryptocompare
    'REDC',
    # Rusgas missing from API but is in
    # https://coinmarketcap.com/currencies/rusgas/
    'RGS',
    # Riptide Coin (https://www.cryptocompare.com/coins/ript/overview)
    # is not in coinmarketcap but is in cryptocompare
    'RIPT',
    # RemiCoin missing from API but is in
    # https://coinmarketcap.com/currencies/remicoin/
    'RMC',
    # Render Token (https://www.cryptocompare.com/coins/rndr/overview)
    # is not in coinmarketcap but is in cryptocompare
    'RNDR',
    # RasputinOnlineCoin missing from API but is in
    # https://coinmarketcap.com/currencies/rasputin-online-coin/
    'ROC',
    # SGPay (https://www.cryptocompare.com/coins/sgp/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SGP',
    # OysterShell missing from API but is in
    # https://coinmarketcap.com/currencies/oyster-shell/
    'SHL',
    # Smart Investment Fund Token missing from API but is in
    # https://coinmarketcap.com/currencies/smart-investment-fund-token/
    'SIFT',
    # SkrillaToken (https://www.cryptocompare.com/coins/skrstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SKR',
    # Skraps (https://www.cryptocompare.com/coins/skrp/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SKRP',
    # SkyMap (https://www.cryptocompare.com/coins/skym/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SKYM',
    # SmartBillion (https://www.cryptocompare.com/coins/smartstar/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SMART-2',
    # snowball (https://etherscan.io/address/0x198A87b3114143913d4229Fb0f6D4BCb44aa8AFF)
    # is not in coinmarketcap but is in paprika
    'SNBL',
    # SandCoin (https://www.cryptocompare.com/coins/snd/overview)
    # is not in coinmarketcap but is in paprika. SND in coinmarketcap is SnodeCoin
    'SND',
    # Spice VC Token (https://www.cryptocompare.com/coins/spice/overview)
    # is not in coinmarketcap but is in paprika
    'SPICE',
    # StreamSpace (https://www.cryptocompare.com/coins/ssh/overview)
    # is not in coinmarketcap but is in cryptocompare
    'SSH',
    # StashPay (https://www.cryptocompare.com/coins/stp/overview)
    # is not in coinmarketcap but is in cryptocompare
    'STP',
    # StarCredits missing from API but is in
    # https://coinmarketcap.com/currencies/starcredits/
    'STRC',
    # Taklimakan (https://www.cryptocompare.com/coins/tan/overview)
    # is not in coinmarketcap but is in cryptocompare
    'TAN',
    # T-Bot (https://www.cryptocompare.com/coins/tbt/overview)
    # is not in coinmarketcap but is in cryptocompare
    'TBT',
    # TercetNetwork (https://etherscan.io/address/0x28d7F432d24ba6020d1cbD4f28BEDc5a82F24320)
    # is not in coinmarketcap but is in paprika
    'TCNX',
    # Trade.io (https://www.cryptocompare.com/coins/tio/)
    # is not in coinmarketcap but is in paprika and cryptocompare
    'TIO',
    # CryptoInsight is missing from API but is in
    # https://coinmarketcap.com/currencies/trackr/
    'TKR',
    # Missing from API but are both in:
    # https://coinmarketcap.com/currencies/3x-short-trx-token/
    # https://coinmarketcap.com/currencies/3x-long-trx-token/
    'TRXBEAR',
    'TRXBULL',
    # TaTaTu is missing from API but is in
    # https://coinmarketcap.com/currencies/tatatu/
    'TTU',
    # Urbit (https://www.cryptocompare.com/coins/urb/overview)
    # is not in coinmarketcap but is in cryptocompare
    'URB',
    'UTI',
    # USDJ is missing from coinmarketcap but is in cryptocompare
    # https://www.cryptocompare.com/coins/usdj/overview
    'USDJ',
    # Bitcoin Card (https://etherscan.io/address/0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D)
    # is not in coinmarketcap but is in paprika
    'VD',
    # VenusEnergy (https://www.cryptocompare.com/coins/venus/overview)
    # is not in coinmarketcap but is in cryptocompare
    'VENUS',
    # WhenCoin (https://www.cryptocompare.com/coins/when/overview)
    # is not in coinmarketcap but is in cryptocompare
    'WHEN',
    # WildCrypto missing from API but is in
    # https://coinmarketcap.com/currencies/wild-crypto/
    'WILD',
    # Wcoin missing from API but is in
    # https://coinmarketcap.com/currencies/wawllet/
    'WIN-2',
    # WeMark (https://www.cryptocompare.com/coins/wmk/overview)
    # is not in coinmarketcap but is in cryptocompare
    'WMK',
    # Wolk (https://www.cryptocompare.com/coins/wlk/overview)
    # is not in coinmarketcap but is in cryptocompare
    'WLK',
    # Gigawatt missing from API but is in
    # https://coinmarketcap.com/currencies/giga-watt-token/
    'WTT',
    # Sphere Identity missing from API but is in
    # https://coinmarketcap.com/currencies/sphere-identity/
    'XID',
    # Rialto missing from API but is in
    # https://coinmarketcap.com/currencies/rialto/
    'XRL',
    # ZIX (https://www.cryptocompare.com/coins/zix/)
    # is not in coinmarketcap but is in cryptocompare
    'ZIX',
)


# There can be multiple ids for the same symbol and for cases such as this
# we use this mapping to manually map Rotkehlchen symbols to CMC IDs
WORLD_TO_CMC_ID = {
    # For Rotkehlchen AID is AidCoin and AID-2 is Aidus token
    'AID': 2462,
    'AID-2': 3785,
    'ALQO': 2199,
    # For Rotkehlchen ATOM is Cosmos and ATOM-2 is Atomic Coin
    'ATOM': 3794,
    'ATOM-2': 1420,
    # Bitstars
    'BITS': 276,
    # Bitswift
    'BITS-2': 659,
    # Bitmark
    'BTM': 543,
    # Bytom
    'BTM-2': 1866,
    # 3x Long Bitcoin
    'BULL': 5157,
    # DEC is Darico Ecosystem Coin and DEC-2 is Decenter
    'DEC': 3376,
    'DEC-2': 5835,
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
    # For Rotkehlchen YOYOW if YOYO but in coinmarketcap it's YOYOW
    'YOYOW': 1899,
    # For Rotkehlchen ACC is AdCoin, ACC-2 is ACChain and ACC-3 is Accelerator network
    'ACC': 1915,
    'ACC-2': 2515,
    # For Rotkehlchen ADST is Adshares but in coinmarketcap it's ADS
    'ADST': 1883,
    # For Rotkehlchen ARB is Arbitrage coin and ARB-2 is ARbit
    'ARB': 2985,
    'ARB-2': 938,
    # Symbol for B2BX is B2B is coinmarketcap so we need to specify it
    'B2BX': 2204,
    # For Rotkehlchen BBK is BrickBlock and BBK-2 is Bitblocks
    'BBK': 3015,
    'BBK-2': 3051,
    # For Rotkehlchen BET is Dao.Casino and BET-2 is BetaCoin
    'BET': 1771,
    'BET-2': 70,
    # For Rotkehlchen BLOC is BlockCloud and BLOC-2 is Bloc.Money
    'BLOC': 3860,
    'BLOC-2': 3451,
    # For Rotkehlchen BOX is BoxToken and BOX-2 is ContentBox
    'BOX': 3475,
    'BOX-2': 2945,
    # For Rotkehlchen CAN is CanYaCoin and CAN-2 is Content And Ad Network
    'CAN': 2343,
    'CAN-2': 2358,
    # For Rotkehlchen CAT is Bitclave and CAT-2 is BlockCAT
    'CAT': 2334,
    'CAT-2': 1882,
    # For Rotkehlchen COS is Contentos. If ever want to add the other COS it's 1989
    'COS': 4036,
    # For Rotkehlchen CPC is CPChain and CPC-2 is CapriCoin
    'CPC': 2482,
    'CPC-2': 1008,
    # For Rotkehlchen EVN is Envion and EVN-2 is EvenCoin
    'EVN': 2526,
    'EVN-2': 3261,
    # For Rotkehlchen FT is Fabric Token and FT-2 is FCoin
    'FT': 2768,
    'FT-2': 2904,
    # For Rotkehlchen GENE is ParkGene and GENE-2 is Gene Source Code Chain
    'GENE': 2720,
    'GENE-2': 3297,
    # For Rotkehlchen GET is Guaranteed Entrance Token and GET-2 is Themis
    'GET': 2354,
    'GET-2': 3127,
    # For Rotkehlchen GOT is Go Network Token and GOT-2 is ParkinGo
    'GOT': 2898,
    'GOT-2': 3251,
    # For Rotkehlchen HMC is Hi Mutual Society and HMC-2 is Harmony Coin
    'HMC': 2484,
    'HMC-2': 1832,
    # For Rotkehlchen HMC is Hi Mutual Society and HMC-2 is Harmony Coin
    # For Rotkehlchen IQ is Everipedia and IQ-2 is IQ.cash
    'IQ': 2930,
    'IQ-2': 3273,
    'KNT': 3086,
    'KNT-2': 3383,
    # For Rotkehlchen LUNA is Luna Coin and LUNA-2 is Terra Luna
    'LUNA': 1496,
    'LUNA-2': 4172,
    # For Rotkehlchen MTC is doc.com Token and MTC-2 is Mesh Network
    'MTC': 2711,
    'MTC-2': 2936,
    # For Rotkehlchen NTK is Neurotoken and NTK-2 is NetKoin
    'NTK': 2536,
    'NTK-2': 3149,
    # For Rotkehlchen ONE is Menlo One and ONE-2 is Harmony
    'ONE': 3603,
    'ONE-2': 3945,
    # For Rotkehlchen ORS is OriginSport Token and ORS-2 is ORS Group
    'ORS': 2879,
    'ORS-2': 2911,
    # For Rotkehlchen PLA is Plair and PLA-2 is Playchip
    'PLA': 3711,
    'PLA-2': 3731,
    # For Rotkehlchen PNT is pNetwork and PNT-2 Penta
    'PNT': 5794,
    'PNT-2': 2691,
    # For Rotkehlcen SOL is Sola token and SOL-2 is Solana
    'SOL': 3333,
    'SOL-2': 5426,
    # For Rotkehlchen SOUL is Phantasma and SOUL-2 is CryptoSoul
    'SOUL': 2827,
    'SOUL-2': 3501,
    # For Rotkehlchen SPD is Spindle and SPD-2 is Stipend
    'SPD': 2828,
    'SPD-2': 2616,
    # For Rotkehlchen TCH is ThoreCash and TCH-2 is TigerCash
    'TCH': 3056,
    'TCH-2': 3806,
    # For Rotkehlchen TNC is TNC Token and we don't deal with Trinity network yet (2443)
    'TNC': 5524,
    # For Rotkehlchen WEB is Webcoin and WEB-2 Webchain
    'WEB': 3027,
    'WEB-2': 3361,
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

        raise AssertionError('The CMC id should always be correct. Is our data corrupt?')

    if asset_symbol in KNOWN_TO_MISS_FROM_CMC:
        return None

    found_coin_data: Optional[Dict[str, Any]] = None
    for coin in cmc_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_data:
                print(
                    # pylint false positive: https://github.com/PyCQA/pylint/issues/1498
                    f'Asset with symbol {asset_symbol} was found in coinmarketcap '  # pylint: disable=unsubscriptable-object  # noqa: E501
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

    def __init__(self, data_directory: Path, api_key: str):
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
            if response.status_code != 200:
                raise RemoteError(
                    f'Coinpaprika API request {response.url} for {path} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            return response.text

    def _get_cryptocyrrency_map(self) -> List[Dict[str, Any]]:
        start = 1
        limit = 5000
        result: List[Dict[str, Any]] = []
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
            with open(coinlist_cache_path, 'r') as f:
                try:
                    file_data = rlk_jsonloads_dict(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and it's over a month old then requery coinmarketcap
                    if file_data['time'] < now and now - file_data['time'] > 2629800:
                        log.info('Coinmarketcap coinlist cache is now invalidated')
                        invalidate_cache = True
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
            data = file_data['data']

        return data
