from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SOCKET: Final = 'socket'
GATEWAY_ADDRESS: Final = string_to_evm_address('0x3a23F943181408EAC424116Af7b7790c94Cb97a5')
BRIDGE_TOPIC: Final = b"tYM\xa9\xe3\x1e\xe4\x06\x8e\x17\x80\x907\xdb7\xdbIg\x02\xbf}\x8dc\xaf\xe6\xf9yI'}\x16\t"  # noqa: E501

# Direct Socket route payload selectors. The first four bytes of the transaction input are
# the route id, followed by the route implementation selector.
SWAP_AND_BRIDGE_SELECTOR: Final = b'\xc4\x8c;B'
PERFORM_ACTION_WITH_IN_SELECTOR: Final = b'\xee\x8f\x0b\x86'
