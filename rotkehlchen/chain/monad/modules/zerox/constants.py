from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

SETTLER_ROUTERS: Final = {
    string_to_evm_address('0xabC23F53f5bE23458d752aD18d10cA14506B2593'),  # Settler nonce 1
    string_to_evm_address('0x478cF28Fd1Ba92a6afd04F44b05833F6dF7f1486'),  # Settler nonce 2
    string_to_evm_address('0xFBC7D833F086A33CCA5a54D7271E17D010d29435'),  # Settler nonce 3
    string_to_evm_address('0xC2D3689cF6cE2859a3ffBc8fE09ab4C8623766b8'),  # Settler nonce 4
    string_to_evm_address('0x1727568c43303abCcE381B9A873B8913b5F966Ec'),  # Settler nonce 5
    string_to_evm_address('0x0f8701fD6B00F8d67836c39a0D10936043cDF267'),  # Settler nonce 6
    string_to_evm_address('0x4f83A6D66e89aE4B040cc7B9d89b1FB14e730314'),  # Settler nonce 7
}
