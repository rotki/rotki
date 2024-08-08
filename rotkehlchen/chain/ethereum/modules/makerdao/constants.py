from rotkehlchen.chain.evm.types import string_to_evm_address

MAKERDAO_REQUERY_PERIOD = 7200  # Refresh queries every 2 hours

WAD_DIGITS = 18
WAD = 10**WAD_DIGITS

RAD_DIGITS = 45
RAD = 10**RAD_DIGITS

CPT_VAULT = 'makerdao vault'
CPT_DSR = 'makerdao dsr'
CPT_MAKERDAO_MIGRATION = 'makerdao migration'

MAKERDAO_LABEL = 'Makerdao'
MAKERDAO_ICON = 'makerdao.svg'

MAKERDAO_MIGRATION_ADDRESS = string_to_evm_address('0xc73e0383F3Aff3215E6f04B0331D58CeCf0Ab849')

MAKERDAO_MCD_DAIJOIN_ADDRESS = string_to_evm_address('0x9759A6Ac90977b93B58547b4A71c78317f391A28')
MAKERDAO_GEM_JOIN_ETHA_ADDRESS = string_to_evm_address('0x2F0b23f53734252Bda2277357e97e1517d6B042A')  # noqa: E501
