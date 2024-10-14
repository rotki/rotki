from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_PUFFER = 'puffer'
UNLOCKED_TOKENS_CLAIMED: Final = b'\xed\xa9\xc5\x84/\x9d\xe6:RNK\xaf\xca\xb7\x17\x96\x9b\x8c\xfd\xb8\xbb\xd1S>9Iu \xdb\xc1\x12u'  # noqa: E501

HEDGEY_DELEGATEDCLAIMS_CAMPAIGN: Final = string_to_evm_address('0x5Ae97e4770b7034C7Ca99Ab7edC26a18a23CB412')  # noqa: E501

PUFFERX_EIGEN_S2_AIRDROP = '9a43f419c0b0442ca93b48840b301630'
PUFFER_AIRDROP_S1_CAMPAIGN1 = '5614e2600ab1450f86b97d326f086872'
PUFFER_AIRDROP_S1_CAMPAIGN2 = 'd50f51a2fd4c4d5ba84ba43af6903afa'
PUFFER_AIRDROP_S1_CAMPAIGN3 = '334be319cbe94dc09381ac6768a2c5e6'

PUFFER_TOKEN_ID: Final = 'eip155:1/erc20:0x4d1C297d39C5c1277964D0E3f8Aa901493664530'
