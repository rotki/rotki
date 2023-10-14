from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_OKX = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0x3301Ee63Fb29F863f2333Bd4466acb46CD8323E6'): 'AKITA',  # noqa: E501
    strethaddress_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975'): 'ALPHA',  # noqa: E501
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',    # noqa: E501
    strethaddress_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d'): 'BADGER',  # noqa: E501
    'ETH2': 'BETH',
    strethaddress_to_identifier('0xb056c38f6b7Dc4064367403E26424CD2c60655e1'): 'CEEK',  # noqa: E501
    strethaddress_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d'): 'CEL',
    strethaddress_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667'): 'CELR',  # noqa: E501
    strethaddress_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52'): 'CLV',
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): 'COMP',  # noqa: E501
    strethaddress_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52'): 'CRV',
    strethaddress_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419'): 'CTC',
    strethaddress_to_identifier('0x1A3496C18d558bd9C6C8f609E1B129f67AB08163'): 'DEP',
    strethaddress_to_identifier('0xca1207647Ff814039530D7d35df0e1Dd2e91Fa84'): 'DHT',
    strethaddress_to_identifier('0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419'): 'DIA',
    strethaddress_to_identifier('0xb31eF9e52d94D4120eb44Fe1ddfDe5B4654A6515'): 'DOSE',  # noqa: E501
    strethaddress_to_identifier('0xf8E9F10c22840b613cdA05A0c5Fdb59A4d6cd7eF'): 'ELON',  # noqa: E501
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',  # noqa: E501
    strethaddress_to_identifier('0x43f11c02439e2736800433b4594994Bd43Cd066D'): 'FLOKI',  # noqa: E501
    strethaddress_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f'): 'FRONT',  # noqa: E501
    strethaddress_to_identifier('0xD0352a019e9AB9d757776F532377aAEbd36Fd541'): 'FSN',
    strethaddress_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550'): 'GHST',  # noqa: E501
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'): 'LDO',
    'LUNA-2': 'LUNA',
    strethaddress_to_identifier('0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A'): 'MAGIC',  # noqa: E501
    strethaddress_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'): 'MASK',  # noqa: E501
    strethaddress_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e'): 'METIS',  # noqa: E501
    strethaddress_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608'): 'MIR',
    strethaddress_to_identifier('0x3593D125a4f7849a1B059E64F4517A86Dd60c95d'): 'OM',
    'ONE-2': 'ONE',
    strethaddress_to_identifier('0xff56Cc6b1E6dEd347aA0B7676C85AB0B3D08B0FA'): 'ORBS',  # noqa: E501
    strethaddress_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447'): 'PERP',  # noqa: E501
    strethaddress_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa'): 'POLS',  # noqa: E501
    strethaddress_to_identifier('0x362bc847A3a9637d3af6624EeC853618a43ed7D2'): 'PRQ',
    strethaddress_to_identifier('0xfB5c6815cA3AC72Ce9F5006869AE67f18bF77006'): 'PSTAKE',  # noqa: E501
    strethaddress_to_identifier('0x557B933a7C2c45672B610F8954A3deB39a51A8Ca'): 'REVV',  # noqa: E501
    strethaddress_to_identifier('0xaf9f549774ecEDbD0966C52f250aCc548D3F36E5'): 'RFUEL',  # noqa: E501
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',    # noqa: E501
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6'): 'SPELL',  # noqa: E501
    strethaddress_to_identifier('0x6F87D756DAf0503d08Eb8993686c7Fc01Dc44fB1'): 'TRADE',  # noqa: E501
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',    # noqa: E501
    strethaddress_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376'): 'TUSD',  # noqa: E501
    strethaddress_to_identifier('0xF411903cbC70a74d22900a5DE66A2dda66507255'): 'VRA',   # noqa: E501
    'WIN-3': 'WIN',
    strethaddress_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'): 'WOO',
    strethaddress_to_identifier('0xD7EFB00d12C2c13131FD319336Fdf952525dA2af'): 'XPR',
    strethaddress_to_identifier('0xcbeAEc699431857FDB4d37aDDBBdc20E132D4903'): 'YOYO',  # noqa: E501
    strethaddress_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27'): 'ZIL',
    evm_address_to_identifier('0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PICKLE',  # noqa: E501
    evm_address_to_identifier('0x4C2e59D098DF7b6cBaE0848d66DE2f8A4889b9C3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FODL',  # noqa: E501
    evm_address_to_identifier('0xEB9A4B185816C354dB92DB09cC3B50bE60b901b6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORS',  # noqa: E501
    evm_address_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REP',  # noqa: E501
    evm_address_to_identifier('0x320623b8E4fF03373931769A31Fc52A4E78B5d70', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RSR',  # noqa: E501
    evm_address_to_identifier('0x2dff88a56767223a5529ea5960da7a3f5f766406', ChainID.BINANCE, EvmTokenKind.ERC20): 'ID',  # noqa: E501
    evm_address_to_identifier('0xBc7d6B50616989655AfD682fb42743507003056D', ChainID.BINANCE, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0x4922a015c4407F87432B179bb209e125432E4a2A', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XAUT',  # noqa: E501
    evm_address_to_identifier('0x3c8b650257cfb5f272f799f5e2b4e65093a11a05', ChainID.OPTIMISM, EvmTokenKind.ERC20): 'VELODROME',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x163f8C2467924be0ae7B5347228CABF260318753', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WLD',  # noqa: E501
    evm_address_to_identifier('0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TON',  # noqa: E501
}
