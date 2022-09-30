from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_COINBASE_PRO = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'WLUNA',
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
    strethaddress_to_identifier('0xFE2786D7D1cCAb8B015f6Ef7392F67d778f8d8D7'): 'PRQ',
    strethaddress_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a'): 'ORN',
    strethaddress_to_identifier('0xdd974D5C2e2928deA5F71b9825b8b646686BD200'): 'KNC',
    strethaddress_to_identifier('0xEcE83617Db208Ad255Ad4f45Daf81E25137535bb'): 'INV',
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
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
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0xD291E7a03283640FDc51b121aC401383A46cC623', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RGT',  # noqa: E501
    evm_address_to_identifier('0xA2120b9e674d3fC3875f415A7DF52e382F141225', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ATA',  # noqa: E501
    evm_address_to_identifier('0x04abEdA201850aC0124161F037Efd70c74ddC74C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NEST',  # noqa: E501
    evm_address_to_identifier('0x0f2D719407FdBeFF09D87557AbB7232601FD9F29', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SYN',  # noqa: E501
}
