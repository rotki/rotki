from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_POLONIEX = COMMON_ASSETS_MAPPINGS | {
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
    strethaddress_to_identifier('0xfB7B4564402E5500dB5bB6d63Ae671302777C75a'): 'DEXT',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0x9E46A38F5DaaBe8683E10793b06749EEF7D733d1'): 'NCT',
    strethaddress_to_identifier('0xa3EE21C306A700E682AbCdfe9BaA6A08F3820419'): 'CTC',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'WLUNA',
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
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
    evm_address_to_identifier('0xfFffFffF2ba8F66D4e51811C5190992176930278', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMBO',  # noqa: E501
}
