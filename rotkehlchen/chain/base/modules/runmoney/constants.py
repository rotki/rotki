from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_RUNMONEY: Final = 'runmoney'
RUNMONEY_CONTRACT_ADDRESS: Final = string_to_evm_address('0x1089Db83561d4c9B68350E1c292279817AC6c8DA')  # noqa: E501
RUNMONEY_MEMBERSHIP_NFT_COLLECTION_IDENTIFIER: Final = f'eip155:8453/erc721:{RUNMONEY_CONTRACT_ADDRESS}'  # noqa: E501
CLAIM_TOPIC: Final = b'\xb9A\xdaN.\xc1\x05\xfe\xc1hI\xe53\xfb\xec.\x85\x1e\xdf\x82/&\x9d\xdb6\x0eCj\x8c5\x10\x91'  # noqa: E501
UNSTAKE_TOPIC: Final = b'\x0f[\xb8!v\xfe\xb1\xb5\xe7G\xe2\x84q\xaa\x92\x15j\x04\xd9\xf3\xab\x9fE\xf2\x8e-pB2\xb9?u'  # noqa: E501
JOINED_TOPIC: Final = b'ps\xaf\xa6\x0bH\xe83\xa1\xa6n\xbbD+\xc8\xe0\xd1\x9e\x9f<\xc0_4\xbd\xcd\x1d\xa2,\x8d\x87\xf2u'  # noqa: E501
