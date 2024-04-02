from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


POOL_ADDRESS: Final = string_to_evm_address('0x11fCfe756c05AD438e312a7fd934381537D3cFfe')
ETH_GATEWAYS: Final = (string_to_evm_address('0xFF75A4B698E3Ec95E608ac0f22A03B8368E05F5D'),)
AAVE_TREASURY: Final = string_to_evm_address('0x90eB541e1a431D8a30ED85A77675D1F001128cb5')
AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0xa99F4E69acF23C6838DE90dD1B5c02EA928A53ee')
