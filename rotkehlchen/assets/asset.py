import logging
from dataclasses import InitVar, dataclass, field
from functools import total_ordering
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Type, TypeVar

from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.resolver import (
    ChainID,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, Timestamp

from .types import AssetType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UnderlyingTokenDBTuple = Tuple[str, str, str, str]


class UnderlyingToken(NamedTuple):
    """Represents an underlying token of a token

    Is used for pool tokens, tokensets etc.
    """
    address: ChecksumEvmAddress
    chain: ChainID
    token_kind: EvmTokenKind
    weight: FVal  # Floating percentage from 0 to 1

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'chain': self.chain.serialize(),
            'token_kind': self.token_kind.serialize(),
            'weight': str(self.weight * 100),
        }

    @classmethod
    def deserialize_from_db(cls, entry: UnderlyingTokenDBTuple) -> 'UnderlyingToken':
        return UnderlyingToken(
            address=entry[0],  # type: ignore
            chain=ChainID.deserialize_from_db(entry[1]),
            token_kind=EvmTokenKind.deserialize_from_db(entry[2]),
            weight=FVal(entry[3]),
        )

    def get_identifier(self) -> str:
        return evm_address_to_identifier(
            address=str(self.address),
            chain=self.chain,
            token_type=self.token_kind,
        )


WORLD_TO_BITTREX = {
    # In Rotkehlchen Bitswift is BITS-2 but in Bittrex it's BITS
    'BITS-2': 'BITS',
    # In Rotkehlchen NuBits is USNBT but in Bittrex it's NBT
    'USNBT': 'NBT',
    # In Rotkehlchen BTM-2 is Bytom but in Bittrex it's BTM
    'BTM-2': 'BTM',
    # Bittrex PI shoould map to rotki's PCHAIN
    strethaddress_to_identifier('0xB9bb08AB7E9Fa0A1356bd4A39eC0ca267E03b0b3'): 'PI',
    # Bittrex PLA should map to rotki's PlayChip
    strethaddress_to_identifier('0x0198f46f520F33cd4329bd4bE380a25a90536CD5'): 'PLA',
    # In Rotkehlchen LUNA-2 is Terra Luna but in Bittrex it's LUNA
    'LUNA-2': 'LUNA',
    # WASP in binance maps to WorldWideAssetExchange in rotki
    # In Rotkehlchen WorldWideAssetExchange is WAX but in Bittrex it's WASP
    strethaddress_to_identifier('0x39Bb259F66E1C59d5ABEF88375979b4D20D98022'): 'WAXP',
    # In Rotkehlchen Validity is RADS, the old name but in Bittrex it's VAL
    'RADS': 'VAL',
    # make sure bittrex matches ADX latest contract
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    # Bittrex AID maps to Aidcoin
    strethaddress_to_identifier('0x37E8789bB9996CaC9156cD5F5Fd32599E6b91289'): 'AID',
    # make sure bittrex matches ANT latest contract
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    # Bittrex CMCT maps to Crowdmachine
    strethaddress_to_identifier('0x47bc01597798DCD7506DCCA36ac4302fc93a8cFb'): 'CMCT',
    # Bittrex REV maps to REV (and not R)
    strethaddress_to_identifier('0x2ef52Ed7De8c5ce03a4eF0efbe9B7450F2D7Edc9'): 'REV',
    # make sure bittrex matches latest VRA contract
    strethaddress_to_identifier('0xF411903cbC70a74d22900a5DE66A2dda66507255'): 'VRA',
    # FET is Fetch AI in bittrex
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # make sure GNY maps to the appropriate token for bittrex
    strethaddress_to_identifier('0xb1f871Ae9462F1b2C6826E88A7827e76f86751d4'): 'GNY',
    # MTC is Metacoin in Bittrex
    'MTC-3': 'MTC',
    # EDG renamed to EDGELESS
    strethaddress_to_identifier('0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c'): 'EDGELESS',
    strethaddress_to_identifier('0xF970b8E36e23F7fC3FD752EeA86f8Be8D83375A6'): 'RCN',
    strethaddress_to_identifier('0x6F919D67967a97EA36195A2346d9244E60FE0dDB'): 'BLOC',
    strethaddress_to_identifier('0xc528c28FEC0A90C083328BC45f587eE215760A0F'): 'EDR',
    strethaddress_to_identifier('0xfAE4Ee59CDd86e3Be9e8b90b53AA866327D7c090'): 'CPC',
    # Tokenized coinbase in bittrex
    'COIN-2': 'COIN',
    strethaddress_to_identifier('0x15B543e986b8c34074DFc9901136d9355a537e7E'): 'STCCOIN',
    strethaddress_to_identifier('0x8f136Cc8bEf1fEA4A7b71aa2301ff1A52F084384'): 'STC',
    'MER': 'MER',
    # For some reason seems that XSILV and XGOLD are the same asset in bittrex
    strethaddress_to_identifier('0x670f9D9a26D3D42030794ff035d35a67AA092ead'): 'XGOLD',
    strethaddress_to_identifier('0x3b58c52C03ca5Eb619EBa171091c86C34d603e5f'): 'CYCLUB',
    strethaddress_to_identifier('0xE081b71Ed098FBe1108EA48e235b74F122272E68'): 'GOLD',
    strethaddress_to_identifier('0x13339fD07934CD674269726EdF3B5ccEE9DD93de'): 'CURIO',
    'YCE': 'MYCE',
    strethaddress_to_identifier('0xF56b164efd3CFc02BA739b719B6526A6FA1cA32a'): 'CGT',
    strethaddress_to_identifier('0x9b5161a41B58498Eb9c5FEBf89d60714089d2253'): 'MF1',
    strethaddress_to_identifier('0x765f0C16D1Ddc279295c1a7C24B0883F62d33F75'): 'DTX',
    strethaddress_to_identifier('0xfa5B75a9e13Df9775cf5b996A049D9cc07c15731'): 'VCK',
    strethaddress_to_identifier('0x653430560bE843C4a3D143d0110e896c2Ab8ac0D'): '_MOF',
    strethaddress_to_identifier('0x909E34d3f6124C324ac83DccA84b74398a6fa173'): 'ZKP',
    strethaddress_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419'): 'CTC',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
}

