import abc
import logging
from dataclasses import InitVar, dataclass, field
from functools import total_ordering
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Type, Union

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.resolver import (
    ChainID,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, Timestamp

from .types import ASSETS_WITH_NO_CRYPTO_ORACLES, AssetType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UnderlyingTokenDBTuple = Tuple[str, str, str]


class UnderlyingToken(NamedTuple):
    """Represents an underlying token of a token

    Is used for pool tokens, tokensets etc.
    """
    address: ChecksumEvmAddress
    token_kind: EvmTokenKind
    weight: FVal  # Floating percentage from 0 to 1

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'token_kind': self.token_kind.serialize(),
            'weight': str(self.weight * 100),
        }

    @classmethod
    def deserialize_from_db(cls, entry: UnderlyingTokenDBTuple) -> 'UnderlyingToken':
        return UnderlyingToken(
            address=entry[0],  # type: ignore
            token_kind=EvmTokenKind.deserialize_from_db(entry[1]),
            weight=FVal(entry[2]),
        )

    def get_identifier(self, parent_chain: ChainID) -> str:
        return evm_address_to_identifier(
            address=str(self.address),
            chain=parent_chain,
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
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0xe0cCa86B254005889aC3a81e737f56a14f4A38F5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALTA',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0xeDF6568618A00C6F0908Bf7758A16F76B6E04aF9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARIA20',  # noqa: E501
    evm_address_to_identifier('0xdacD69347dE42baBfAEcD09dC88958378780FB62', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ATRI',  # noqa: E501
    evm_address_to_identifier('0xB90cb79B72EB10c39CbDF86e50B1C89F6a235f2e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AUDT',  # noqa: E501
    evm_address_to_identifier('0xd7c302fc3ac829C7E896a32c4Bd126f3e8Bd0a1f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'B2M',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0x33D0568941C0C64ff7e0FB4fbA0B11BD37deEd9f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RAMP',  # noqa: E501
    evm_address_to_identifier('0x459086F2376525BdCebA5bDDA135e4E9d3FeF5bf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RENBTC',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0x0AbdAce70D3790235af448C88547603b945604ea', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DNT',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0xEe9801669C6138E84bD50dEB500827b776777d28', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'O3',  # noqa: E501
    evm_address_to_identifier('0x47b9F01B16E9C9cb99191DCA68c9cc5bF6403957', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ONSTON',  # noqa: E501
    evm_address_to_identifier('0x8642A849D0dcb7a15a974794668ADcfbe4794B56', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PROS',  # noqa: E501
    evm_address_to_identifier('0x9534ad65fb398E27Ac8F4251dAe1780B989D136e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PYR',  # noqa: E501
    evm_address_to_identifier('0x33D0568941C0C64ff7e0FB4fbA0B11BD37deEd9f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RAMP',  # noqa: E501
    evm_address_to_identifier('0x459086F2376525BdCebA5bDDA135e4E9d3FeF5bf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RENBTC',  # noqa: E501
    evm_address_to_identifier('0x557B933a7C2c45672B610F8954A3deB39a51A8Ca', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REVV',  # noqa: E501
    evm_address_to_identifier('0xD291E7a03283640FDc51b121aC401383A46cC623', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RGT',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x340D2bdE5Eb28c1eed91B2f790723E3B160613B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEE',  # noqa: E501
    evm_address_to_identifier('0x1b793E49237758dBD8b752AFC9Eb4b329d5Da016', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VITE',  # noqa: E501
    evm_address_to_identifier('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VSP',  # noqa: E501
    evm_address_to_identifier('0x7659CE147D0e714454073a5dd7003544234b6Aa0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCAD',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
}

WORLD_TO_BITSTAMP = {
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    'SOL-2': 'SOL',
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501

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
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMPL',  # noqa: E501
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
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ONEINCH',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMPL',  # noqa: E501
    evm_address_to_identifier('0x4Fabb145d64652a948d72533023f6E7A623C7C53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BUSD',  # noqa: E501
    evm_address_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GHST',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LUSD',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WETH',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0x77777FeDdddFfC19Ff86DB637967013e6C6A116C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TORN',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    'LUNA-2': 'LUNA',
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x71Ab77b7dbB4fa7e017BC15090b2163221420282', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HIGH',  # noqa: E501
    evm_address_to_identifier('0x853d955aCEf822Db058eb8505911ED77F175b99e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRAX',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x635d081fD8F6670135D8a3640E2cF78220787d56', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ADD',  # noqa: E501
    evm_address_to_identifier('0x3301Ee63Fb29F863f2333Bd4466acb46CD8323E6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AKITA',  # noqa: E501
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0xb056c38f6b7Dc4064367403E26424CD2c60655e1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEEK',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CHR',  # noqa: E501
    evm_address_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CLV',  # noqa: E501
    evm_address_to_identifier('0xca1207647Ff814039530D7d35df0e1Dd2e91Fa84', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DHT',  # noqa: E501
    evm_address_to_identifier('0xf8E9F10c22840b613cdA05A0c5Fdb59A4d6cd7eF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ELON',  # noqa: E501
    evm_address_to_identifier('0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DIA',  # noqa: E501
    evm_address_to_identifier('0x961C8c0B1aaD0c0b10a51FeF6a867E3091BCef17', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DYP',  # noqa: E501
    evm_address_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FARM',  # noqa: E501
    evm_address_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRONT',  # noqa: E501
    evm_address_to_identifier('0x6531f133e6DeeBe7F2dcE5A0441aA7ef330B4e53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIME',  # noqa: E501
    evm_address_to_identifier('0x43f11c02439e2736800433b4594994Bd43Cd066D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FLOKI',  # noqa: E501
    evm_address_to_identifier('0x37941b3Fdb2bD332e667D452a58Be01bcacb923e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FREN',  # noqa: E501
    evm_address_to_identifier('0xfffffffFf15AbF397dA76f1dcc1A1604F45126DB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FSW',  # noqa: E501
    evm_address_to_identifier('0xD9016A907Dc0ECfA3ca425ab20B6b785B42F2373', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GMEE',  # noqa: E501
    evm_address_to_identifier('0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HEX',  # noqa: E501
    evm_address_to_identifier('0x0b15Ddf19D47E6a86A56148fb4aFFFc6929BcB89', ChainID.BINANCE, EvmTokenKind.ERC20): 'IDIA',  # noqa: E501
    evm_address_to_identifier('0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MAGIC',  # noqa: E501
    evm_address_to_identifier('0x9B99CcA871Be05119B2012fd4474731dd653FEBe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATTER',  # noqa: E501
    evm_address_to_identifier('0xCC4304A31d09258b0029eA7FE63d032f52e44EFe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SWAP',  # noqa: E501
    evm_address_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TLM',  # noqa: E501
    evm_address_to_identifier('0x6F87D756DAf0503d08Eb8993686c7Fc01Dc44fB1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRADE',  # noqa: E501
    evm_address_to_identifier('0x6fC13EACE26590B80cCCAB1ba5d51890577D83B2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UMB',  # noqa: E501
    evm_address_to_identifier('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VSP',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0x7659CE147D0e714454073a5dd7003544234b6Aa0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCAD',  # noqa: E501
    evm_address_to_identifier('0xF55a93b613D172b86c2Ba3981a849DaE2aeCDE2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFX',  # noqa: E501
    evm_address_to_identifier('0x6781a0F84c7E9e846DCb84A9a5bd49333067b104', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZAP',  # noqa: E501
    evm_address_to_identifier('0xaf9f549774ecEDbD0966C52f250aCc548D3F36E5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RFUEL',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x0Ae055097C6d159879521C384F1D2123D1f195e6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STAKE',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUPER',  # noqa: E501
    evm_address_to_identifier('0x557B933a7C2c45672B610F8954A3deB39a51A8Ca', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REVV',  # noqa: E501
    evm_address_to_identifier('0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIM',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MTA',  # noqa: E501
    evm_address_to_identifier('0xEe9801669C6138E84bD50dEB500827b776777d28', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'O3',  # noqa: E501
    evm_address_to_identifier('0x2baEcDf43734F22FD5c152DB08E3C27233F0c7d2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OM',  # noqa: E501
    evm_address_to_identifier('0x47b9F01B16E9C9cb99191DCA68c9cc5bF6403957', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ONSTON',  # noqa: E501
    evm_address_to_identifier('0x3C6ff50c9Ec362efa359317009428d52115fe643', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERX',  # noqa: E501
    evm_address_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLS',  # noqa: E501
    evm_address_to_identifier('0xcAfE001067cDEF266AfB7Eb5A286dCFD277f3dE5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PSP',  # noqa: E501
    evm_address_to_identifier('0x9534ad65fb398E27Ac8F4251dAe1780B989D136e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PYR',  # noqa: E501
    evm_address_to_identifier('0xFE3E6a25e6b192A42a44ecDDCd13796471735ACf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REEF',  # noqa: E501
    evm_address_to_identifier('0xFE2786D7D1cCAb8B015f6Ef7392F67d778f8d8D7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PRQ',  # noqa: E501
    evm_address_to_identifier('0x4e352cF164E64ADCBad318C3a1e222E9EBa4Ce42', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MCB',  # noqa: E501
    evm_address_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MC',  # noqa: E501
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
    'eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978': 'DAR',
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMPL',  # noqa: E501
    evm_address_to_identifier('0x4Fabb145d64652a948d72533023f6E7A623C7C53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BUSD',  # noqa: E501
    evm_address_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GHST',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LUSD',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WETH',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0x77777FeDdddFfC19Ff86DB637967013e6C6A116C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TORN',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x71Ab77b7dbB4fa7e017BC15090b2163221420282', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HIGH',  # noqa: E501
    evm_address_to_identifier('0x853d955aCEf822Db058eb8505911ED77F175b99e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRAX',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSD',  # noqa: E501
    evm_address_to_identifier('0x33D0568941C0C64ff7e0FB4fbA0B11BD37deEd9f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RAMP',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DIA',  # noqa: E501
    evm_address_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FARM',  # noqa: E501
    evm_address_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MC',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUPER',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0xFE3E6a25e6b192A42a44ecDDCd13796471735ACf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REEF',  # noqa: E501
    evm_address_to_identifier('0x9534ad65fb398E27Ac8F4251dAe1780B989D136e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PYR',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0x1b793E49237758dBD8b752AFC9Eb4b329d5Da016', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VITE',  # noqa: E501
    evm_address_to_identifier('0xb5A73f5Fc8BbdbcE59bfD01CA8d35062e0dad801', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERL',  # noqa: E501
    evm_address_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLS',  # noqa: E501
    evm_address_to_identifier('0x459086F2376525BdCebA5bDDA135e4E9d3FeF5bf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RENBTC',  # noqa: E501
    evm_address_to_identifier('0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DODO',  # noqa: E501
    evm_address_to_identifier('0x1FCdcE58959f536621d76f5b7FfB955baa5A672F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FOR',  # noqa: E501
    evm_address_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRONT',  # noqa: E501
    evm_address_to_identifier('0x103c3A209da59d3E7C4A89307e66521e081CFDF0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GVT',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
    evm_address_to_identifier('0x3E9BC21C9b189C09dF3eF1B824798658d5011937', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINA',  # noqa: E501
    evm_address_to_identifier('0x3DB6Ba6ab6F95efed1a6E794caD492fAAabF294D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LTO',  # noqa: E501
    evm_address_to_identifier('0x65Ef703f5594D2573eb71Aaf55BC0CB548492df4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MULTI',  # noqa: E501
    evm_address_to_identifier('0x809826cceAb68c387726af962713b64Cb5Cb3CCA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NCASH',  # noqa: E501
    evm_address_to_identifier('0x2baEcDf43734F22FD5c152DB08E3C27233F0c7d2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OM',  # noqa: E501
    evm_address_to_identifier('0xfc82bb4ba86045Af6F327323a46E80412b91b27d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PROM',  # noqa: E501
    evm_address_to_identifier('0x8642A849D0dcb7a15a974794668ADcfbe4794B56', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PROS',  # noqa: E501
    evm_address_to_identifier('0xD291E7a03283640FDc51b121aC401383A46cC623', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RGT',  # noqa: E501
    evm_address_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TLM',  # noqa: E501
    evm_address_to_identifier('0xA91ac63D040dEB1b7A5E4d4134aD23eb0ba07e14', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BEL',  # noqa: E501
    evm_address_to_identifier('0xBA50933C268F567BDC86E1aC131BE072C6B0b71a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARPA',  # noqa: E501
    evm_address_to_identifier('0xA2120b9e674d3fC3875f415A7DF52e382F141225', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ATA',  # noqa: E501
    evm_address_to_identifier('0xBe1a001FE942f96Eea22bA08783140B9Dcc09D28', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BETA',  # noqa: E501
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CHR',  # noqa: E501
    evm_address_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CLV',  # noqa: E501
    evm_address_to_identifier('0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DEXE',  # noqa: E501
    evm_address_to_identifier('0x431ad2ff6a9C365805eBaD47Ee021148d6f7DBe0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DF',  # noqa: E501
    evm_address_to_identifier('0x0AbdAce70D3790235af448C88547603b945604ea', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DNT',  # noqa: E501
    evm_address_to_identifier('0x00AbA6fE5557De1a1d565658cBDdddf7C710a1eb', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EZ',  # noqa: E501
    evm_address_to_identifier('0x445f51299Ef3307dBD75036dd896565F5B4BF7A5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VIDT',  # noqa: E501
    evm_address_to_identifier('0xb6EE9668771a79be7967ee29a63D4184F8097143', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CXO',  # noqa: E501
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
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMP',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MNA',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TSD',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBT',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UST',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0x340D2bdE5Eb28c1eed91B2f790723E3B160613B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEE',  # noqa: E501
    evm_address_to_identifier('0xdB25f211AB05b1c97D595516F45794528a807ad8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EUS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x4674672BcDdDA2ea5300F5207E1158185c944bc0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GXT',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBT',  # noqa: E501
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
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x6531f133e6DeeBe7F2dcE5A0441aA7ef330B4e53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIME',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSD',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x77777FeDdddFfC19Ff86DB637967013e6C6A116C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TORN',  # noqa: E501
    evm_address_to_identifier('0x853d955aCEf822Db058eb8505911ED77F175b99e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRAX',  # noqa: E501
    evm_address_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GHST',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xf1Dc500FdE233A4055e25e5BbF516372BC4F6871', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SDL',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CHR',  # noqa: E501
    evm_address_to_identifier('0xBA50933C268F567BDC86E1aC131BE072C6B0b71a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARPA',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x445f51299Ef3307dBD75036dd896565F5B4BF7A5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VIDT',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMPL',  # noqa: E501
    evm_address_to_identifier('0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DIA',  # noqa: E501
    evm_address_to_identifier('0xaf9f549774ecEDbD0966C52f250aCc548D3F36E5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RFUEL',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x557B933a7C2c45672B610F8954A3deB39a51A8Ca', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REVV',  # noqa: E501
    evm_address_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRONT',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x961C8c0B1aaD0c0b10a51FeF6a867E3091BCef17', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DYP',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DODO',  # noqa: E501
    evm_address_to_identifier('0xFE2786D7D1cCAb8B015f6Ef7392F67d778f8d8D7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PRQ',  # noqa: E501
    evm_address_to_identifier('0x9534ad65fb398E27Ac8F4251dAe1780B989D136e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PYR',  # noqa: E501
    evm_address_to_identifier('0x7659CE147D0e714454073a5dd7003544234b6Aa0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCAD',  # noqa: E501
    evm_address_to_identifier('0xfc82bb4ba86045Af6F327323a46E80412b91b27d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PROM',  # noqa: E501
    evm_address_to_identifier('0xf8E9F10c22840b613cdA05A0c5Fdb59A4d6cd7eF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ELON',  # noqa: E501
    evm_address_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLS',  # noqa: E501
    evm_address_to_identifier('0xD9016A907Dc0ECfA3ca425ab20B6b785B42F2373', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GMEE',  # noqa: E501
    evm_address_to_identifier('0x626E8036dEB333b408Be468F951bdB42433cBF18', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AIOZ',  # noqa: E501
    evm_address_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CLV',  # noqa: E501
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0xA2120b9e674d3fC3875f415A7DF52e382F141225', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ATA',  # noqa: E501
    evm_address_to_identifier('0x2baEcDf43734F22FD5c152DB08E3C27233F0c7d2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OM',  # noqa: E501
    evm_address_to_identifier('0x6F87D756DAf0503d08Eb8993686c7Fc01Dc44fB1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRADE',  # noqa: E501
    evm_address_to_identifier('0x3E9BC21C9b189C09dF3eF1B824798658d5011937', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINA',  # noqa: E501
    evm_address_to_identifier('0x47b9F01B16E9C9cb99191DCA68c9cc5bF6403957', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ONSTON',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0xb056c38f6b7Dc4064367403E26424CD2c60655e1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEEK',  # noqa: E501
    evm_address_to_identifier('0xBe1a001FE942f96Eea22bA08783140B9Dcc09D28', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BETA',  # noqa: E501
    strethaddress_to_identifier('0xfB5c6815cA3AC72Ce9F5006869AE67f18bF77006'): 'PSTAKE',
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x4Fabb145d64652a948d72533023f6E7A623C7C53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BUSD',  # noqa: E501
    evm_address_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MC',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0xd794DD1CAda4cf79C9EebaAb8327a1B0507ef7d4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HYVE',  # noqa: E501
    evm_address_to_identifier('0x728f30fa2f100742C7949D1961804FA8E0B1387d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GHX',  # noqa: E501
    evm_address_to_identifier('0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DPI',  # noqa: E501
    evm_address_to_identifier('0x38A2fDc11f526Ddd5a607C1F251C065f40fBF2f7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PHNX',  # noqa: E501
    evm_address_to_identifier('0x9B02dD390a603Add5c07f9fd9175b7DABE8D63B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPI',  # noqa: E501
    evm_address_to_identifier('0xC005204856ee7035a13D8D7CdBbdc13027AFff90', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MSWAP',  # noqa: E501
    evm_address_to_identifier('0xE5CAeF4Af8780E59Df925470b050Fb23C43CA68C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRM',  # noqa: E501
    evm_address_to_identifier('0xd98F75b1A3261dab9eEd4956c93F33749027a964', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SHR',  # noqa: E501
    evm_address_to_identifier('0x0c963A1B52Eb97C5e457c7D76696F8b95c3087eD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TOKO',  # noqa: E501
    evm_address_to_identifier('0xa8c8CfB141A3bB59FEA1E2ea6B79b5ECBCD7b6ca', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NOIA',  # noqa: E501
    evm_address_to_identifier('0xa1d6Df714F91DeBF4e0802A542E13067f31b8262', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RFOX',  # noqa: E501
    evm_address_to_identifier('0x6226e00bCAc68b0Fe55583B90A1d727C14fAB77f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MTV',  # noqa: E501
    evm_address_to_identifier('0x8564653879a18C560E7C0Ea0E084c516C62F5653', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UBXT',  # noqa: E501
    evm_address_to_identifier('0x4c11249814f11b9346808179Cf06e71ac328c1b5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORAI',  # noqa: E501
    evm_address_to_identifier('0x2eDf094dB69d6Dcd487f1B3dB9febE2eeC0dd4c5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZEE',  # noqa: E501
    evm_address_to_identifier('0x0fF6ffcFDa92c53F615a4A75D982f399C989366b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LAYER',  # noqa: E501
    evm_address_to_identifier('0x3aFfCCa64c2A6f4e3B6Bd9c64CD2C969EFd1ECBe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DSLA',  # noqa: E501
    evm_address_to_identifier('0x2C9C19cE3b15ae77C6d80aEc3C1194Cfd6F7F3fA', ChainID.ETHEREUM, EvmTokenKind.ERC20): '2CRZ',  # noqa: E501
    evm_address_to_identifier('0x9695e0114e12C0d3A3636fAb5A18e6b737529023', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DFYN',  # noqa: E501
    evm_address_to_identifier('0x33f391F4c4fE802b70B77AE37670037A92114A7c', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BURP',  # noqa: E501
    evm_address_to_identifier('0x6149C26Cd2f7b5CCdb32029aF817123F6E37Df5B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LPOOL',  # noqa: E501
    evm_address_to_identifier('0xD9c2D319Cd7e6177336b0a9c93c21cb48d84Fb54', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HAPI',  # noqa: E501
    evm_address_to_identifier('0x21381e026Ad6d8266244f2A583b35F9E4413FA2a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FORM',  # noqa: E501
    evm_address_to_identifier('0xCd2828fc4D8E8a0eDe91bB38CF64B1a81De65Bf6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ODDZ',  # noqa: E501
    evm_address_to_identifier('0xD7EFB00d12C2c13131FD319336Fdf952525dA2af', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XPR',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0x993864E43Caa7F7F12953AD6fEb1d1Ca635B875F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SDAO',  # noqa: E501
    evm_address_to_identifier('0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DEXE',  # noqa: E501
    evm_address_to_identifier('0xF94b5C5651c888d928439aB6514B93944eEE6F48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YLD',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x467Bccd9d29f223BcE8043b84E8C8B282827790F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TEL',  # noqa: E501
    evm_address_to_identifier('0x79637D860380bd28dF5a07329749654790FAc1Df', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PLATO',  # noqa: E501
    evm_address_to_identifier('0xcFEB09C3c5F0f78aD72166D55f9e6E9A60e96eEC', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEMP',  # noqa: E501
    evm_address_to_identifier('0xD2dDa223b2617cB616c1580db421e4cFAe6a8a85', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BONDLY',  # noqa: E501
    evm_address_to_identifier('0xc6DdDB5bc6E61e0841C54f3e723Ae1f3A807260b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'URUS',  # noqa: E501
    evm_address_to_identifier('0xaA8330FB2B4D5D07ABFE7A72262752a8505C6B37', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLC',  # noqa: E501
    evm_address_to_identifier('0xCd1fAFf6e578Fa5cAC469d2418C95671bA1a62Fe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XTM',  # noqa: E501
    evm_address_to_identifier('0x29CbD0510EEc0327992CD6006e63F9Fa8E7f33B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIDAL',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
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
    strethaddress_to_identifier('0x362bc847A3a9637d3af6624EeC853618a43ed7D2'): 'PRQ',
    strethaddress_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a'): 'ORN',
    strethaddress_to_identifier('0xdeFA4e8a7bcBA345F687a2f1456F5Edd9CE97202'): 'KNC',
    strethaddress_to_identifier('0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68'): 'INV',
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RARE',  # noqa: E501
    evm_address_to_identifier('0xc770EEfAd204B5180dF6a14Ee197D99d808ee52d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FOX',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0x6531f133e6DeeBe7F2dcE5A0441aA7ef330B4e53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIME',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    evm_address_to_identifier('0xF5581dFeFD8Fb0e4aeC526bE659CFaB1f8c781dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HOPR',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x4Fabb145d64652a948d72533023f6E7A623C7C53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BUSD',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RAI',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x0954906da0Bf32d5479e25f46056d22f08464cab', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INDEX',  # noqa: E501
    evm_address_to_identifier('0x961C8c0B1aaD0c0b10a51FeF6a867E3091BCef17', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DYP',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CLV',  # noqa: E501
    evm_address_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUPER',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0x626E8036dEB333b408Be468F951bdB42433cBF18', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AIOZ',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0xBA50933C268F567BDC86E1aC131BE072C6B0b71a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARPA',  # noqa: E501
    evm_address_to_identifier('0x0AbdAce70D3790235af448C88547603b945604ea', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DNT',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0x71Ab77b7dbB4fa7e017BC15090b2163221420282', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HIGH',  # noqa: E501
    evm_address_to_identifier('0x0AbdAce70D3790235af448C88547603b945604ea', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DNT',  # noqa: E501
    evm_address_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLS',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
    evm_address_to_identifier('0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DIA',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0xD291E7a03283640FDc51b121aC401383A46cC623', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RGT',  # noqa: E501
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
    strethaddress_to_identifier('0x362bc847A3a9637d3af6624EeC853618a43ed7D2'): 'PRQ',
    strethaddress_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a'): 'ORN',
    strethaddress_to_identifier('0xdeFA4e8a7bcBA345F687a2f1456F5Edd9CE97202'): 'KNC',
    strethaddress_to_identifier('0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68'): 'INV',
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
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x0954906da0Bf32d5479e25f46056d22f08464cab', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INDEX',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIM',  # noqa: E501
    evm_address_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MC',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METI',  # noqa: E501
    evm_address_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IMX',  # noqa: E501

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
    'eip155:56/erc20:0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82': 'CAKE',
    'SOL-2': 'SOL',  # Solana
    'LUNA-2': 'LUNA',  # Luna Terra
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
}

WORLD_TO_CRYPTOCOM = {
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    'LUNA-2': 'LUNA',
}


@total_ordering
@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=True)
class Asset:
    """Base class for all assets"""
    identifier: str
    direct_field_initialization: InitVar[bool] = field(default=False)

    def __post_init__(self, direct_field_initializaion: bool) -> None:  # pylint: disable=unused-argument  # noqa: E501
        if not isinstance(self.identifier, str):
            raise DeserializationError(
                'Tried to initialize an asset out of a non-string identifier',
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
        }

    def serialize(self) -> str:
        return self.identifier

    def check_existence(self) -> 'Asset':
        """
        If this asset exists, returns the instance. If it doesn't, throws an error.
        May raise:
        - UnknownAsset
        """
        # We don't need asset type, but using `get_asset_type` since it has all the functionality
        # that we need here
        AssetResolver().get_asset_type(self.identifier)
        return self

    def is_nft(self) -> bool:
        return self.identifier.startswith(NFT_DIRECTIVE)

    def is_fiat(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) == AssetType.FIAT

    def is_asset_with_oracles(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) not in ASSETS_WITH_NO_CRYPTO_ORACLES

    def is_evm_token(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) == AssetType.EVM_TOKEN

    def resolve(self, form_with_incomplete_data: bool = False) -> 'Asset':
        """
        Returns the final representation for the current asset identifier. For example if we do
        dai = Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F').resolve()
        we will get in the variable dai the `EvmToken` representation of DAI. Same for other
        subclasses of Asset.

        May raise:
        - UnknownAsset
        """
        if self.identifier.startswith(NFT_DIRECTIVE):
            return Nft.initialize(
                identifier=self.identifier,
                chain=ChainID.ETHEREUM,
            )

        return AssetResolver().resolve_asset(
            identifier=self.identifier,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_asset_with_name_and_type(
            self,
            form_with_incomplete_data: bool = False,
    ) -> 'AssetWithNameAndType':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithNameAndType,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_asset_with_symbol(
            self,
            form_with_incomplete_data: bool = False,
    ) -> 'AssetWithSymbol':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithSymbol,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_crypto_asset(self, form_with_incomplete_data: bool = False) -> 'CryptoAsset':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=CryptoAsset,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_evm_token(self, form_with_incomplete_data: bool = False) -> 'EvmToken':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=EvmToken,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_asset_with_oracles(
            self,
            form_with_incomplete_data: bool = False,
    ) -> 'AssetWithOracles':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithOracles,
            form_with_incomplete_data=form_with_incomplete_data,
        )

    def resolve_to_fiat_asset(self) -> 'FiatAsset':
        # no `form_with_incomplete_data` here since EvmToken is not a subclass of FiatAsset
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=FiatAsset,
        )

    def symbol_or_name(self) -> str:
        """
        If it is an asset with symbol, returns symbol. If it's not, returns name.
        May raise:
        - UnknownAsset if identifier is not in the db
        """
        try:
            with_symbol = self.resolve_to_asset_with_symbol()
            return with_symbol.symbol
        except WrongAssetType:
            with_name = self.resolve_to_asset_with_name_and_type()
            return with_name.name

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier}>'

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if isinstance(other, Asset):
            return self.identifier.lower() == other.identifier.lower()
        if isinstance(other, str):
            return self.identifier.lower() == other.lower()
        # else
        raise NotImplementedError(f'Invalid comparison of asset with {type(other)}')

    def __lt__(self, other: Union['Asset', str]) -> bool:
        if isinstance(other, Asset):
            return self.identifier < other.identifier
        if isinstance(other, str):
            return self.identifier < other
        # else (but should never happen due to type checking)
        raise NotImplementedError(f'Invalid comparison of asset with {type(other)}')

    def __str__(self) -> str:
        return self.identifier


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class AssetWithNameAndType(Asset, metaclass=abc.ABCMeta):
    asset_type: AssetType = field(init=False)
    name: str = field(init=False)

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict() | {
            'name': self.name,
            'asset_type': str(self.asset_type),
        }

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name}>'

    def __str__(self) -> str:
        return f'{self.identifier}({self.name})'


class AssetWithSymbol(AssetWithNameAndType, metaclass=abc.ABCMeta):
    symbol: str = field(init=False)

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict() | {'symbol': self.symbol}

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name} symbol:{self.symbol}>'


class AssetWithOracles(AssetWithSymbol, metaclass=abc.ABCMeta):
    # None means no special mapping. '' means not supported
    cryptocompare: Optional[str] = field(init=False)
    coingecko: Optional[str] = field(init=False)

    def to_cryptocompare(self) -> str:
        """
        Returns the symbol with which to query cryptocompare for the asset
        May raise:
            - UnsupportedAsset if the asset is not supported by cryptocompare
        """
        cryptocompare_str = self.symbol if self.cryptocompare is None else self.cryptocompare
        # There is an asset which should not be queried in cryptocompare
        if cryptocompare_str is None or cryptocompare_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

        # Seems cryptocompare capitalizes everything. So cDAI -> CDAI
        return cryptocompare_str.upper()  # pylint: disable=no-member

    def to_coingecko(self) -> str:
        """
        Returns the symbol with which to query coingecko for the asset
        May raise:
            - UnsupportedAsset if the asset is not supported by coingecko
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

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.identifier, self.identifier)

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict() | {
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
        }


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class FiatAsset(AssetWithOracles):

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(self.identifier, FiatAsset)
        object.__setattr__(self, 'identifier', resolved.identifier)
        object.__setattr__(self, 'asset_type', resolved.asset_type)
        object.__setattr__(self, 'name', resolved.name)
        object.__setattr__(self, 'symbol', resolved.symbol)
        object.__setattr__(self, 'cryptocompare', resolved.cryptocompare)
        object.__setattr__(self, 'coingecko', resolved.coingecko)

    @classmethod
    def initialize(
            cls: Type['FiatAsset'],
            identifier: str,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
    ) -> 'FiatAsset':
        asset = FiatAsset(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', AssetType.FIAT)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        return asset


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class CryptoAsset(AssetWithOracles):
    started: Optional[Timestamp] = field(init=False)
    forked: Optional['CryptoAsset'] = field(init=False)
    swapped_for: Optional['CryptoAsset'] = field(init=False)

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=CryptoAsset,
            form_with_incomplete_data=getattr(self, 'form_with_incomplete_data', False),
        )
        object.__setattr__(self, 'identifier', resolved.identifier)
        object.__setattr__(self, 'asset_type', resolved.asset_type)
        object.__setattr__(self, 'name', resolved.name)
        object.__setattr__(self, 'symbol', resolved.symbol)
        object.__setattr__(self, 'cryptocompare', resolved.cryptocompare)
        object.__setattr__(self, 'coingecko', resolved.coingecko)
        object.__setattr__(self, 'started', resolved.started)
        object.__setattr__(self, 'forked', resolved.forked)
        object.__setattr__(self, 'swapped_for', resolved.swapped_for)

    @classmethod
    def initialize(
            cls: Type['CryptoAsset'],
            identifier: str,
            asset_type: AssetType,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
            started: Optional[Timestamp] = None,
            forked: Optional['CryptoAsset'] = None,
            swapped_for: Optional['CryptoAsset'] = None,
    ) -> 'CryptoAsset':
        asset = CryptoAsset(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', asset_type)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        object.__setattr__(asset, 'started', started)
        object.__setattr__(asset, 'forked', forked)
        object.__setattr__(asset, 'swapped_for', swapped_for)
        return asset

    def to_dict(self) -> Dict[str, Any]:
        forked, swapped_for = None, None
        if self.forked is not None:
            forked = self.forked.identifier
        if self.swapped_for is not None:
            swapped_for = self.swapped_for.identifier

        return super().to_dict() | {
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': str(self.asset_type),
            'started': self.started,
            'forked': forked,
            'swapped_for': swapped_for,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
        }


class CustomAsset(AssetWithNameAndType):
    notes: Optional[str] = field(init=False)
    custom_asset_type: str = field(init=False)

    @classmethod
    def initialize(
        cls: Type['CustomAsset'],
        identifier: str,
        name: str,
        custom_asset_type: str,
        notes: Optional[str] = None,
    ) -> 'CustomAsset':
        asset = CustomAsset(identifier=identifier)
        object.__setattr__(asset, 'asset_type', AssetType.CUSTOM_ASSET)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'custom_asset_type', custom_asset_type)
        object.__setattr__(asset, 'notes', notes)
        return asset

    @classmethod
    def deserialize_from_db(
            cls: Type['CustomAsset'],
            entry: Tuple[str, str, str, Optional[str]],
    ) -> 'CustomAsset':
        """
        Takes a `custom_asset` entry from DB and turns it into a `CustomAsset` instance.
        May raise:
        - DeserializationError if the identifier is not a string
        """
        return cls.initialize(
            identifier=entry[0],
            name=entry[1],
            custom_asset_type=entry[2],
            notes=entry[3],
        )

    def serialize_for_db(self) -> Tuple[str, str, Optional[str]]:
        return (
            self.identifier,
            self.custom_asset_type,
            self.notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'name': self.name,
            'custom_asset_type': self.custom_asset_type,
            'notes': self.notes,
        }


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


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class EvmToken(CryptoAsset):
    form_with_incomplete_data: bool = field(default=False)
    evm_address: ChecksumEvmAddress = field(init=False)
    chain: ChainID = field(init=False)
    token_kind: EvmTokenKind = field(init=False)
    decimals: int = field(init=False)
    protocol: str = field(init=False)
    underlying_tokens: List[UnderlyingToken] = field(init=False)

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=EvmToken,
            form_with_incomplete_data=self.form_with_incomplete_data,
        )
        object.__setattr__(self, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(self, 'evm_address', resolved.evm_address)
        object.__setattr__(self, 'chain', resolved.chain)
        object.__setattr__(self, 'token_kind', resolved.token_kind)
        object.__setattr__(self, 'decimals', resolved.decimals)
        object.__setattr__(self, 'protocol', resolved.protocol)
        object.__setattr__(self, 'underlying_tokens', resolved.underlying_tokens)

    @classmethod
    def initialize(  # type: ignore  # signature is incompatible with super type
            cls: Type['EvmToken'],
            address: ChecksumEvmAddress,
            chain: ChainID,
            token_kind: EvmTokenKind,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            started: Optional[Timestamp] = None,
            forked: Optional[CryptoAsset] = None,
            swapped_for: Optional[CryptoAsset] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
            decimals: Optional[int] = None,
            protocol: Optional[str] = None,
            underlying_tokens: Optional[List[UnderlyingToken]] = None,
    ) -> 'EvmToken':
        identifier = evm_address_to_identifier(
            address=address,
            chain=chain,
            token_type=token_kind,
        )
        asset = EvmToken(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        object.__setattr__(asset, 'started', started)
        object.__setattr__(asset, 'forked', forked)
        object.__setattr__(asset, 'swapped_for', swapped_for)
        object.__setattr__(asset, 'evm_address', address)
        object.__setattr__(asset, 'chain', chain)
        object.__setattr__(asset, 'token_kind', token_kind)
        object.__setattr__(asset, 'decimals', decimals)
        object.__setattr__(asset, 'protocol', protocol)
        object.__setattr__(asset, 'underlying_tokens', underlying_tokens)
        return asset

    @classmethod
    def deserialize_from_db(
            cls: Type['EvmToken'],
            entry: EthereumTokenDBTuple,
            underlying_tokens: Optional[List[UnderlyingToken]] = None,
    ) -> 'EvmToken':
        """May raise UnknownAsset if the swapped for asset can't be recognized
        That error would be bad because it would mean somehow an unknown id made it into the DB
        """
        swapped_for = CryptoAsset(entry[8]) if entry[8] is not None else None
        return EvmToken.initialize(
            address=entry[1],  # type: ignore
            chain=ChainID(entry[2]),
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

    def to_dict(self) -> Dict[str, Any]:
        underlying_tokens = [x.serialize() for x in self.underlying_tokens] if self.underlying_tokens is not None else None  # noqa: E501
        return super().to_dict() | {
            'address': self.evm_address,
            'chain': self.chain.serialize(),
            'token_kind': self.token_kind.serialize(),
            'decimals': self.decimals,
            'protocol': self.protocol,
            'underlying_tokens': underlying_tokens,
        }


class Nft(EvmToken):

    def __post_init__(self, direct_field_initialization: bool) -> None:
        if direct_field_initialization is True:
            return

        identifier_parts = self.identifier[len(NFT_DIRECTIVE):].split('_')
        if len(identifier_parts) == 0 or len(identifier_parts[0]) == 0:
            raise UnknownAsset(self.identifier)
        address = identifier_parts[0]
        object.__setattr__(self, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(self, 'name', f'nft with id {self.identifier}')
        object.__setattr__(self, 'symbol', self.identifier[len(NFT_DIRECTIVE):])
        object.__setattr__(self, 'cryptocompare', None)
        object.__setattr__(self, 'coingecko', None)
        object.__setattr__(self, 'started', None)
        object.__setattr__(self, 'forked', None)
        object.__setattr__(self, 'swapped_for', None)
        object.__setattr__(self, 'evm_address', address)
        object.__setattr__(self, 'chain', ChainID.ETHEREUM)
        object.__setattr__(self, 'token_kind', EvmTokenKind.ERC721)
        object.__setattr__(self, 'decimals', 0)
        object.__setattr__(self, 'protocol', None)
        object.__setattr__(self, 'underlying_tokens', None)

    @classmethod
    def initialize(  # type: ignore  # signature is incompatible with super type
            cls: Type['EvmToken'],
            identifier: str,
            chain: ChainID,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
    ) -> 'Nft':
        # TODO: This needs to change once we correctly track NFTs
        asset = Nft(identifier=identifier, direct_field_initialization=True)
        identifier_parts = identifier[len(NFT_DIRECTIVE):].split('_')
        if len(identifier_parts) == 0 or len(identifier_parts[0]) == 0:
            raise UnknownAsset(identifier)
        address = identifier_parts[0]

        nft_name = f'nft with id {identifier}' if name is None else name
        nft_symbol = identifier[len(NFT_DIRECTIVE):] if symbol is None else symbol
        object.__setattr__(asset, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(asset, 'name', nft_name)
        object.__setattr__(asset, 'symbol', nft_symbol)
        object.__setattr__(asset, 'cryptocompare', None)
        object.__setattr__(asset, 'coingecko', None)
        object.__setattr__(asset, 'started', None)
        object.__setattr__(asset, 'forked', None)
        object.__setattr__(asset, 'swapped_for', None)
        object.__setattr__(asset, 'evm_address', address)
        object.__setattr__(asset, 'chain', chain)
        object.__setattr__(asset, 'token_kind', EvmTokenKind.ERC721)
        object.__setattr__(asset, 'decimals', 0)
        object.__setattr__(asset, 'protocol', None)
        object.__setattr__(asset, 'underlying_tokens', None)
        return asset
