from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

SPOKE_POOL: Final = string_to_evm_address('0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5')
HUB_POOL: Final = string_to_evm_address('0xc186fA914353c44b2E33eBE05f21846F1048bEda')
LP_STAKING: Final = string_to_evm_address('0x9040e41eF5E8b281535a96D9a48aCb8cfaBD9a48')

# Canonical Ethereum pools returned by https://across.to/api/pools?token=<underlying address>.
ACROSS_LP_TOKEN_UNDERLYING: Final = {
    string_to_evm_address('0x28F77208728B0A45cAb24c4868334581Fe86F95B'): string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),  # WETH  # noqa: E501
    string_to_evm_address('0xC9b09405959f63F72725828b5d449488b02be1cA'): string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # USDC  # noqa: E501
    string_to_evm_address('0xC2faB88f215f62244d2E32c8a65E8F58DA8415a5'): string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # USDT  # noqa: E501
    string_to_evm_address('0x4FaBacAC8C41466117D6A38F46d08ddD4948A0cB'): string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),  # DAI  # noqa: E501
    string_to_evm_address('0x59C1427c658E97a7d568541DaC780b2E5c8affb4'): string_to_evm_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),  # WBTC  # noqa: E501
    string_to_evm_address('0xfacd2eC4647df2Cb758F684C2aAAB56A93288f9e'): string_to_evm_address('0xba100000625a3754423978a60c9317c58a424e3D'),  # BAL  # noqa: E501
    string_to_evm_address('0xB9921d28466304103a233fcD071833e498f12853'): string_to_evm_address('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'),  # UMA  # noqa: E501
    string_to_evm_address('0xb0C8fEf534223B891D4A430e49537143829c4817'): string_to_evm_address('0x44108f0223A3C3028F5Fe7AEC7f9bb2E66beF82F'),  # ACX  # noqa: E501
    string_to_evm_address('0xe480f5A42E263ac0352D0c9C6e75C4A612eE52A7'): string_to_evm_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),  # SNX  # noqa: E501
    string_to_evm_address('0xC3f35d90EbCE372ded12029b72B22a23A2F637fD'): string_to_evm_address('0x0cEC1A9154Ff802e7934Fc916Ed7Ca50bDE6844e'),  # noqa: E501
    string_to_evm_address('0xfd4a46D76Fb8fc13F5a77883519A0cfB656D3BEc'): string_to_evm_address('0x6033F7f88332B8db6ad452B7C6D5bB643990aE3f'),  # noqa: E501
    string_to_evm_address('0xA6ABcB5530770C32fd489eBD90D29Cde99d91d7F'): string_to_evm_address('0x1ff1dC3cB9eeDbC6Eb2d99C03b30A05cA625fB5a'),  # noqa: E501
    string_to_evm_address('0x8d29B8f64237cf39E93111a96A73e5dC03Eb612d'): string_to_evm_address('0x4e107a0000DB66f0E9Fd2039288Bf811dD1f9c74'),  # noqa: E501
}

ACROSS_HUB_POOL_ABI: Final[ABI] = [{
    'inputs': [{'name': 'l1Token', 'type': 'address'}],
    'name': 'exchangeRateCurrent',
    'outputs': [{'name': '', 'type': 'uint256'}],
    'stateMutability': 'nonpayable',
    'type': 'function',
}]
