from typing import NamedTuple

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.contracts import EvmContract


class YearnVault(NamedTuple):
    name: str
    contract: EvmContract
    token: EvmToken