WORLD_TO_BITSTAMP = {
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
}

WORLD_TO_FTX = {
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    strethaddress_to_identifier('0xcca0c9c383076649604eE31b20248BC04FdF61cA'): 'ASD',
    'SOL-2': 'SOL',
    'COIN': 'COIN',
    # SLP is smooth love potion
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    'MER-2': 'MER',
    strethaddress_to_identifier('0x476c5E26a75bd202a9683ffD34359C0CC15be0fF'): 'SRM',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    'GENE': 'GENE',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',
    'LUNA-2': 'LUNA',
    strethaddress_to_identifier('0x3392D8A60B77F8d3eAa4FB58F09d835bD31ADD29'): 'INDI',
    strethaddress_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6'): 'STG',
    strethaddress_to_identifier('0x5c147e74D63B1D31AA3Fd78Eb229B65161983B2b'): 'WFLOW',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
}

WORLD_TO_POLONIEX = {
    # AIR-2 is aircoin for us and AIR is airtoken. Poloniex has only aircoin
    'AIR-2': 'AIR',
    # DEC in poloniex matches Decentr
    strethaddress_to_identifier('0x30f271C9E86D2B7d00a6376Cd96A1cFBD5F0b9b3'): 'DEC',
    # Poloniex delisted BCH and listed it as BCHABC after the Bitcoin Cash
    # ABC / SV fork. In Rotkehlchen we consider BCH to be the same as BCHABC
    'BCH': 'BCHABC',
    # Poloniex has the BCH Fork, Bitcoin Satoshi's vision listed as BCHSV.
    # We know it as BSV
    'BSV': 'BCHSV',
    # Caishen is known as CAI in Poloniex. This is before the swap to CAIX
    'CAIX': 'CAI',
    # CCN is Cannacoin in Poloniex but in Rotkehlchen we know it as CCN-2
    'CCN-2': 'CCN',
    # CCN is CustomContractNetwork in Rotkehlchen but does not exist in Cryptocompare
    # Putting it as conversion to make sure we don't accidentally ask for wrong price
    'CCN': '',
    'cUSDT': 'CUSDT',
    # Faircoin is known as FAIR outside of Poloniex. Seems to be the same as the
    # now delisted Poloniex's FAC if you look at the bitcointalk announcement
    # https://bitcointalk.org/index.php?topic=702675.0
    'FAIR': 'FAC',
    # KeyCoin in Poloniex is KEY but in Rotkehlchen it's KEY-3
    'KEY-3': 'KEY',
    # Mazacoin in Poloniex is MZC but in Rotkehlchen it's MAZA
    'MAZA': 'MZC',
    # Myriadcoin in Poloniex is MYR but in Rotkehlchen it's XMY
    'XMY': 'MYR',
    # NuBits in Poloniex is NBT but in Rotkehlchen it's USNBT
    'USNBT': 'NBT',
    # Stellar is XLM everywhere, apart from Poloniex
    'XLM': 'STR',
    # Poloniex still has the old name WC for WhiteCoin
    'XWC': 'WC',
    # Poloniex uses a different name for 1inch. Maybe due to starting with number?
    '1INCH': 'ONEINCH',
    # FTT is FTX token in poloniex
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    # TRB is Tellor Tributes in poloniex
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    # WINK is WIN in poloniex
    'WIN-3': 'WIN',
    # GTC is gitcoin in poloniex
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xfB7B4564402E5500dB5bB6d63Ae671302777C75a'): 'DEXT',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0x9E46A38F5DaaBe8683E10793b06749EEF7D733d1'): 'NCT',
    strethaddress_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419'): 'CTC',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'WLUNA',
}

