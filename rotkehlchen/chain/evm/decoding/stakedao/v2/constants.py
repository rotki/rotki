from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_STAKEDAO_V2: Final = 'stakedao-v2'
VOTEMARKET_CLAIM_TOPIC: Final = b'\x31\x8e\x0a\x24\xa7\xfc\x05\xb1\x2e\x35\x89\x02\xd9\xd5\x84\x75\x43\x4a\x01\x76\x8f\x87\xa4\x31\x9f\xb3\x5d\xc5\xb5\x33\xe9\x86'  # noqa: E501
LAPOSTE_MESSAGE_SENT_TOPIC: Final = b'\xc3\xfe\x0c\xec\x81\xa9\xf3\x5c\xd4\xd9\x04\xd9\xbd\xc8\xa8\x07\xc1\xdf\xb9\xc7\x7c\x51\x1f\xa8\x76\x89\x9e\xb0\xb1\xa4\xc9\x29'  # noqa: E501
LAPOSTE_MESSAGE_RECEIVED_TOPIC: Final = b'\xe1\x20\x70\xab\x31\xc3\x54\xe3\x2f\x75\x59\x84\x62\x8c\xc3\xaf\x26\x01\x21\xee\x90\x15\xcf\x34\x63\x7b\x82\x4e\x34\xd0\x0b\xc7'  # noqa: E501

LAPOSTE_ADDRESS: Final = string_to_evm_address('0xF0000058000021003E4754dCA700C766DE7601C2')
LAPOSTE_BUNDLER_ADDRESS: Final = string_to_evm_address(
    '0x67346f8b9B7dDA4639600C190DDaEcDc654359c8',
)
LAPOSTE_TOKEN_FACTORY_ADDRESS: Final = string_to_evm_address('0x96006425Da428E45c282008b00004a00002B345e')  # noqa: E501
VOTEMARKET_PLATFORM_ADDRESSES: Final = frozenset({
    string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    string_to_evm_address('0xDD2FaD5606cD8ec0c3b93Eb4F9849572b598F4c7'),
    string_to_evm_address('0x155a7Cf21F8853c135BdeBa27FEA19674C65F2b4'),
    string_to_evm_address('0x105694FC5204787eD571842671d1262A54a8135B'),
})
