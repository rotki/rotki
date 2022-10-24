from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind


WORLD_TO_BITFINEX = COMMON_ASSETS_MAPPINGS | {
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
    # Spankchain is SPK in bitfinex
    strethaddress_to_identifier('0x42d6622deCe394b54999Fbd73D108123806f6a18'): 'SPK',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EUT',
    strethaddress_to_identifier('0xC4f6E93AEDdc11dc22268488465bAbcAF09399aC'): 'HIX',
    'NFT': 'APENFT',
    'LUNA-3': 'LUNA2',
    strethaddress_to_identifier('0xF411903cbC70a74d22900a5DE66A2dda66507255'): 'VRA',
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UDC',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMP',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MNA',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TSD',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBT',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UST',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0x340D2bdE5Eb28c1eed91B2f790723E3B160613B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEE',  # noqa: E501
    evm_address_to_identifier('0xdB25f211AB05b1c97D595516F45794528a807ad8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EUS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x4674672BcDdDA2ea5300F5207E1158185c944bc0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GXT',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBT',  # noqa: E501
    evm_address_to_identifier('0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIM',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0xd7c302fc3ac829C7E896a32c4Bd126f3e8Bd0a1f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'B2M',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0xb9EF770B6A5e12E45983C5D80545258aA38F3B78', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZCN',  # noqa: E501
    evm_address_to_identifier('0xD9Ec3ff1f8be459Bb9369b4E79e9Ebcf7141C093', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'KAI',  # noqa: E501
    evm_address_to_identifier('0x99fE3B1391503A1bC1788051347A1324bff41452', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXX',  # noqa: E501
    evm_address_to_identifier('0xFE3E6a25e6b192A42a44ecDDCd13796471735ACf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REEF',  # noqa: E501
    evm_address_to_identifier('0xaA8330FB2B4D5D07ABFE7A72262752a8505C6B37', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLC',  # noqa: E501
    evm_address_to_identifier('0xd1ba9BAC957322D6e8c07a160a3A8dA11A0d2867', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HMT',  # noqa: E501
    evm_address_to_identifier('0x6F87D756DAf0503d08Eb8993686c7Fc01Dc44fB1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRADE',  # noqa: E501
    evm_address_to_identifier('0x2a3bFF78B79A009976EeA096a51A948a3dC00e34', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WILD',  # noqa: E501
}