WORLD_TO_KRAKEN = {
    'ATOM': 'ATOM',
    'ALGO': 'ALGO',
    'AUD': 'ZAUD',
    strethaddress_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'): 'BAT',
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): 'COMP',
    'DOT': 'DOT',
    'KAVA': 'KAVA',
    strethaddress_to_identifier('0xdeFA4e8a7bcBA345F687a2f1456F5Edd9CE97202'): 'KNC',
    'LINK': 'LINK',
    'BSV': 'BSV',
    'ETC': 'XETC',
    'ETH': 'XETH',
    'LTC': 'XLTC',
    # REP V1
    strethaddress_to_identifier('0x1985365e9f78359a9B6AD760e32412f4a445E862'): 'XREP',
    'BTC': 'XXBT',
    'XMR': 'XXMR',
    'XRP': 'XXRP',
    'ZEC': 'XZEC',
    'EUR': 'ZEUR',
    'USD': 'ZUSD',
    'GBP': 'ZGBP',
    'CAD': 'ZCAD',
    'JPY': 'ZJPY',
    'CHF': 'CHF',
    'KRW': 'ZKRW',
    'AED': 'AED',
    # REP V2
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REPV2',
    'DAO': 'XDAO',
    strethaddress_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892'): 'XMLN',
    'ICN': 'XICN',
    strethaddress_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96'): 'GNO',
    'BCH': 'BCH',
    'XLM': 'XXLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    strethaddress_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'): 'USDC',
    strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7'): 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'NMC': 'XNMC',
    'VEN': 'XXVN',
    'DOGE': 'XXDG',
    strethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F'): 'DAI',
    'XTZ': 'XTZ',
    'WAVES': 'WAVES',
    'ICX': 'ICX',
    'NANO': 'NANO',
    'OMG': 'OMG',
    'SC': 'SC',
    'PAXG': 'PAXG',
    'LSK': 'LSK',
    'TRX': 'TRX',
    'OXT': 'OXT',
    'STORJ': 'STORJ',
    strethaddress_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D'): 'BAL',
    'KSM': 'KSM',
    strethaddress_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52'): 'CRV',
    strethaddress_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'): 'SNX',
    'FIL': 'FIL',
    strethaddress_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'): 'UNI',
    strethaddress_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'): 'YFI',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    'KEEP': 'KEEP',
    'TBTC': 'TBTC',
    'ETH2': 'ETH2',
    strethaddress_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'): 'AAVE',
    'MANA': 'MANA',
    strethaddress_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7'): 'GRT',
    'FLOW': 'FLOW',
    'OCEAN': 'OCEAN',
    'EWT': 'EWT',
    strethaddress_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'): 'MATIC',
    strethaddress_to_identifier('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'): 'MKR',
    strethaddress_to_identifier('0xFca59Cd816aB1eaD66534D82bc21E7515cE441CF'): 'RARI',
    'REN': 'REN',
    strethaddress_to_identifier('0xE41d2489571d322189246DaFA5ebDe1F4699F498'): 'ZRX',
    strethaddress_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550'): 'GHST',
    strethaddress_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2'): 'SUSHI',
    strethaddress_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4'): 'ANKR',
    strethaddress_to_identifier('0x58b6A8A3302369DAEc383334672404Ee733aB239'): 'LPT',
    strethaddress_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0'): 'SAND',
    strethaddress_to_identifier('0x1F573D6Fb3F13d689FF844B4cE37794d79a7FF1C'): 'BNT',
    strethaddress_to_identifier('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'): 'ENJ',
    'MINA': 'MINA',
    'SRM': 'SRM',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x3506424F91fD33084466F402d5D97f05F8e3b4AF'): 'CHZ',
    strethaddress_to_identifier('0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26'): 'OGN',
    strethaddress_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447'): 'PERP',
    strethaddress_to_identifier('0xD417144312DbF50465b1C641d016962017Ef6240'): 'CQT',
    strethaddress_to_identifier('0xF5D669627376EBd411E34b98F19C868c8ABA5ADA'): 'AXS',
    'WBTC': 'WBTC',
    strethaddress_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D'): 'CTSI',
    strethaddress_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD'): 'LRC',
    'KAR': 'KAR',
    strethaddress_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d'): 'BADGER',
    strethaddress_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302'): '1INCH',
    strethaddress_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608'): 'MIR',
    strethaddress_to_identifier('0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55'): 'BAND',
    strethaddress_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30'): 'INJ',
    'MOVR': 'MOVR',
    'SDN': 'SDN',
    strethaddress_to_identifier('0x92D6C1e31e14520e676a687F0a93788B716BEff5'): 'DYDX',
    'OXY': 'OXY',
    'RAY': 'RAY',
    strethaddress_to_identifier('0x6c5bA91642F10282b576d91922Ae6448C9d52f4E'): 'PHA',
    'BNC': 'BNC',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'LUNA',
    strethaddress_to_identifier('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'): 'SHIB',
    'AVAX': 'AVAX',
    'KILT': 'KILT',
    'STEP': 'STEP',
    'UST': 'UST',
    'MNGO': 'MNGO',
    'ORCA': 'ORCA',
    'KINT': 'KINT',
    'GLMR': 'GLMR',
    'ATLAS': 'ATLAS',
    'ACA': 'ACA',
    'AIR': 'AIR',
    'POLIS': 'POLIS',
    'KIN': 'KIN',
    'FIDA': 'FIDA',
    'ASTR': 'ASTR',
    'AKT': 'AKT',
    'SGB': 'SGB',
    'SBR': 'SBR',
    strethaddress_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'): 'FXS',
    strethaddress_to_identifier('0xc7283b66Eb1EB5FB86327f08e1B5816b0720212B'): 'TRIBE',
    strethaddress_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6'): 'SPELL',
    strethaddress_to_identifier('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'): 'CVX',
    strethaddress_to_identifier('0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF'): 'ALCX',
    strethaddress_to_identifier('0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72'): 'ENS',
    strethaddress_to_identifier('0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44'): 'KP3R',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x25f8087EAD173b73D6e8B84329989A8eEA16CF73'): 'YGG',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    'ICP': 'ICP',
    strethaddress_to_identifier('0x0391D2021f89DC339F60Fff84546EA23E337750f'): 'BOND',
    strethaddress_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8'): 'ALICE',
    strethaddress_to_identifier('0x7dE91B204C1C737bcEe6F000AAA6569Cf7061cb7'): 'XRT',
    strethaddress_to_identifier('0x18aAA7115705e8be94bfFEBDE57Af9BFc265B998'): 'AUDIO',
    strethaddress_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'): 'WOO',
    strethaddress_to_identifier('0x7420B4b9a0110cdC71fB720908340C03F9Bc03EC'): 'JASMY',
    strethaddress_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B'): 'RNDR',
    strethaddress_to_identifier('0x4a220E6096B25EADb88358cb44068A3248254675'): 'QNT',
    strethaddress_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA'): 'GALA',
    strethaddress_to_identifier('0xfB5c6815cA3AC72Ce9F5006869AE67f18bF77006'): 'PSTAKE',
    strethaddress_to_identifier('0x4d224452801ACEd8B2F0aebE155379bb5D594381'): 'APE',
    strethaddress_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'): 'MASK',
    strethaddress_to_identifier('0x595832F8FC6BF59c85C527fEC3740A1b7a361269'): 'POWR',
    'SCRT': 'SCRT',
    strethaddress_to_identifier('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'): 'UMA',
    strethaddress_to_identifier('0x2e9d63788249371f1DFC918a52f8d799F4a38C94'): 'TOKE',
    strethaddress_to_identifier('0x65Ef703f5594D2573eb71Aaf55BC0CB548492df4'): 'MULTI',
    strethaddress_to_identifier('0xA4EED63db85311E22dF4473f87CcfC3DaDCFA3E3'): 'RBC',
    strethaddress_to_identifier('0x3a4f40631a4f906c2BaD353Ed06De7A5D3fCb430'): 'PLA',
    strethaddress_to_identifier('0xF17e65822b568B3903685a7c9F496CF7656Cc6C2'): 'BICO',
    strethaddress_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6'): 'MC',
    'MSOL': 'MSOL',
    'SAMO': 'SAMO',
    'GARI': 'GARI',
    'GST-2': 'GST',
    'GMT': 'GMT',
    'CFG': 'CFG',
    strethaddress_to_identifier('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'): 'WETH',
    strethaddress_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'): 'LDO',
    strethaddress_to_identifier('0x0b38210ea11411557c13457D4dA7dC6ea731B88a'): 'API3',
    'RUNE': 'RUNE',
    strethaddress_to_identifier('0x607F4C5BB672230e8672085532f7e901544a7375'): 'RLC',
    strethaddress_to_identifier('0xCdF7028ceAB81fA0C6971208e83fa7872994beE5'): 'T',
    strethaddress_to_identifier('0x32353A6C91143bfd6C7d363B546e62a9A2489A20'): 'AGLD',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0x525A8F6F3Ba4752868cde25164382BfbaE3990e1'): 'NYM',
    strethaddress_to_identifier('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671'): 'NMR',
    strethaddress_to_identifier('0xfA5047c9c78B8877af97BDcb85Db743fD7313d4a'): 'ROOK',
    strethaddress_to_identifier('0x41e5560054824eA6B0732E656E3Ad64E20e94E45'): 'CVC',
    strethaddress_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55'): 'SUPER',
    strethaddress_to_identifier('0x31c8EAcBFFdD875c74b94b077895Bd78CF1E64A3'): 'RAD',
    'NEAR': 'NEAR',
    strethaddress_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9'): 'SXP',
    'LUNA-3': 'LUNA2',
    strethaddress_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72'): 'TLM',
    strethaddress_to_identifier('0x3597bfD533a99c9aa083587B074434E61Eb0A258'): 'DENT',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    strethaddress_to_identifier('0x037A54AaB062628C9Bbae1FDB1583c195585fe41'): 'LCX',
    strethaddress_to_identifier('0xd084B83C305daFD76AE3E1b4E1F1fe2eCcCb3988'): 'TVK',
    strethaddress_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870'): 'FTM',
    strethaddress_to_identifier('0xB705268213D593B8FD88d3FDEFF93AFF5CbDcfAE'): 'IDEX',
    'BTT': 'BTT',
    strethaddress_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a'): 'REQ',
    strethaddress_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D'): 'CHR',
    strethaddress_to_identifier('0x77FbA179C79De5B7653F68b5039Af940AdA60ce0'): 'FORTH',
    strethaddress_to_identifier('0xef3A930e1FfFFAcd2fc13434aC81bD278B0ecC8d'): 'FIS',
    strethaddress_to_identifier('0x5Ca381bBfb58f0092df149bD3D243b08B9a8386e'): 'MXC',
    strethaddress_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D'): 'FARM',
    strethaddress_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d'): 'ACH',
    'MV': 'MV',
    'EGLD': 'EGLD',
    'UNFI': 'UNFI',
    'COTI': 'COTI',
    strethaddress_to_identifier('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7'): 'KEY',
    strethaddress_to_identifier('0x1A4b46696b2bB4794Eb3D4c26f1c55F9170fa4C5'): 'BIT',
    'INTR': 'INTR',
    'TEER': 'TEER',
}

