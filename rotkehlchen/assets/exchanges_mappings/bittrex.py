from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind


WORLD_TO_BITTREX = COMMON_ASSETS_MAPPINGS | {
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
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0xe0cCa86B254005889aC3a81e737f56a14f4A38F5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALTA',  # noqa: E501
    evm_address_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ANKR',  # noqa: E501
    evm_address_to_identifier('0xeDF6568618A00C6F0908Bf7758A16F76B6E04aF9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARIA20',  # noqa: E501
    evm_address_to_identifier('0xdacD69347dE42baBfAEcD09dC88958378780FB62', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ATRI',  # noqa: E501
    evm_address_to_identifier('0xB90cb79B72EB10c39CbDF86e50B1C89F6a235f2e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AUDT',  # noqa: E501
    evm_address_to_identifier('0xd7c302fc3ac829C7E896a32c4Bd126f3e8Bd0a1f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'B2M',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0xCa3F508B8e4Dd382eE878A314789373D80A5190A', ChainID.BINANCE, EvmTokenKind.ERC20): 'BIFI',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0x33D0568941C0C64ff7e0FB4fbA0B11BD37deEd9f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RAMP',  # noqa: E501
    evm_address_to_identifier('0x459086F2376525BdCebA5bDDA135e4E9d3FeF5bf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RENBTC',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x0AbdAce70D3790235af448C88547603b945604ea', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DNT',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GNO',  # noqa: E501
    evm_address_to_identifier('0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IOTX',  # noqa: E501
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
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0x340D2bdE5Eb28c1eed91B2f790723E3B160613B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEE',  # noqa: E501
    evm_address_to_identifier('0x1b793E49237758dBD8b752AFC9Eb4b329d5Da016', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VITE',  # noqa: E501
    evm_address_to_identifier('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VSP',  # noqa: E501
    evm_address_to_identifier('0x7659CE147D0e714454073a5dd7003544234b6Aa0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCAD',  # noqa: E501
    evm_address_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ZIL',  # noqa: E501
    evm_address_to_identifier('0xD2dDa223b2617cB616c1580db421e4cFAe6a8a85', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BONDLY',  # noqa: E501
    evm_address_to_identifier('0x32E6C34Cd57087aBBD59B5A4AECC4cB495924356', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BTBS',  # noqa: E501
    evm_address_to_identifier('0xb683D83a532e2Cb7DFa5275eED3698436371cc9f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BTU',  # noqa: E501
    evm_address_to_identifier('0x41e5560054824eA6B0732E656E3Ad64E20e94E45', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CIV',  # noqa: E501
    evm_address_to_identifier('0x5B685863494C33F344081F75e5430C260c224A32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CMCX',  # noqa: E501
    evm_address_to_identifier('0x5CAc718A3AE330d361e39244BF9e67AB17514CE8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COT',  # noqa: E501
    evm_address_to_identifier('0x1A3496C18d558bd9C6C8f609E1B129f67AB08163', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DEP',  # noqa: E501
    evm_address_to_identifier('0x82030CDBD9e4B7c5bb0b811A61DA6360D69449cc', ChainID.BINANCE, EvmTokenKind.ERC20): 'FEVR',  # noqa: E501
    evm_address_to_identifier('0x0e2ef8AeCB3c01Ad5D596f1B67134e178199984D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LAND',  # noqa: E501
    evm_address_to_identifier('0xF94b5C5651c888d928439aB6514B93944eEE6F48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YLD',  # noqa: E501
    evm_address_to_identifier('0xcC1a8BD438BebC4b2a885a34475BB974f2124317', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WEC',  # noqa: E501
    evm_address_to_identifier('0x755be920943eA95e39eE2DC437b268917B580D6e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VVT',  # noqa: E501
    evm_address_to_identifier('0xcFEB09C3c5F0f78aD72166D55f9e6E9A60e96eEC', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'VEMP',  # noqa: E501
    evm_address_to_identifier('0x1735Db6AB5BAa19eA55d0AdcEeD7bcDc008B3136', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'URQA',  # noqa: E501
    evm_address_to_identifier('0xDDD6A0ECc3c6F6C102E5eA3d8Af7B801d1a77aC8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNIX',  # noqa: E501
    evm_address_to_identifier('0x8400D94A5cb0fa0D041a3788e395285d61c9ee5e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UBT',  # noqa: E501
    evm_address_to_identifier('0x394A16744Dcd805BB0cA7252e70691f0dcAc56AA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRZ',  # noqa: E501
    evm_address_to_identifier('0x2C537E5624e4af88A7ae4060C022609376C8D0EB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRYB',  # noqa: E501
    evm_address_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TLM',  # noqa: E501
    'SOL-2': 'SOL',
    evm_address_to_identifier('0xd98F75b1A3261dab9eEd4956c93F33749027a964', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SHR',  # noqa: E501
    evm_address_to_identifier('0x2A039B1D9bBDccBb91be28691b730ca893e5e743', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNB',  # noqa: E501
    evm_address_to_identifier('0xa1d6Df714F91DeBF4e0802A542E13067f31b8262', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RFOX',  # noqa: E501
    evm_address_to_identifier('0x6D0F5149c502faf215C89ab306ec3E50b15e2892', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PRT',  # noqa: E501
    evm_address_to_identifier('0x054D64b73d3D8A21Af3D764eFd76bCaA774f3Bb2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PPAY',  # noqa: E501
    evm_address_to_identifier('0xaA8330FB2B4D5D07ABFE7A72262752a8505C6B37', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLC',  # noqa: E501
    evm_address_to_identifier('0x846C66cf71C43f80403B51fE3906B3599D63336f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PMA',  # noqa: E501
    evm_address_to_identifier('0x001A8Ffcb0f03e99141652eBCdecDb0384E3bd6c', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PKR',  # noqa: E501
    evm_address_to_identifier('0xff56Cc6b1E6dEd347aA0B7676C85AB0B3D08B0FA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORBS',  # noqa: E501
    evm_address_to_identifier('0xa645264C5603E96c3b0B078cdab68733794B0A71', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MYST',  # noqa: E501
    evm_address_to_identifier('0x16CDA4028e9E872a38AcB903176719299beAed87', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MARS4',  # noqa: E501
    evm_address_to_identifier('0x2162f572B25f7358db9376AB58a947a4e45CeDE1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LBL',  # noqa: E501
    evm_address_to_identifier('0x0e2ef8AeCB3c01Ad5D596f1B67134e178199984D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LAND',  # noqa: E501
    evm_address_to_identifier('0xD9Ec3ff1f8be459Bb9369b4E79e9Ebcf7141C093', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'KAI',  # noqa: E501
    evm_address_to_identifier('0x73374Ea518De7adDD4c2B624C0e8B113955ee041', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'JGN',  # noqa: E501
    evm_address_to_identifier('0xd794DD1CAda4cf79C9EebaAb8327a1B0507ef7d4', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HYVE',  # noqa: E501
    evm_address_to_identifier('0xEBBdf302c940c6bfd49C6b165f457fdb324649bc', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HYDRO',  # noqa: E501
    evm_address_to_identifier('0x4297394c20800E8a38A619A243E9BbE7681Ff24E', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HOTCROSS',  # noqa: E501
    evm_address_to_identifier('0x970B9bB2C0444F5E81e9d0eFb84C8ccdcdcAf84d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FUSE',  # noqa: E501

    evm_address_to_identifier('0x6e8908cfa881C9f6f2C64d3436E7b80b1bf0093F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BIST',  # noqa: E501
    evm_address_to_identifier('0xF74941046389c78F12fE44784C0EC9ca7CEb7dc2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DMR',  # noqa: E501
    evm_address_to_identifier('0xa150Db9b1Fa65b44799d4dD949D922c0a33Ee606', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DRC',  # noqa: E501
    evm_address_to_identifier('0xBd3de9a069648c84d27d74d701C9fa3253098B15', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'EQX',  # noqa: E501
    evm_address_to_identifier('0x1FCdcE58959f536621d76f5b7FfB955baa5A672F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FOR',  # noqa: E501
    evm_address_to_identifier('0x9B02dD390a603Add5c07f9fd9175b7DABE8D63B7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPI',  # noqa: E501
    evm_address_to_identifier('0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INV',  # noqa: E501
    evm_address_to_identifier('0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIM',  # noqa: E501
    'META': 'METADIUM',
    'NLG': 'MUNT',
}
