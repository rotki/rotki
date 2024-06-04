from typing import Final
from rotkehlchen.chain.evm.types import string_to_evm_address


GOVERNOR_ADDRESSES: Final = (
    string_to_evm_address('0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9'),
    string_to_evm_address('0x467923B9AE90BDB36BA88eCA11604D45F13b712C'),
)