WORLD_TO_BINANCE = {
    # When BCH forked to BCHABC and BCHSV, binance renamed the original to ABC
    'BCH': 'BCHABC',
    'BSV': 'BCHSV',
    # ETHOS is known as BQX in Binance
    strethaddress_to_identifier('0x5Af2Be193a6ABCa9c8817001F45744777Db30756'): 'BQX',
    # GXChain is GXS in Binance but GXC in Rotkehlchen
    'GXC': 'GXS',
    # Luna Terra is LUNA-2 in rotki
    'LUNA-2': 'LUNA',
    # YOYOW is known as YOYO in Binance
    strethaddress_to_identifier('0xcbeAEc699431857FDB4d37aDDBBdc20E132D4903'): 'YOYO',
    # Solana is SOL-2 in rotki
    'SOL-2': 'SOL',
    # BETH is the eth staked in beacon chain
    'ETH2': 'BETH',
    # STX is Blockstack in Binance
    'STX-2': 'STX',
    # ONE is Harmony in Binance
    'ONE-2': 'ONE',
    # FTT is FTX in Binance
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    # make sure binance matches ADX latest contract
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    # make sure binance matces ANT latest contract
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    # HOT is Holo in Binance
    strethaddress_to_identifier('0x6c6EE5e31d828De241282B9606C8e98Ea48526E2'): 'HOT',
    # Key is SelfKey in Binance
    strethaddress_to_identifier('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7'): 'KEY',
    # PNT is pNetwork in Binance
    strethaddress_to_identifier('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'): 'PNT',
    # FET is Fetch AI in Binance
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # TRB is Tellor Tributes in Binance
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    # WIN is WINk in Binance
    'WIN-3': 'WIN',
    strethaddress_to_identifier('0xF970b8E36e23F7fC3FD752EeA86f8Be8D83375A6'): 'RCN',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0xEA1ea0972fa092dd463f2968F9bB51Cc4c981D71'): 'MOD',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0x8f693ca8D21b157107184d29D398A8D082b38b76'): 'DATA',
    strethaddress_to_identifier('0x4824A7b64E3966B0133f4f4FFB1b9D6bEb75FFF7'): 'TCT',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
    strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7'): 'USDT',
    'NFT': 'APENFT',
}

