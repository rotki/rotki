# -*- coding: utf-8
from binascii import hexlify

from rotkehlchen.utils import int_to_big_endian

GAS_LIMIT = 3141592  # Morden's gasLimit.
GAS_LIMIT_HEX = '0x' + hexlify(int_to_big_endian(GAS_LIMIT)).decode('utf-8')

GENESIS_STUB = {
    'config': {
        'homesteadBlock': 0,
        'eip150Block': 0,
        'eip150Hash': '0x0000000000000000000000000000000000000000000000000000000000000000',
        'eip155Block': 0,
        'eip158Block': 0,
        'ByzantiumBlock': 0,
    },
    'nonce': '0x0',
    'mixhash': '0x0000000000000000000000000000000000000000000000000000000000000000',
    'difficulty': '0x1',
    'coinbase': '0x0000000000000000000000000000000000000000',
    'timestamp': '0x00',
    'parentHash': '0x0000000000000000000000000000000000000000000000000000000000000000',
    'extraData': '0x' + hexlify(b'raiden').decode(),
    'gasLimit': GAS_LIMIT_HEX,
    # add precompiled addresses with minimal balance to avoid deletion
    'alloc': {'%040x' % precompiled: {'balance': '0x1'} for precompiled in range(256)},
}
