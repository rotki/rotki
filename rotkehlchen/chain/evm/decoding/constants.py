from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.history.events.structures.types import HistoryEventType

CPT_GAS: Final = 'gas'
CPT_GITCOIN: Final = 'gitcoin'
CPT_BASE: Final = 'base'
CPT_SDAI: Final = 'sDAI'

OUTGOING_EVENT_TYPES: Final = {
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
}

# keccak of Transfer(address,address,uint256)
ERC20_OR_ERC721_TRANSFER: Final = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE: Final = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501
# keccak of DelegateChanged(address,address,address)
DELEGATE_CHANGED: Final = b'14\xe8\xa2\xe6\xd9~\x92\x9a~T\x01\x1e\xa5H]}\x19m\xd5\xf0\xbaMN\xf9X\x03\xe8\xe3\xfc%\x7f'  # noqa: E501
SDAI_DEPOSIT: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
SDAI_REDEEM: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
# keccak of Staked(address,uint256)
STAKED: Final = b'\x9eq\xbc\x8e\xea\x02\xa69i\xf5\t\x81\x8f-\xaf\xb9%E2\x90C\x19\xf9\xdb\xday\xb6{\xd3J_='  # noqa: E501

# Counterparty details shared between chains
OPTIMISM_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_OPTIMISM,
    label='Optimism',
    image='optimism.svg',
)
BASE_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_BASE,
    label='Base',
    image='base.svg',
)
GITCOIN_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GITCOIN,
    label='Gitcoin',
    image='gitcoin.svg',
)
SDAI_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_SDAI,
    label='sDAI contract',
    image='sdai.svg',
)