WORLD_TO_BITFINEX = {
    'BCH': 'BCHN',
    'CNY': 'CNH',
    'DOGE': 'DOG',
    'LUNA-2': 'LUNA',
    'SOL-2': 'SOL',
    # make sure GNY maps to the appropriate token for bitfinex
    strethaddress_to_identifier('0xb1f871Ae9462F1b2C6826E88A7827e76f86751d4'): 'GNY',
    # make sure REP maps to latest one in bitfinex
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
    # TRIO is TRI in bitfinex
    strethaddress_to_identifier('0x8B40761142B9aa6dc8964e61D0585995425C3D94'): 'TRI',
    # ZB token is ZBT in bitfinex
    strethaddress_to_identifier('0xBd0793332e9fB844A52a205A233EF27a5b34B927'): 'ZBT',
    # GOT is parkingo in bitfinex
    strethaddress_to_identifier('0x613Fa2A6e6DAA70c659060E86bA1443D2679c9D7'): 'GOT',
    # make sure ANT maps to latest one in bitfinex
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    # PNT is pNetwork in bitfinex. Also original symbol is EDO there.
    strethaddress_to_identifier('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'): 'EDO',
    # ORS is orsgroup in bitfinex
    strethaddress_to_identifier('0xac2e58A06E6265F1Cf5084EE58da68e5d75b49CA'): 'ORS',
    # FTT is ftx in bitfinex
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    # FET is Fetch AI in bitfinex
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # TerraUSD is TERRAUST in bitfinex
    'UST': 'TERRAUST',
    strethaddress_to_identifier('0x8f693ca8D21b157107184d29D398A8D082b38b76'): 'DAT',
    'XEC': 'BCHABC',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    # Spankchain is SPK in bitfinex
    strethaddress_to_identifier('0x42d6622deCe394b54999Fbd73D108123806f6a18'): 'SPK',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EUT',
    strethaddress_to_identifier('0xC4f6E93AEDdc11dc22268488465bAbcAF09399aC'): 'HIX',
    'NFT': 'APENFT',
    'LUNA-3': 'LUNA2',
    strethaddress_to_identifier('0xF411903cbC70a74d22900a5DE66A2dda66507255'): 'VRA',
}

WORLD_TO_KUCOIN = {
    'BSV': 'BCHSV',
    'LUNA-2': 'LUNA',
    # make sure Veracity maps to latest one in kucoin
    strethaddress_to_identifier('0xF411903cbC70a74d22900a5DE66A2dda66507255'): 'VRA',
    # KEY is selfkey in kucoin
    strethaddress_to_identifier('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7'): 'KEY',
    # MTC is doc.com in kucoin
    strethaddress_to_identifier('0x905E337c6c8645263D3521205Aa37bf4d034e745'): 'MTC',
    # R is revain in kucoin
    strethaddress_to_identifier('0x2ef52Ed7De8c5ce03a4eF0efbe9B7450F2D7Edc9'): 'R',
    # FET is Fetch AI in Kucoin
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # As reported in #2805 CAPP refers to this token
    strethaddress_to_identifier('0x11613b1f840bb5A40F8866d857e24DA126B79D73'): 'CAPP',
    strethaddress_to_identifier('0x6F919D67967a97EA36195A2346d9244E60FE0dDB'): 'BLOC',
    'WIN-3': 'WIN',
    'STX-2': 'STX',
    strethaddress_to_identifier('0xfAE4Ee59CDd86e3Be9e8b90b53AA866327D7c090'): 'CPC',
    'ONE-2': 'ONE',
    strethaddress_to_identifier('0xf4CD3d3Fda8d7Fd6C5a500203e38640A70Bf9577'): 'YFDAI',
    strethaddress_to_identifier('0xcca0c9c383076649604eE31b20248BC04FdF61cA'): 'ASD',
    strethaddress_to_identifier('0xEA1ea0972fa092dd463f2968F9bB51Cc4c981D71'): 'MODEFI',
    strethaddress_to_identifier('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'): 'KICK',
    strethaddress_to_identifier('0x15B543e986b8c34074DFc9901136d9355a537e7E'): 'STC',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA'): 'GALAX',
    strethaddress_to_identifier('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'): 'PNT',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xc221b7E65FfC80DE234bbB6667aBDd46593D34F0'): 'CFG',  # using wrapped centrifuge for now  # noqa: E501
    strethaddress_to_identifier('0x88df592f8eb5d7bd38bfef7deb0fbc02cf3778a0'): 'TRB',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    'EDG-2': 'EDG',
    strethaddress_to_identifier('0x8f693ca8D21b157107184d29D398A8D082b38b76'): 'DATA',
    strethaddress_to_identifier('0xAA2ce7Ae64066175E0B90497CE7d9c190c315DB4'): 'SUTER',
    'RMRK': 'RMRK',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x3106a0a076BeDAE847652F42ef07FD58589E001f'): 'ADS',
    strethaddress_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419'): 'CTC',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
    strethaddress_to_identifier('0xDaF88906aC1DE12bA2b1D2f7bfC94E9638Ac40c4'): 'EPK',
    'ARN': 'ARNM',
    strethaddress_to_identifier('0xC775C0C30840Cb9F51e21061B054ebf1A00aCC29'): 'PSL',
    strethaddress_to_identifier('0x29d578CEc46B50Fa5C88a99C6A4B70184C062953'): 'EVER',
}

WORLD_TO_ICONOMI = {
    # In Rotkehlchen LUNA-2 is Terra Luna but in Iconomi it's LUNA
    'LUNA-2': 'LUNA',
    # make sure iconomi matches ADX latest contract
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    # make sure iconomi matces ANT latest contract
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    # make sure iconomi matces REP latest contract
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
    # FTT is ftx in iconomi
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    # HOT is Holo chain token in iconomi
    strethaddress_to_identifier('0x6c6EE5e31d828De241282B9606C8e98Ea48526E2'): 'HOT',
    # PNT is pNetwork in iconomi
    strethaddress_to_identifier('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'): 'PNT',
    # FET is Fetch AI in iconomi
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # TRB is Tellor Tributes in iconomi
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    # EDG is Edgeless in iconomi
    strethaddress_to_identifier('0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c'): 'EDG',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xF970b8E36e23F7fC3FD752EeA86f8Be8D83375A6'): 'RCN',
    'ONE-2': 'ONE',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'): 'FXS',
}

WORLD_TO_COINBASE_PRO = {
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'WLUNA',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0x0391D2021f89DC339F60Fff84546EA23E337750f'): 'BOND',
    strethaddress_to_identifier('0x2565ae0385659badCada1031DB704442E1b69982'): 'ASM',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x4C19596f5aAfF459fA38B0f7eD92F11AE6543784'): 'TRU',
    strethaddress_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D'): 'FARM',
    'STX-2': 'STX',
    strethaddress_to_identifier('0x9E46A38F5DaaBe8683E10793b06749EEF7D733d1'): 'NCT',
    strethaddress_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892'): 'MLN',
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
    strethaddress_to_identifier('0xfB7B4564402E5500dB5bB6d63Ae671302777C75a'): 'DEXT',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
}

