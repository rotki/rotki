from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BITPANDA = COMMON_ASSETS_MAPPINGS | {
    'IOTA': 'MIOTA',
    strethaddress_to_identifier('0x536381a8628dBcC8C70aC9A30A7258442eAb4c92'): 'PAN',  # Pantos
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',  # ANT v2
    'SOL-2': 'SOL',  # Solana
    'LUNA-2': 'LUNA',  # Luna Terra
    'ONE-2': 'ONE',
    evm_address_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REP',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REQ',  # noqa: E501
    evm_address_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IMX',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x71Ab77b7dbB4fa7e017BC15090b2163221420282', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HIGH',  # noqa: E501
    evm_address_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUPER',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0xBA50933C268F567BDC86E1aC131BE072C6B0b71a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARPA',  # noqa: E501
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
    evm_address_to_identifier('0xff56Cc6b1E6dEd347aA0B7676C85AB0B3D08B0FA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORBS',  # noqa: E501
    evm_address_to_identifier('0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DODO',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0x3E9BC21C9b189C09dF3eF1B824798658d5011937', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINA',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FARM',  # noqa: E501
    evm_address_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FET',  # noqa: E501
    evm_address_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GTC',  # noqa: E501
    evm_address_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTT',  # noqa: E501
    evm_address_to_identifier('0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82', ChainID.BINANCE, EvmTokenKind.ERC20): 'CAKE',  # noqa: E501
}
