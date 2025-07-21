from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.history.events.structures.types import HistoryEventType

CPT_GAS: Final = 'gas'
CPT_GITCOIN: Final = 'gitcoin'
CPT_BASE: Final = 'base'
CPT_ACCOUNT_DELEGATION: Final = 'account delegation'

# Common addresses across EVM chains
RABBY_WALLET_FEE_ADDRESS: Final = string_to_evm_address('0x39041F1B366fE33F9A5a79dE5120F2Aee2577ebc')  # noqa: E501

OUTGOING_EVENT_TYPES: Final = {
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
}

# keccak of Transfer(address,address,uint256)
ERC20_OR_ERC721_TRANSFER: Final = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_OR_ERC721_APPROVE: Final = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501
# keccak of DelegateChanged(address,address,address)
DELEGATE_CHANGED: Final = b'14\xe8\xa2\xe6\xd9~\x92\x9a~T\x01\x1e\xa5H]}\x19m\xd5\xf0\xbaMN\xf9X\x03\xe8\xe3\xfc%\x7f'  # noqa: E501
# keccak of Staked(address,uint256)
STAKED: Final = b'\x9eq\xbc\x8e\xea\x02\xa69i\xf5\t\x81\x8f-\xaf\xb9%E2\x90C\x19\xf9\xdb\xday\xb6{\xd3J_='  # noqa: E501
FUNDS_CLAIMED: Final = b'\xa4\xebP\x10;\x05\x91\xfe\xb0\xbc\x91?G\x9d\x92\xaf^\xb7\xea3\xe8\xc3\x97\xb4\x9b\xabR\xcej\xf2l\xb5'  # noqa: E501
WITHDRAWN: Final = b'p\x84\xf5Gf\x18\xd8\xe6\x0b\x11\xef\r}?\x06\x91FU\xad\xb8y>(\xff\x7f\x01\x8dLv\xd5\x05\xd5'  # noqa: E501
ERC4626_ABI: ABI = [{'inputs': [{'name': '', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'name': 'asset', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'name': 'pps', 'outputs': [{'name': 'pricePerShare', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


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
