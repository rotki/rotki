from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.types import deserialize_evm_tx_hash

CURRENT_PRICE_MOCK = FVal('1.5')

A_RDN = Asset('eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6')
A_GNO = Asset('eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96')
A_DAO = Asset('eip155:1/erc20:0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413')
A_MKR = Asset('eip155:1/erc20:0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2')
A_SNGLS = Asset('eip155:1/erc20:0xaeC2E87E0A235266D9C5ADc9DEb4b2E29b54D009')
A_PAXG = Asset('eip155:1/erc20:0x45804880De22913dAFE09f4980848ECE6EcbAf78')
A_KCS = Asset('KCS')
A_MCO = Asset('eip155:1/erc20:0xB63B606Ac810a52cCa15e44bB630fd42D8d1d83d')
A_CRO = Asset('eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b')
A_SUSHI = Asset('eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2')
A_SDT2 = Asset('eip155:1/erc20:0x73968b9a57c6E53d41345FD57a6E6ae27d6CDB2F')
A_QTUM = Asset('QTUM')
A_OCEAN = Asset('eip155:1/erc20:0x967da4048cD07aB37855c090aAF366e4ce1b9F48')
A_BUSD = Asset('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53')
A_BAND = Asset('eip155:1/erc20:0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55')
A_AXS = Asset('eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b')
A_CHI = Asset('eip155:1/erc20:0x0000000000004946c0e9F43F4Dee607b0eF1fA1c')
A_PAN = Asset('eip155:1/erc20:0xD56daC73A4d6766464b38ec6D91eB45Ce7457c44')
A_LPT = Asset('eip155:1/erc20:0x58b6A8A3302369DAEc383334672404Ee733aB239')

A_SOL = Asset('SOL-2')
A_XRP = Asset('XRP')
A_ADA = Asset('ADA')
A_LUNA = Asset('LUNA-2')
A_LTC = Asset('LTC')
A_AIR2 = Asset('AIR-2')
A_SDC = Asset('SDC')
A_DOGE = Asset('DOGE')
A_NANO = Asset('NANO')
A_NEO = Asset('NEO')
A_SC = Asset('SC')
A_XMR = Asset('XMR')
A_DASH = Asset('DASH')
A_WAVES = Asset('WAVES')
A_EWT = Asset('EWT')
A_XTZ = Asset('XTZ')
A_BSV = Asset('BSV')
A_BCH = Asset('BCH')
A_CNY = Asset('CNY')
A_JPY = Asset('JPY')
A_ZEC = Asset('ZEC')
A_GBP = Asset('GBP')
A_CHF = Asset('CHF')
A_AUD = Asset('AUD')
A_CAD = Asset('CAD')
A_TRY = Asset('TRY')

A_OPTIMISM_USDT = Asset('eip155:10/erc20:0x94b008aA00579c1307B0EF2c499aD98a8ce58e58')
A_GNOSIS_EURE = Asset('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E')

ETH_ADDRESS1 = string_to_evm_address('0x5153493bB1E1642A63A098A65dD3913daBB6AE24')
ETH_ADDRESS2 = string_to_evm_address('0x4FED1fC4144c223aE3C1553be203cDFcbD38C581')
ETH_ADDRESS3 = string_to_evm_address('0x267FdC6F9F1C1a783b36126c1A59a9fbEBf42f84')

TX_HASH_STR1 = '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4'
TX_HASH_STR2 = '0x1c81f44c29ff0236f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e899'
TX_HASH_STR3 = '0x3c81144c29f60236f735cd0a8a2f2a7e3a6db52a713f8211b562fd15d3e0e192'

MOCK_INPUT_DATA = b'123'
MOCK_INPUT_DATA_HEX = '0x313233'

DEFAULT_TESTS_MAIN_CURRENCY = A_EUR

GRAPH_QUERY_CRED = 'd943ea1af415001154223fdf46b6f193'


