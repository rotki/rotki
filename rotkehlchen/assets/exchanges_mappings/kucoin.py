from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind


WORLD_TO_KUCOIN = COMMON_ASSETS_MAPPINGS | {
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
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MASK',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x6531f133e6DeeBe7F2dcE5A0441aA7ef330B4e53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIME',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0x6c28AeF8977c9B773996d0e8376d2EE379446F2f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'QUICK',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSD',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
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
    evm_address_to_identifier('0x557B933a7C2c45672B610F8954A3deB39a51A8Ca', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REVV',  # noqa: E501
    evm_address_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRONT',  # noqa: E501
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
    evm_address_to_identifier('0x467Bccd9d29f223BcE8043b84E8C8B282827790F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TEL',  # noqa: E501
    evm_address_to_identifier('0x79637D860380bd28dF5a07329749654790FAc1Df', ChainID.MATIC, EvmTokenKind.ERC20): 'PLATO',  # noqa: E501
    evm_address_to_identifier('0xcFEB09C3c5F0f78aD72166D55f9e6E9A60e96eEC', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEMP',  # noqa: E501
    evm_address_to_identifier('0xD2dDa223b2617cB616c1580db421e4cFAe6a8a85', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BONDLY',  # noqa: E501
    evm_address_to_identifier('0xc6DdDB5bc6E61e0841C54f3e723Ae1f3A807260b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'URUS',  # noqa: E501
    evm_address_to_identifier('0xaA8330FB2B4D5D07ABFE7A72262752a8505C6B37', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLC',  # noqa: E501
    evm_address_to_identifier('0xCd1fAFf6e578Fa5cAC469d2418C95671bA1a62Fe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XTM',  # noqa: E501
    evm_address_to_identifier('0x29CbD0510EEc0327992CD6006e63F9Fa8E7f33B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TIDAL',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0xA31B1767e09f842ECFd4bc471Fe44F830E3891AA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ROOBEE',  # noqa: E501
    evm_address_to_identifier('0xD9Ec3ff1f8be459Bb9369b4E79e9Ebcf7141C093', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'KAI',  # noqa: E501
    evm_address_to_identifier('0xDb05EA0877A2622883941b939f0bb11d1ac7c400', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OPCT',  # noqa: E501
    evm_address_to_identifier('0x8c18D6a985Ef69744b9d57248a45c0861874f244', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTI',  # noqa: E501
    evm_address_to_identifier('0xe8780B48bdb05F928697A5e8155f672ED91462F7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CAS',  # noqa: E501
    evm_address_to_identifier('0x7cA4408137eb639570F8E647d9bD7B7E8717514A', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPA',  # noqa: E501
    evm_address_to_identifier('0x4a527d8fc13C5203AB24BA0944F4Cb14658D1Db6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MITX',  # noqa: E501
    evm_address_to_identifier('0xff56Cc6b1E6dEd347aA0B7676C85AB0B3D08B0FA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORBS',  # noqa: E501
    evm_address_to_identifier('0xE1c7E30C42C24582888C758984f6e382096786bd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCUR',  # noqa: E501
    evm_address_to_identifier('0x8b0E42F366bA502d787BB134478aDfAE966C8798', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LABS',  # noqa: E501
    evm_address_to_identifier('0x1Da87b114f35E1DC91F72bF57fc07A768Ad40Bb0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EQZ',  # noqa: E501
    evm_address_to_identifier('0x43A96962254855F16b925556f9e97BE436A43448', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HORD',  # noqa: E501
    evm_address_to_identifier('0x1fE24F25b1Cf609B9c4e7E12D802e3640dFA5e43', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CGG',  # noqa: E501
    evm_address_to_identifier('0x1C9922314ED1415c95b9FD453c3818fd41867d0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TOWER',  # noqa: E501
    evm_address_to_identifier('0x85f6eB2BD5a062f5F8560BE93FB7147e16c81472', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FLY',  # noqa: E501
    evm_address_to_identifier('0xeEAA40B28A2d1b0B08f6f97bB1DD4B75316c6107', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GOVI',  # noqa: E501
    evm_address_to_identifier('0xB4d930279552397bbA2ee473229f89Ec245bc365', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MAHA',  # noqa: E501
    evm_address_to_identifier('0x038a68FF68c393373eC894015816e33Ad41BD564', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GLCH',  # noqa: E501
    evm_address_to_identifier('0x48b19b7605429aCAa8Ea734117F39726a9AAb1f9', ChainID.BINANCE, EvmTokenKind.ERC20): 'ETHO',  # noqa: E501
    evm_address_to_identifier('0x5a666c7d92E5fA7Edcb6390E4efD6d0CDd69cF37', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MARSH',  # noqa: E501
    evm_address_to_identifier('0x16ECCfDbb4eE1A85A33f3A9B21175Cd7Ae753dB4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ROUTE',  # noqa: E501
    evm_address_to_identifier('0x6e9730EcFfBed43fD876A264C982e254ef05a0DE', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NORD',  # noqa: E501
    evm_address_to_identifier('0x4da0C48376C277cdBd7Fc6FdC6936DEE3e4AdF75', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EPIK',  # noqa: E501
    evm_address_to_identifier('0x298d492e8c1d909D3F63Bc4A36C66c64ACB3d695', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PBR',  # noqa: E501
    evm_address_to_identifier('0xA130E3a33a4d84b04c3918c4E5762223Ae252F80', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SWASH',  # noqa: E501
    evm_address_to_identifier('0x16CDA4028e9E872a38AcB903176719299beAed87', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MARS4',  # noqa: E501
    evm_address_to_identifier('0xE2FB6529EF566a080e6d23dE0bd351311087D567', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COV',  # noqa: E501
    evm_address_to_identifier('0xb6EE9668771a79be7967ee29a63D4184F8097143', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CXO',  # noqa: E501
    evm_address_to_identifier('0x9B99CcA871Be05119B2012fd4474731dd653FEBe', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATTER',  # noqa: E501
    evm_address_to_identifier('0xFE3E6a25e6b192A42a44ecDDCd13796471735ACf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REEF',  # noqa: E501
    evm_address_to_identifier('0x3DB6Ba6ab6F95efed1a6E794caD492fAAabF294D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LTO',  # noqa: E501
    evm_address_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUPER',  # noqa: E501
    evm_address_to_identifier('0xee573a945B01B788B9287CE062A0CFC15bE9fd86', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XED',  # noqa: E501
    evm_address_to_identifier('0xf3AE5d769e153Ef72b4e3591aC004E89F48107a1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DPR',  # noqa: E501
    evm_address_to_identifier('0x3496B523e5C00a4b4150D6721320CdDb234c3079', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NUM',  # noqa: E501
    evm_address_to_identifier('0x94E0BAb2F6Ab1F19F4750E42d7349f2740513aD5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNIC',  # noqa: E501
    evm_address_to_identifier('0x21BfBDa47A0B4B5b1248c767Ee49F7caA9B23697', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OVR',  # noqa: E501
    evm_address_to_identifier('0x24EC2Ca132abf8F6f8a6E24A1B97943e31f256a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MOOV',  # noqa: E501
    evm_address_to_identifier('0x474021845C4643113458ea4414bdb7fB74A01A77', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNO',  # noqa: E501
    evm_address_to_identifier('0x8B3870Df408fF4D7C3A26DF852D41034eDa11d81', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOI',  # noqa: E501
    evm_address_to_identifier('0x1796ae0b0fa4862485106a0de9b654eFE301D0b2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PMON',  # noqa: E501
    evm_address_to_identifier('0xD85AD783cc94bd04196a13DC042A3054a9B52210', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HAKA',  # noqa: E501
    evm_address_to_identifier('0xBd3de9a069648c84d27d74d701C9fa3253098B15', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EQX',  # noqa: E501
    evm_address_to_identifier('0x80D55c03180349Fff4a229102F62328220A96444', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'OPUL',  # noqa: E501
    evm_address_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TLM',  # noqa: E501
    evm_address_to_identifier('0x2653891204F463fb2a2F4f412564b19e955166aE', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'NGL',  # noqa: E501
    evm_address_to_identifier('0xd47bDF574B4F76210ed503e0EFe81B58Aa061F3d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRVL',  # noqa: E501
    evm_address_to_identifier('0x8dB253a1943DdDf1AF9bcF8706ac9A0Ce939d922', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNB',  # noqa: E501
    evm_address_to_identifier('0xb31eF9e52d94D4120eb44Fe1ddfDe5B4654A6515', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DOSE',  # noqa: E501
    evm_address_to_identifier('0x0C9c7712C83B3C70e7c5E11100D33D9401BdF9dd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WOMBAT',  # noqa: E501
    evm_address_to_identifier('0xabEDe05598760E399ed7EB24900b30C51788f00F', ChainID.MATIC, EvmTokenKind.ERC20): 'STEPWATCH',  # noqa: E501
    evm_address_to_identifier('0x6fC13EACE26590B80cCCAB1ba5d51890577D83B2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UMB',  # noqa: E501
    evm_address_to_identifier('0x4b520c812E8430659FC9f12f6d0c39026C83588D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DG',  # noqa: E501
    evm_address_to_identifier('0xD0352a019e9AB9d757776F532377aAEbd36Fd541', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FSN',  # noqa: E501
    evm_address_to_identifier('0x31ea0de8119307aA264Bb4b38727aAb4E36b074f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STORE',  # noqa: E501
    'MLS': 'PIKASTER2',
    evm_address_to_identifier('0x2a3bFF78B79A009976EeA096a51A948a3dC00e34', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WILD',  # noqa: E501
    evm_address_to_identifier('0x881Ba05de1E78f549cC63a8f6Cabb1d4AD32250D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'P00LS',  # noqa: E501
    evm_address_to_identifier('0x9fa69536d1cda4A04cFB50688294de75B505a9aE', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DERC',  # noqa: E501
}