WORLD_TO_COINBASE = {
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0x32353A6C91143bfd6C7d363B546e62a9A2489A20'): 'AGLD',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0x4C19596f5aAfF459fA38B0f7eD92F11AE6543784'): 'TRU',
    strethaddress_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D'): 'FARM',
    'STX-2': 'STX',
    strethaddress_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892'): 'MLN',
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
}

WORLD_TO_UPHOLD = {
    'BTC': 'BTC',
    strethaddress_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'): 'AAVE',
    'XRP': 'XRP',
    'ETH': 'ETH',
    strethaddress_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'): 'BAT',
    'ADA': 'ADA',
    'ATOM': 'ATOM',
    'BCH': 'BCH',
    'BAL': 'BAL',
    'BTG': 'BTG',  # Bitcoin Gold
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): 'COMP',
    'DASH': 'DASH',
    'DCR': 'DCR',
    'DGB': 'DGB',
    'DOGE': 'DOGE',
    'DOT': 'DOT',
    strethaddress_to_identifier('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'): 'ENJ',
    'EOS': 'EOS',
    'FIL': 'FIL',
    'FLOW': 'FLOW',
    strethaddress_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7'): 'GRT',
    'HBAR': 'HBAR',
    'HNT': 'HNT',
    'IOTA': 'MIOTA',
    strethaddress_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA'): 'LINK',
    'LTC': 'LTC',
    strethaddress_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'): 'MATIC',
    strethaddress_to_identifier('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'): 'MKR',
    'NANO': 'NANO',
    'NEO': 'NEO',
    strethaddress_to_identifier('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'): 'OMG',
    strethaddress_to_identifier('0x4575f41308EC1483f3d399aa9a2826d74Da13Deb'): 'OXT',
    strethaddress_to_identifier('0x408e41876cCCDC0F92210600ef50372656052a38'): 'REN',
    strethaddress_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'): 'SNX',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x476c5E26a75bd202a9683ffD34359C0CC15be0fF'): 'SRM',
    strethaddress_to_identifier('0x3883f5e181fccaF8410FA61e12b59BAd963fb645'): 'THETA',
    strethaddress_to_identifier('0xf230b790E05390FC8295F4d3F60332c93BEd42e2'): 'TRX',
    'VET': 'VET',
    strethaddress_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'): 'WBTC',
    strethaddress_to_identifier('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'): 'UMA',
    strethaddress_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'): 'UNI',
    # 'UPT': 'UPT',
    'XCH': 'XCH',
    'XEM': 'NEM',
    'XLM': 'XLM',
    'XTZ': 'XTZ',
    strethaddress_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27'): 'ZIL',
    strethaddress_to_identifier('0xE41d2489571d322189246DaFA5ebDe1F4699F498'): 'ZRX',
}

WORLD_TO_GEMINI = {
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0x18aAA7115705e8be94bfFEBDE57Af9BFc265B998'): 'AUDIO',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'LUNA',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e'): 'METI',
}

WORLD_TO_NEXO = {
    strethaddress_to_identifier('0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206'): 'NEXONEXO',
    'GBP': 'GBPX',
    strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7'): 'USDTERC',
}

WORLD_TO_BITPANDA = {
    'IOTA': 'MIOTA',
    strethaddress_to_identifier('0x536381a8628dBcC8C70aC9A30A7258442eAb4c92'): 'PAN',  # Pantos
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',  # ANT v2
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',  # AXS v2
    'SOL-2': 'SOL',  # Solana
    'LUNA-2': 'LUNA',  # Luna Terra
}

WORLD_TO_CRYPTOCOM = {
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    'LUNA-2': 'LUNA',
}

# Create a generic variable that can be 'Asset', or any subclass.
Z = TypeVar('Z', bound='Asset')


