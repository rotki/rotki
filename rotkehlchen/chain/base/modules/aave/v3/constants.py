from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

POOL_ADDRESS: Final = string_to_evm_address('0xA238Dd80C259a72e81d7e4664a9801593F98d1c5')
ETH_GATEWAYS: Final = (string_to_evm_address('0x8be473dCfA93132658821E67CbEB684ec8Ea2E74'),)
AAVE_TREASURY: Final = string_to_evm_address('0xBA9424d650A4F5c80a0dA641254d1AcCE2A37057')
AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0x2d8A3C5677189723C4cB8873CfC9C8976FDF38Ac')
