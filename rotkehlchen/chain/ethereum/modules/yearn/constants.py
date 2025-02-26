from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_YEARN_V1: Final = 'yearn-v1'
CPT_YEARN_V2: Final = 'yearn-v2'
CPT_YEARN_V3: Final = 'yearn-v3'
CPT_YGOV: Final = 'ygov'

YEARN_LABEL_V1: Final = 'Yearn V1'
YEARN_LABEL_V2: Final = 'Yearn V2'
YEARN_LABEL_V3: Final = 'Yearn V3'
YEARN_ICON: Final = 'yearn_vaults.svg'

YEARN_PARTNER_TRACKER: Final = string_to_evm_address('0x8ee392a4787397126C163Cb9844d7c447da419D8')
