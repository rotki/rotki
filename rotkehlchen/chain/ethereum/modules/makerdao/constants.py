from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

MAKERDAO_REQUERY_PERIOD: Final = 7200  # Refresh queries every 2 hours

WAD_DIGITS: Final = 18
WAD: Final = 10**WAD_DIGITS

RAD_DIGITS: Final = 45
RAD: Final = 10**RAD_DIGITS

CPT_VAULT: Final = 'makerdao vault'
CPT_DSR: Final = 'makerdao dsr'
CPT_MAKERDAO_MIGRATION: Final = 'makerdao migration'

MAKERDAO_LABEL: Final = 'Makerdao'
MAKERDAO_ICON: Final = 'makerdao.svg'

MAKERDAO_MIGRATION_ADDRESS: Final = string_to_evm_address('0xc73e0383F3Aff3215E6f04B0331D58CeCf0Ab849')  # noqa: E501
MKR_ADDRESS: Final = string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2')
DAI_JOIN_ADDRESS: Final = string_to_evm_address('0x9759A6Ac90977b93B58547b4A71c78317f391A28')

GENERIC_EXIT: Final = b'\xefi;\xed\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
