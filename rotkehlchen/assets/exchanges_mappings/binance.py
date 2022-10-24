from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BINANCE = COMMON_ASSETS_MAPPINGS | {
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
    strethaddress_to_identifier('0x8f693ca8D21b157107184d29D398A8D082b38b76'): 'DATA',
    strethaddress_to_identifier('0x4824A7b64E3966B0133f4f4FFB1b9D6bEb75FFF7'): 'TCT',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
    'NFT': 'APENFT',
    'eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978': 'DAR',
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
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
    evm_address_to_identifier('0x3593D125a4f7849a1B059E64F4517A86Dd60c95d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OM',  # noqa: E501
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
    evm_address_to_identifier('0x0202Be363B8a4820f3F4DE7FaF5224fF05943AB1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UFT',  # noqa: E501
    evm_address_to_identifier('0xdd974D5C2e2928deA5F71b9825b8b646686BD200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'KNC',  # noqa: E501
    evm_address_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REP',  # noqa: E501
    evm_address_to_identifier('0x0391D2021f89DC339F60Fff84546EA23E337750f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BOND',  # noqa: E501
    evm_address_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MLN',  # noqa: E501
    evm_address_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FARM',  # noqa: E501
    evm_address_to_identifier('0x419D0d8BdD9aF5e606Ae2232ed285Aff190E711b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FUN',  # noqa: E501
    evm_address_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORN',  # noqa: E501
}
