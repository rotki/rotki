from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

BLOCKS_PER_YEAR = 2425846

CPT_YEARN_V1: Final = 'yearn-v1'
CPT_YEARN_V2: Final = 'yearn-v2'
CPT_YEARN_V3: Final = 'yearn-v3'

CPT_YGOV: Final = 'ygov'

YEARN_LABEL_V1: Final = 'Yearn V1'
YEARN_LABEL_V2: Final = 'Yearn V2'
YEARN_LABEL_V3: Final = 'Yearn V3'
YEARN_ICON: Final = 'yearn_vaults.svg'

ETHEREUM_YEARN_PARTNER_TRACKER: Final = string_to_evm_address('0x8ee392a4787397126C163Cb9844d7c447da419D8')  # noqa:E501
OPTIMISM_YEARN_PARTNER_TRACKER: Final = string_to_evm_address('0x7E08735690028cdF3D81e7165493F1C34065AbA2')  # noqa: E501
ARBITRUM_YEARN_PARTNER_TRACKER: Final = string_to_evm_address('0x0e5b46E4b2a05fd53F5a4cD974eb98a9a613bcb7')  # noqa: E501
BASE_YEARN_PARTNER_TRACKER: Final = string_to_evm_address('0xD0F08E42A40569fF83D28AA783a5b6537462667c')  # noqa: E501
