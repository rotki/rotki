from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

GOVERNOR_ADDRESSES: Final = (
    string_to_evm_address('0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9'),  # core governor
    string_to_evm_address('0x789fC99093B09aD01C34DC7251D0C89ce743e5a4'),  # treasury
    string_to_evm_address('0x8a1cDA8dee421cD06023470608605934c16A05a0'),  # nominee election
    string_to_evm_address('0x467923B9AE90BDB36BA88eCA11604D45F13b712C'),  # member election
    string_to_evm_address('0x6f3a242cA91A119F872f0073BC14BC8a74a315Ad'),  # member removal
)