@total_ordering
@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Asset():
    identifier: str
    form_with_incomplete_data: InitVar[bool] = field(default=False)
    direct_field_initialization: InitVar[bool] = field(default=False)
    name: str = field(init=False)
    symbol: str = field(init=False)
    asset_type: AssetType = field(init=False)
    started: Optional[Timestamp] = field(init=False)
    forked: Optional['Asset'] = field(init=False)
    swapped_for: Optional['Asset'] = field(init=False)
    # None means no special mapping. '' means not supported
    cryptocompare: Optional[str] = field(init=False)
    coingecko: Optional[str] = field(init=False)

    def __post_init__(
            self,
            form_with_incomplete_data: bool = False,
            direct_field_initialization: bool = False,
    ) -> None:
        """
        Asset post initialization

        The only thing that is given to initialize an asset is a string.

        If a non string is given then it's probably a deserialization error or
        invalid data were given to us by the server if an API was queried.

        If `form_with_incomplete_data` is given and is True then we allow the generation
        of an asset object even if the corresponding underlying object is missing
        important data such as name, symbol, token decimals etc. In most case this
        is not wanted except for some exception like passing in some functions for
        icon generation.

        May raise UnknownAsset if the asset identifier can't be matched to anything
        """
        if not isinstance(self.identifier, str):
            raise DeserializationError(
                'Tried to initialize an asset out of a non-string identifier',
            )

        if self.identifier.startswith(NFT_DIRECTIVE):  # probably should subclass better
            object.__setattr__(self, 'name', f'nft with id {self.identifier}')
            object.__setattr__(self, 'symbol', self.identifier[len(NFT_DIRECTIVE):])
            object.__setattr__(self, 'asset_type', AssetType.NFT)
            object.__setattr__(self, 'started', 0)
            object.__setattr__(self, 'forked', None)
            object.__setattr__(self, 'swapped_for', None)
            object.__setattr__(self, 'cryptocompare', '')
            object.__setattr__(self, 'coingecko', None)
            return

        if direct_field_initialization:
            return

        # TODO: figure out a way to move this out. Moved in here due to cyclic imports
        from rotkehlchen.assets.resolver import AssetResolver  # isort:skip  # noqa: E501  # pylint: disable=import-outside-toplevel
        data = AssetResolver().get_asset_data(self.identifier, form_with_incomplete_data)
        # make sure same case of identifier as in  DB is saved in the structure
        object.__setattr__(self, 'identifier', data.identifier)
        # Ugly hack to set attributes of a frozen data class as post init
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'name', data.name)
        object.__setattr__(self, 'symbol', data.symbol)
        object.__setattr__(self, 'asset_type', data.asset_type)
        object.__setattr__(self, 'started', data.started)
        forked = None
        if data.forked is not None:
            try:
                forked = Asset(data.forked)
            except UnknownAsset:  # should not happen due to foreign keys
                log.error(f'Forked asset {data.forked} for {self.identifier} could not be found')
        object.__setattr__(self, 'forked', forked)
        swapped_for = None
        if data.swapped_for is not None:
            try:
                swapped_for = Asset(data.swapped_for)
            except UnknownAsset:  # should not happen due to foreign keys
                log.error(f'Swapped for asset {data.swapped_for} for {self.identifier} could not be found')  # noqa: E501
        object.__setattr__(self, 'swapped_for', swapped_for)
        object.__setattr__(self, 'cryptocompare', data.cryptocompare)
        object.__setattr__(self, 'coingecko', data.coingecko)

    def serialize(self) -> str:
        return self.identifier

    def is_fiat(self) -> bool:
        return self.asset_type == AssetType.FIAT

    def is_evm_token(self) -> bool:
        return self.asset_type == AssetType.EVM_TOKEN

    def __str__(self) -> str:
        if self.is_evm_token():
            token = EvmToken.from_asset(self)
            assert token, 'Token should exist here'
            return str(token)
        return f'{self.symbol}({self.name})'

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name} symbol:{self.symbol}>'

    def to_kraken(self) -> str:
        return WORLD_TO_KRAKEN[self.identifier]

    def to_bitfinex(self) -> str:
        return WORLD_TO_BITFINEX.get(self.identifier, self.identifier)

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.identifier, self.identifier)

    def to_binance(self) -> str:
        return WORLD_TO_BINANCE.get(self.identifier, self.identifier)

    def to_cryptocompare(self) -> str:
        """Returns the symbol with which to query cryptocompare for the asset

        May raise:
            - UnsupportedAsset() if the asset is not supported by cryptocompare
        """
        cryptocompare_str = self.symbol if self.cryptocompare is None else self.cryptocompare
        # There is an asset which should not be queried in cryptocompare
        if cryptocompare_str is None or cryptocompare_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

        # Seems cryptocompare capitalizes everything. So cDAI -> CDAI
        return cryptocompare_str.upper()

    def to_coingecko(self) -> str:
        """Returns the symbol with which to query coingecko for the asset

        May raise:
            - UnsupportedAsset() if the asset is not supported by coingecko
        """
        coingecko_str = '' if self.coingecko is None else self.coingecko
        # This asset has no coingecko mapping
        if coingecko_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by coingecko')
        return coingecko_str

    def has_coingecko(self) -> bool:
        return self.coingecko is not None and self.coingecko != ''

    def has_oracle(self) -> bool:
        return self.has_coingecko() or self.cryptocompare is not None

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if isinstance(other, Asset):
            return self.identifier.lower() == other.identifier.lower()
        if isinstance(other, str):
            return self.identifier.lower() == other.lower()
        # else
        raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Asset):
            return self.identifier < other.identifier
        if isinstance(other, str):
            return self.identifier < other
        # else
        raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def to_dict(self) -> Dict[str, Any]:
        """Returns an exportable json representation for an asset"""
        forked, swapped_for = None, None
        if self.forked is not None:
            forked = self.forked.identifier
        if self.swapped_for is not None:
            swapped_for = self.swapped_for.identifier

        asset_dict: Dict[str, Any] = {
            'identifier': self.identifier,
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': str(self.asset_type),
            'started': self.started,
            'forked': forked,
            'swapped_for': swapped_for,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
        }

        if self.is_evm_token():
            asset_as_token = EvmToken.from_asset(self)
            if asset_as_token is None:
                return asset_dict
            underlying = None
            if asset_as_token.underlying_tokens is not None:
                underlying = [token.serialize() for token in asset_as_token.underlying_tokens]
            asset_dict |= {
                'evm_address': asset_as_token.evm_address,
                'decimals': asset_as_token.decimals,
                'protocol': asset_as_token.protocol,
                'underlying_tokens': underlying,
            }

        return asset_dict

    @classmethod
    def initialize(
            cls: Type[Z],
            identifier: str,
            asset_type: AssetType,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            started: Optional[Timestamp] = None,
            forked: Optional['Asset'] = None,
            swapped_for: Optional['Asset'] = None,
            coingecko: Optional[str] = None,
            # add the asset with inactive cryptocompare so querying is not attempted by symbol
            cryptocompare: Optional[str] = '',
    ) -> Z:
        """Initialize an asset from fields"""
        asset = cls('whatever', direct_field_initialization=True)
        object.__setattr__(asset, 'identifier', identifier)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'asset_type', asset_type)
        object.__setattr__(asset, 'started', started)
        object.__setattr__(asset, 'forked', forked)
        object.__setattr__(asset, 'swapped_for', swapped_for)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        return asset


EthereumTokenDBTuple = Tuple[
    str,                  # identifier
    str,                  # address
    str,                  # chain id
    str,                  # token type
    Optional[int],        # decimals
    Optional[str],        # name
    Optional[str],        # symbol
    Optional[int],        # started
    Optional[str],        # swapped_for
    Optional[str],        # coingecko
    Optional[str],        # cryptocompare
    Optional[str],        # protocol
]


