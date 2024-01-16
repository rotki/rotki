from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BYBIT = COMMON_ASSETS_MAPPINGS | {
    evm_address_to_identifier('0x4d224452801ACEd8B2F0aebE155379bb5D594381', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'APE',  # noqa: E501
    evm_address_to_identifier('0x6982508145454Ce325dDbE47a25d4ec3d2311933', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PEPE',  # noqa: E501
    evm_address_to_identifier('0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TON',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46', ChainID.BINANCE, EvmTokenKind.ERC20): 'VELO',  # noqa: E501
    evm_address_to_identifier('0x808507121B80c02388fAd14726482e061B8da827', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PENDLE',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0xf4d2888d29D722226FafA5d9B24F9164c092421E', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LOOKS',  # noqa: E501
    evm_address_to_identifier('0x477bC8d23c634C154061869478bce96BE6045D12', ChainID.BINANCE, EvmTokenKind.ERC20): 'SFUND',  # noqa: E501
    evm_address_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IMX',  # noqa: E501
    evm_address_to_identifier('0xcAfE001067cDEF266AfB7Eb5A286dCFD277f3dE5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PSP',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0x467719aD09025FcC6cF6F8311755809d45a5E5f3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AXL',  # noqa: E501
    evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOO',  # noqa: E501
    evm_address_to_identifier('0x14778860E937f509e651192a90589dE711Fb88a9', ChainID.BINANCE, EvmTokenKind.ERC20): 'CYBER',  # noqa: E501
    evm_address_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SLP',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xcf0C122c6b73ff809C693DB761e7BaeBe62b6a2E', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FLOKI',  # noqa: E501
    evm_address_to_identifier('0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MAGIC',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STETH',  # noqa: E501
    evm_address_to_identifier('0x3883f5e181fccaF8410FA61e12b59BAd963fb645', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'THETA',  # noqa: E501
    'WEMIX': 'WEMIX',
    'MYRIA': 'MYRIA',
    evm_address_to_identifier('0xFE67A4450907459c3e1FFf623aA927dD4e28c67a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NEXT',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x714f020C54cc9D104B6F4f6998C63ce2a31D1888', ChainID.AVALANCHE, EvmTokenKind.ERC20): 'FITFI',  # noqa: E501
    evm_address_to_identifier('0x2217e5921B7edfB4BB193a6228459974010D2198', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QMALL',  # noqa: E501
    evm_address_to_identifier('0xb2617246d0c6c0087f18703d576831899ca94f01', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIG',  # noqa: E501
    evm_address_to_identifier('0x52A8845DF664D76C69d2EEa607CD793565aF42B8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'APEX',  # noqa: E501
    evm_address_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTT',  # noqa: E501
    evm_address_to_identifier('0x12970E6868f88f6557B76120662c1B3E50A646bf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LADYS',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0x2C06BA9e7F0dACcbC1f6A33EA67e85bb68fbEE3a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LENDS',  # noqa: E501
    evm_address_to_identifier('0x2B72867c32CF673F7b02d208B26889fEd353B1f8', ChainID.BINANCE, EvmTokenKind.ERC20): 'SQR',  # noqa: E501
    evm_address_to_identifier('0x96F6eF951840721AdBF46Ac996b59E0235CB985C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDY',  # noqa: E501
    evm_address_to_identifier('0xb23d80f5FefcDDaa212212F028021B41DEd428CF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PRIME',  # noqa: E501
    evm_address_to_identifier('0x1cF4592ebfFd730c7dc92c1bdFFDfc3B9EfCf29a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WAVES',  # noqa: E501
    evm_address_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTC',  # noqa: E501
    evm_address_to_identifier('0x1afb69DBC9f54d08DAB1bD3436F8Da1af819E647', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MELOS',  # noqa: E501
    evm_address_to_identifier('0x60322971a672B81BccE5947706D22c19dAeCf6Fb', ChainID.BINANCE, EvmTokenKind.ERC20): 'MDAO',  # noqa: E501
    evm_address_to_identifier('0x6531f133e6DeeBe7F2dcE5A0441aA7ef330B4e53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIME',  # noqa: E501
    evm_address_to_identifier('0xFf76c0B48363A7C7307868a81548d340049b0023', ChainID.POLYGON_POS, EvmTokenKind.ERC20): 'DSRUN',  # noqa: E501
    evm_address_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FET',  # noqa: E501
    evm_address_to_identifier('0x626E8036dEB333b408Be468F951bdB42433cBF18', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AIOZ',  # noqa: E501
    evm_address_to_identifier('0x8c088775e4139af116Ac1FA6f281Bbf71E8c1c73', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PUMLX',  # noqa: E501
    evm_address_to_identifier('0x29a63F4B209C29B4DC47f06FFA896F32667DAD2C', ChainID.BINANCE, EvmTokenKind.ERC20): 'PURSE',  # noqa: E501
    evm_address_to_identifier('0x808507121B80c02388fAd14726482e061B8da827', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PENDLE',  # noqa: E501
    evm_address_to_identifier('0xE29142E14E52bdFBb8108076f66f49661F10EC10', ChainID.BINANCE, EvmTokenKind.ERC20): 'SEILOR',  # noqa: E501
    evm_address_to_identifier('0xAcf79C09Fff518EcBe2A96A2c4dA65B68fEDF6D3', ChainID.BINANCE, EvmTokenKind.ERC20): 'KARATE',  # noqa: E501
    evm_address_to_identifier('0xfB5c6815cA3AC72Ce9F5006869AE67f18bF77006', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PSTAKE',  # noqa: E501
    evm_address_to_identifier('0x477bC8d23c634C154061869478bce96BE6045D12', ChainID.BINANCE, EvmTokenKind.ERC20): 'SFUND',  # noqa: E501
    evm_address_to_identifier('0x2aD9adDD0d97EC3cDBA27F92bF6077893b76Ab0b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PLANET',  # noqa: E501
    evm_address_to_identifier('0x7A58c0Be72BE218B41C608b7Fe7C5bB630736C71', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PEOPLE',  # noqa: E501
    evm_address_to_identifier('0x0678Ca162E737C44cab2Ea31b4bbA78482E1313d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TURBOS',  # noqa: E501
    evm_address_to_identifier('0xd47bDF574B4F76210ed503e0EFe81B58Aa061F3d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRVL',  # noqa: E501
    evm_address_to_identifier('0x088cd8f5eF3652623c22D48b1605DCfE860Cd704', ChainID.ARBITRUM_ONE, EvmTokenKind.ERC20): 'VELA',  # noqa: E501
    'INTER': 'INTER',
    evm_address_to_identifier('0xc7283b66Eb1EB5FB86327f08e1B5816b0720212B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRIBE',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0x7420B4b9a0110cdC71fB720908340C03F9Bc03EC', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'JASMY',  # noqa: E501
    evm_address_to_identifier('0xEec2bE5c91ae7f8a338e1e5f3b5DE49d07AfdC81', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DPX',  # noqa: E501
    evm_address_to_identifier('0x94a7f270cd12545A277E656266Aef5e27dF3Eb28', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STRM',  # noqa: E501
    evm_address_to_identifier('0xDd13DEdeCEbDA566322195bc4451D672A148752C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PRIMAL',  # noqa: E501
    evm_address_to_identifier('0x6cf271270662be1C4fc1b7BB7D7D7Fc60Cc19125', ChainID.BINANCE, EvmTokenKind.ERC20): 'KUNCI',  # noqa: E501
    evm_address_to_identifier('0x24fcFC492C1393274B6bcd568ac9e225BEc93584', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MAVIA',  # noqa: E501
    evm_address_to_identifier('0x9663677B81c2D427E81C01ef7315eA96546F5Bb1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TENET',  # noqa: E501
    'SHILL': 'SHILL',
    evm_address_to_identifier('0x039cD22cb49084142d55FCD4B6096A4F51ffb3B4', ChainID.BINANCE, EvmTokenKind.ERC20): 'MOVEZ',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x628A3b2E302C7e896AcC432D2d0dD22B6cb9bc88', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LMWR',  # noqa: E501
    evm_address_to_identifier('0x31e4efe290973ebE91b3a875a7994f650942D28F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SHRAP',  # noqa: E501
    evm_address_to_identifier('0xB2492E97a68a6E4B9E9a11B99F6C42E5aCCD38c7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEXT',  # noqa: E501
    evm_address_to_identifier('0x549020a9Cb845220D66d3E9c6D9F9eF61C981102', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SIDUS',  # noqa: E501
    evm_address_to_identifier('0xf091867EC603A6628eD83D274E835539D82e9cc8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZETA',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0x29d578CEc46B50Fa5C88a99C6A4B70184C062953', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EVER',  # noqa: E501
    evm_address_to_identifier('0xC5d27F27F08D1FD1E3EbBAa50b3442e6c0D50439', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'APP',  # noqa: E501
}

FIVE_LETTER_ASSETS_BYBIT = {symbol for symbol in WORLD_TO_BYBIT.values() if len(symbol) == 5}
SIX_LETTER_ASSETS = {symbol for symbol in WORLD_TO_BYBIT.values() if len(symbol) == 6}
