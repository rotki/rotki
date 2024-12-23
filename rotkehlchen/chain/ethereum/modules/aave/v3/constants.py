from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

AAVE_V3_DATA_PROVIDER_OLD: Final = string_to_evm_address('0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3')  # noqa: E501
# Those can be found in https://search.onaave.com/?q=protocol%20data%20provider
AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0x41393e5e337606dc3821075Af65AeE84D7688CBD')
LIDO_AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0x08795CFE08C7a81dCDFf482BbAAF474B240f31cD')  # noqa: E501
ETHERFI_AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0xE7d490885A68f00d9886508DF281D67263ed5758')  # noqa: E501