# Create a generic variable that can be 'HasEvmToken', or any subclass.
Y = TypeVar('Y', bound='HasEvmToken')


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class HasEvmToken(Asset):
    """Marker to denote assets having an EVM token address"""
    evm_address: ChecksumEvmAddress = field(init=False)
    chain: ChainID = field(init=False)
    token_kind: EvmTokenKind = field(init=False)
    decimals: int = field(init=False)
    protocol: str = field(init=False)
    underlying_tokens: List[UnderlyingToken] = field(init=False)

    def __post_init__(
            self,
            form_with_incomplete_data: bool = False,
            direct_field_initialization: bool = False,
    ) -> None:
        if direct_field_initialization:
            return

        object.__setattr__(self, 'identifier', self.identifier)
        super().__post_init__(form_with_incomplete_data)
        # TODO: figure out a way to move this out. Moved in here due to cyclic imports
        from rotkehlchen.assets.resolver import AssetResolver  # isort:skip  # noqa: E501  # pylint: disable=import-outside-toplevel
        from rotkehlchen.globaldb import GlobalDBHandler  # isort:skip  # noqa: E501  # pylint: disable=import-outside-toplevel

        data = AssetResolver().get_asset_data(self.identifier)  # pylint: disable=no-member

        if data.evm_address is None:
            raise DeserializationError(
                'Tried to initialize a non Ethereum asset as Ethereum Token',
            )
        object.__setattr__(self, 'evm_address', data.evm_address)
        object.__setattr__(self, 'chain', data.chain)
        object.__setattr__(self, 'token_kind', data.token_kind)
        object.__setattr__(self, 'decimals', data.decimals)
        object.__setattr__(self, 'protocol', data.protocol)

        with GlobalDBHandler().conn.read_ctx() as cursor:
            underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(cursor, data.identifier)  # noqa: E501
        object.__setattr__(self, 'underlying_tokens', underlying_tokens)

    def serialize_all_info(self) -> Dict[str, Any]:
        underlying_tokens = [x.serialize() for x in self.underlying_tokens] if self.underlying_tokens is not None else None  # noqa: E501
        return {
            'identifier': self.identifier,
            'address': self.evm_address,
            'chain': self.chain.serialize(),
            'token_kind': self.token_kind.serialize(),
            'decimals': self.decimals,
            'name': self.name,
            'symbol': self.symbol,
            'started': self.started,
            'swapped_for': self.swapped_for.identifier if self.swapped_for else None,
            'coingecko': self.coingecko,
            'cryptocompare': self.cryptocompare,
            'protocol': self.protocol,
            'underlying_tokens': underlying_tokens,
        }

    @classmethod
    def initialize(  # type: ignore  # figure out a way to make mypy happy
            cls: Type[Y],
            address: ChecksumEvmAddress,
            chain: ChainID,
            token_kind: EvmTokenKind,
            decimals: Optional[int] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            started: Optional[Timestamp] = None,
            swapped_for: Optional[Asset] = None,
            coingecko: Optional[str] = None,
            # add the token with inactive cryptocompare so querying is not attempted by symbol
            cryptocompare: Optional[str] = '',
            protocol: Optional[str] = None,
            underlying_tokens: Optional[List[UnderlyingToken]] = None,
    ) -> Y:
        """Initialize a token from fields"""
        token = cls('whatever', direct_field_initialization=True)
        identifier = evm_address_to_identifier(
            address=address,
            chain=chain,
            token_type=token_kind,
        )
        object.__setattr__(token, 'identifier', identifier)
        object.__setattr__(token, 'name', name)
        object.__setattr__(token, 'symbol', symbol)
        object.__setattr__(token, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(token, 'started', started)
        object.__setattr__(token, 'forked', None)
        object.__setattr__(token, 'swapped_for', swapped_for)
        object.__setattr__(token, 'cryptocompare', cryptocompare)
        object.__setattr__(token, 'coingecko', coingecko)
        object.__setattr__(token, 'evm_address', address)
        object.__setattr__(token, 'chain', chain)
        object.__setattr__(token, 'token_kind', token_kind)
        object.__setattr__(token, 'evm_address', address)
        object.__setattr__(token, 'decimals', decimals)
        object.__setattr__(token, 'protocol', protocol)
        object.__setattr__(token, 'underlying_tokens', underlying_tokens)
        return token

    @classmethod
    def deserialize_from_db(
            cls: Type[Y],
            entry: EthereumTokenDBTuple,
            underlying_tokens: Optional[List[UnderlyingToken]] = None,
    ) -> Y:
        """May raise UnknownAsset if the swapped for asset can't be recognized

        That error would be bad because it would mean somehow an unknown id made it into the DB
        """
        swapped_for = Asset(entry[8]) if entry[8] is not None else None
        return cls.initialize(
            address=entry[1],  # type: ignore
            chain=ChainID.deserialize_from_db(entry[2]),
            token_kind=EvmTokenKind.deserialize_from_db(entry[3]),
            decimals=entry[4],
            name=entry[5],
            symbol=entry[6],
            started=Timestamp(entry[7]),  # type: ignore
            swapped_for=swapped_for,
            coingecko=entry[9],
            cryptocompare=entry[10],
            protocol=entry[11],
            underlying_tokens=underlying_tokens,
        )


# Create a generic variable that can be 'EvmToken', or any subclass.
T = TypeVar('T', bound='EvmToken')


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class EvmToken(HasEvmToken):

    def __str__(self) -> str:
        return f'{self.symbol}({self.evm_address} @ {self.chain})'

    @classmethod
    def from_asset(
            cls: Type[T],
            asset: Asset,
            form_with_incomplete_data: bool = True,
    ) -> Optional[T]:
        """Attempts to turn an asset into an EvmToken. If it fails returns None"""
        return cls.from_identifier(
            identifier=asset.identifier,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    @classmethod
    def from_identifier(
            cls: Type[T],
            identifier: str,
            form_with_incomplete_data: bool = True,
    ) -> Optional[T]:
        """Attempts to turn an asset into an EvmToken. If it fails returns None"""
        try:
            return cls(
                identifier,
                form_with_incomplete_data=form_with_incomplete_data,
            )
        except DeserializationError:
            return None
