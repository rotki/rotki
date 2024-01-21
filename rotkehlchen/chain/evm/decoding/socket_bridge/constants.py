from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SOCKET: Final = 'socket'
GATEWAY_ADDRESS: Final = string_to_evm_address('0x3a23F943181408EAC424116Af7b7790c94Cb97a5')
BRIDGE_TOPIC: Final = b"tYM\xa9\xe3\x1e\xe4\x06\x8e\x17\x80\x907\xdb7\xdbIg\x02\xbf}\x8dc\xaf\xe6\xf9yI'}\x16\t"  # noqa: E501