TXHASH_HEX_TO_BYTES = {
    '0x13684203a4bf07aaed0112983cb380db6004acac772af2a5d46cb2a28245fbad': deserialize_evm_tx_hash('0x13684203a4bf07aaed0112983cb380db6004acac772af2a5d46cb2a28245fbad'),  # noqa: E501
    '0xe58af420fd8430c061303e4c5bd2668fafbc0fd41078fa6aa01d7781c1dadc7a': deserialize_evm_tx_hash('0xe58af420fd8430c061303e4c5bd2668fafbc0fd41078fa6aa01d7781c1dadc7a'),  # noqa: E501
    '0x0ae8b470b4a69c7f6905b9ec09f50c8772821080d11ba0acc83ac23a7ccb4ad8': deserialize_evm_tx_hash('0x0ae8b470b4a69c7f6905b9ec09f50c8772821080d11ba0acc83ac23a7ccb4ad8'),  # noqa: E501
    '0x2f6f167e32e9cb1bef40b92e831c3f1d1cd0348bb72dcc723bde94f51944ebd6': deserialize_evm_tx_hash('0x2f6f167e32e9cb1bef40b92e831c3f1d1cd0348bb72dcc723bde94f51944ebd6'),  # noqa: E501
    '0x5d81f937ad37349f89dc6e9926988855bb6c6e1e00c683ee3b7cb7d7b09b5567': deserialize_evm_tx_hash('0x5d81f937ad37349f89dc6e9926988855bb6c6e1e00c683ee3b7cb7d7b09b5567'),  # noqa: E501
    '0x2964f3a91408337b05aeb8f8f670f4107999be05376e630742404664c96a5c31': deserialize_evm_tx_hash('0x2964f3a91408337b05aeb8f8f670f4107999be05376e630742404664c96a5c31'),  # noqa: E501
    '0xb99a6e0b40f38c4887617bc1df560fde1d0456b712cb2bb1b52fdb8880d3cd74': deserialize_evm_tx_hash('0xb99a6e0b40f38c4887617bc1df560fde1d0456b712cb2bb1b52fdb8880d3cd74'),  # noqa: E501
    '0xfadf1f12281ee2c0311055848b4ffc0046ac80afae4a9d3640b5f57bb8a7795a': deserialize_evm_tx_hash('0xfadf1f12281ee2c0311055848b4ffc0046ac80afae4a9d3640b5f57bb8a7795a'),  # noqa: E501
    '0x3a9013edd5d7554699c9edcb316d4658dbf673e1940061b6f9c95f91a2c2d0a9': deserialize_evm_tx_hash('0x3a9013edd5d7554699c9edcb316d4658dbf673e1940061b6f9c95f91a2c2d0a9'),  # noqa: E501
    '0x7293791b92306c2081432438fbf666c917577e373ba178d4232dbebc18875a78': deserialize_evm_tx_hash('0x7293791b92306c2081432438fbf666c917577e373ba178d4232dbebc18875a78'),  # noqa: E501
    '0x7e254511474ee9cb2ea033ebb6743845c3d44d9f31165e7f69aa6bfd768192d0': deserialize_evm_tx_hash('0x7e254511474ee9cb2ea033ebb6743845c3d44d9f31165e7f69aa6bfd768192d0'),  # noqa: E501
    '0xe1ab3767684e9ae1859e78fc8dea00927b078be238b51426a5a01acbc3eabfa1': deserialize_evm_tx_hash('0xe1ab3767684e9ae1859e78fc8dea00927b078be238b51426a5a01acbc3eabfa1'),  # noqa: E501
    '0x7070ac300cfe44f2791bb53a272eddb6c04cf5b2a34c7b30f223034bf0fbc9f5': deserialize_evm_tx_hash('0x7070ac300cfe44f2791bb53a272eddb6c04cf5b2a34c7b30f223034bf0fbc9f5'),  # noqa: E501
    '0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2': deserialize_evm_tx_hash('0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2'),  # noqa: E501
    '0xefaf420db6bc00e007724c9f109cc2513886bf572cec52ce5c4fc4ea0c6691d6': deserialize_evm_tx_hash('0xefaf420db6bc00e007724c9f109cc2513886bf572cec52ce5c4fc4ea0c6691d6'),  # noqa: E501
    '0x983676d8ff7568f2502d73cdca96150be26dd033da86c4e05ea3a2c4ecb66182': deserialize_evm_tx_hash('0x983676d8ff7568f2502d73cdca96150be26dd033da86c4e05ea3a2c4ecb66182'),  # noqa: E501
    '0xb41eeed3fde0b6376bba43523d1f8e18127587ffa269b343b7155805bda27270': deserialize_evm_tx_hash('0xb41eeed3fde0b6376bba43523d1f8e18127587ffa269b343b7155805bda27270'),  # noqa: E501
    '0xe4a6a3759abeba7fe5d79bd77955b3ce6545f593efb445137b2eb29d3b685a55': deserialize_evm_tx_hash('0xe4a6a3759abeba7fe5d79bd77955b3ce6545f593efb445137b2eb29d3b685a55'),  # noqa: E501
    '0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f': deserialize_evm_tx_hash('0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f'),  # noqa: E501
    '0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017': deserialize_evm_tx_hash('0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017'),  # noqa: E501
    '0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824': deserialize_evm_tx_hash('0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824'),  # noqa: E501
    '0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa': deserialize_evm_tx_hash('0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa'),  # noqa: E501
    '0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4': deserialize_evm_tx_hash('0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4'),  # noqa: E501
    '0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa': deserialize_evm_tx_hash('0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa'),  # noqa: E501
    '0xc612f05bf9f3d814ffbe3649feacbf5bda213297bf7af53a56956814652fe9cc': deserialize_evm_tx_hash('0xc612f05bf9f3d814ffbe3649feacbf5bda213297bf7af53a56956814652fe9cc'),  # noqa: E501
    '0x597f8790a3b9353114b364777c9d32373930e5ad6b8c8f97a58cd2dd58f12b89': deserialize_evm_tx_hash('0x597f8790a3b9353114b364777c9d32373930e5ad6b8c8f97a58cd2dd58f12b89'),  # noqa: E501
    '0xbfb58e9f11484d1cdf0a6f13fe437c2db273663f8711586ca81f2c43cfafef52': deserialize_evm_tx_hash('0xbfb58e9f11484d1cdf0a6f13fe437c2db273663f8711586ca81f2c43cfafef52'),  # noqa: E501
    '0x6c94a0c25739863fd4cfc40cacf32b5a74d9d4a04b675e72c01dd71e4b3113d1': deserialize_evm_tx_hash('0x6c94a0c25739863fd4cfc40cacf32b5a74d9d4a04b675e72c01dd71e4b3113d1'),  # noqa: E501
    '0x0007999335475071899b18de7226d32b5ff83a182d37485faac0e8050e2fec14': deserialize_evm_tx_hash('0x0007999335475071899b18de7226d32b5ff83a182d37485faac0e8050e2fec14'),  # noqa: E501
}

TEST_PREMIUM_DEVICE_LIMIT: Final = 100
TEST_PREMIUM_DB_SIZE_LIMIT: Final = 1024
TEST_PREMIUM_PNL_EVENTS_LIMIT: Final = 50_000
TEST_PREMIUM_HISTORY_EVENTS_LIMIT: Final = 500_000
TEST_PREMIUM_PNL_REPORTS_LOOKUP_LIMIT: Final = 50_000
TEST_PREMIUM_ETH_STAKED_LIMIT: Final = 128
