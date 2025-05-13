from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal

VALIDATOR_STATS_QUERY_BACKOFF_EVERY_N_VALIDATORS: Final = 30
VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE: Final = 20
VALIDATOR_STATS_QUERY_BACKOFF_TIME: Final = 8

FREE_VALIDATORS_LIMIT: Final = 4
UNKNOWN_VALIDATOR_INDEX: Final = -1
MIN_EFFECTIVE_BALANCE: Final = FVal(32)
MAX_EFFECTIVE_BALANCE: Final = FVal(2048)

CPT_ETH2: Final = 'eth2'

BEACONCHAIN_MAX_EPOCH: Final = 9223372036854775807  # This is INT64 MAX. Beacon node API actually returns 18446744073709551615 which is UINT64 MAX # noqa: E501

DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE: Final = 100  # Maximum number of validators allowed per beaconcha.in API request  # noqa: E501

CONSOLIDATION_REQUEST_CONTRACT: Final = string_to_evm_address('0x0000BBdDc7CE488642fb579F8B00f3a590007251')  # noqa: E501
WITHDRAWAL_REQUEST_CONTRACT: Final = string_to_evm_address('0x00000961Ef480Eb55e80D19ad83579A64c007002')  # noqa: E501
