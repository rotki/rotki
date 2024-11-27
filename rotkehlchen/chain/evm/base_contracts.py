import json
from typing import Final

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address

BALANCE_SCANNER: Final = EvmContract(  # defined here only until we merge bugfixes to develop  # noqa: E501
    address=string_to_evm_address('0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92'),
    abi=json.loads('[{"inputs":[{"name":"addresses","type":"address[]"}],"name":"ether_balances","outputs":[{"name":"","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"tokens","type":"address[]"}],"name":"tokens_balance","outputs":[{"name":"","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"owners","type":"address[]"},{"name":"token","type":"address"}],"name":"token_balances","outputs":[{"name":"","type":"uint256[]"}],"stateMutability":"view","type":"function"}]'),
    deployed_block=0,
)
