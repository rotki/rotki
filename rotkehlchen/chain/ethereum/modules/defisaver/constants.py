from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_DEFISAVER: Final = 'defisaver'
SUB_STORAGE: Final = string_to_evm_address('0x1612fc28Ee0AB882eC99842Cde0Fc77ff0691e90')

SUBSCRIBE: Final = b'w\x91\xee\xa7\xfdZ\x87y@\xfd\x06T\xc6\xb1\xe0Y\x11)<\xed\xab\xdf\xe1\xf9\x9b|,\xb00\x8d\xba\xf7'  # noqa: E501
DEACTIVATE_SUB: Final = b'\x1f\x854\xa3*\xe8\x1aG\xc9\xe9\xfe%m\x92O:\xd6h\xe9\x19\x16\xa4\x8f\xd4\x1a\xc2\x7f\x84\xc6m\x94,'  # noqa: E501

DFS_GENERIC_LOGGER_LEGACY: Final = string_to_evm_address('0x5c55B921f590a89C1Ebe84dF170E655a82b62126')  # noqa: E501

# FLAction contract addresses taken from https://github.com/defisaver/defisaver-v3-contracts/blob/main/addresses/mainnet.json
FL_ACTION_V1_0_0: Final = string_to_evm_address('0x9eC9E483Edb2dACA782222fF32b261AD56e43879')
FL_ACTION_V1_0_1: Final = string_to_evm_address('0x72915D41982DfCAf30b871290618E59C45Edba7F')
FL_ACTION_V1_0_2: Final = string_to_evm_address('0x2bE65F12dCc55c8485030E306A1B01F47C437a8A')
FL_ACTION_V1_0_3: Final = string_to_evm_address('0xC2b92B6c69e5c3b6b29385C1a17FEe906e0CA910')
FL_ACTION_V1_0_3_BIS: Final = string_to_evm_address('0x5f1dC84Ba060Ea3f7429c6A7bBEdd9243CF1209b')
FL_MORPHO_BLUE: Final = string_to_evm_address('0x6206C96EAc5EAC546861438A9f953B6BEa50EBAB')
FL_BALANCER: Final = string_to_evm_address('0x93d333930c7f7260a1E6061B0a8C0CbdEC95F367')
FL_BALANCER_VPREV_1: Final = string_to_evm_address('0x540a83E36E5E6Aa916A6c591934d800e17115048')
FL_BALANCER_VPREV_2: Final = string_to_evm_address('0x5C7a9f4635AE4F95da2e45317311AAe255FB71B3')
FL_AAVEV3: Final = string_to_evm_address('0xd9D8e68717Ce24CCbf162868aaad7E38d81b05d1')
FL_EULER_V1_0_1: Final = string_to_evm_address('0x66DC6444CdC099153f89332e0d4C87af5C966A75')
FL_EULER_V1_0_0: Final = string_to_evm_address('0xaf591afeCbAa4026Be377AA3cF02dA366f18DE07')
FL_SPARK: Final = string_to_evm_address('0xe9Fe5a0f5e4B370Ae60d837da58744666D5C06F7')
FL_AAVEV3_WITH_FEE: Final = string_to_evm_address('0x5021d70aB7D757D61E0230c472ff89b8B2B8705e')
FL_AAVEV3_CARRY_DEBT: Final = string_to_evm_address('0x7BdD8ACE8a48B7032Df68B7f53E0D6D9Ea9411A7')
FL_AAVEV2: Final = string_to_evm_address('0xEA55576383C96A69B3E8beD51Ce0d0294001bc5F')
FL_DYDX: Final = string_to_evm_address('0x08AC78B418fCB0DDF1096533856A757C28d430d7')
FL_DYDX_VPREV_1: Final = string_to_evm_address('0x973065599BACa33FC9CAD2823710f1332D2B7805')
FL_DYDX_VPREV_2: Final = string_to_evm_address('0x505079b4E049B9e641deb7E04D55e9457B8ad8Bc')
FL_GHO: Final = string_to_evm_address('0xbb67b81dD080a406227A38965d0393f396ddECBc')
FL_MAKER_V1_0_3: Final = string_to_evm_address('0x0f8C3368cADF78167F5355D746Ed7b2A826A6e3b')
FL_MAKER_V1_0_2: Final = string_to_evm_address('0x672DE08e36A1698fD5e9E34045F81558dB4c1AFE')
FL_MAKER_V1_0_1: Final = string_to_evm_address('0x5DCf600C35ae2752A8a11eB7C489EF3D93126fB4')
FL_MAKER_V1_0_0: Final = string_to_evm_address('0xd393582bE148A45585aB202Fa7Cc789Fa5127223')
FL_UNIV3: Final = string_to_evm_address('0x9CAdAC8Be718572F82B672b950c53F0b58483A35')
