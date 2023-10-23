from rotkehlchen.chain.evm.types import string_to_evm_address

MAKERDAO_REQUERY_PERIOD = 7200  # Refresh queries every 2 hours

WAD_DIGITS = 18
WAD = 10**WAD_DIGITS

RAD_DIGITS = 45
RAD = 10**RAD_DIGITS

CPT_VAULT = 'makerdao vault'
CPT_DSR = 'makerdao dsr'
CPT_MAKERDAO_MIGRATION = 'makerdao migration'
CPT_SDAI = 'sDAI'

MAKERDAO_LABEL = 'Makerdao'
MAKERDAO_ICON = 'makerdao.svg'
SDAI_LABEL = 'sDAI contract'
SDAI_ICON = 'sdai.svg'

MAKERDAO_MIGRATION_ADDRESS = string_to_evm_address('0xc73e0383F3Aff3215E6f04B0331D58CeCf0Ab849')
