from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

# v0.6, v0.7 and v0.8 EntryPoint addresses. They are the same across all EVM chains.
ERC4337_ENTRYPOINTS: Final = (
    string_to_evm_address('0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789'),
    string_to_evm_address('0x0000000071727De22E5E9d8BAf0edAc6f37da032'),
    string_to_evm_address('0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108'),
)
# 0x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f
USER_OPERATION_EVENT: Final = b'Ib\x8f\xd1G\x10\x06\xc1H-\xa8\x80(\xe9\xceM\xbb\x08\x0b\x81\\\x9b\x03D\xd3\x9eZ\x8en\xc1A\x9f'  # noqa: E501
