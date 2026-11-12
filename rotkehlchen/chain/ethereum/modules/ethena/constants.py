from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.types import ChecksumEvmAddress

CPT_ETHENA: Final = 'ethena'


class EthenaStakingVault(NamedTuple):
    """A staking vault of Ethena and the silo that holds its tokens during the cooldown."""
    token_id: str
    symbol: str
    underlying_token_id: str
    underlying_symbol: str
    silo: ChecksumEvmAddress


SUSDE_ADDRESS: Final = string_to_evm_address('0x9D39A5DE30e57443BfF2A8307A4256c8797A3497')
SENA_ADDRESS: Final = string_to_evm_address('0x8bE3460A480c80728a8C4D7a5D5303c85ba7B3b9')
USDE_SILO: Final = string_to_evm_address('0x7FC7c91D556B400AFa565013E3F32055a0713425')
ENA_SILO: Final = string_to_evm_address('0x4655B6A10C83D6bEfF1DC7116436cFD8b4F8d48A')
STAKING_VAULTS: Final = {
    SUSDE_ADDRESS: EthenaStakingVault(
        token_id='eip155:1/erc20:0x9D39A5DE30e57443BfF2A8307A4256c8797A3497',
        symbol='sUSDe',
        underlying_token_id='eip155:1/erc20:0x4c9EDD5852cd905f086C759E8383e09bff1E68B3',
        underlying_symbol='USDe',
        silo=USDE_SILO,
    ),
    SENA_ADDRESS: EthenaStakingVault(
        token_id='eip155:1/erc20:0x8bE3460A480c80728a8C4D7a5D5303c85ba7B3b9',
        symbol='sENA',
        underlying_token_id='eip155:1/erc20:0x57e114B691Db790C35207b2e685D4A43181e6061',
        underlying_symbol='ENA',
        silo=ENA_SILO,
    ),
}
SILO_TO_VAULT: Final = {vault.silo: vault for vault in STAKING_VAULTS.values()}

# cooldowns(address) of the staking vaults. cooldownShares/cooldownAssets burn the staked
# tokens, send the underlying tokens to the silo and add them to underlyingAmount, which can
# be claimed with unstake once cooldownEnd has passed.
ETHENA_STAKING_ABI: Final[ABI] = [{
    'inputs': [{'name': '', 'type': 'address'}],
    'name': 'cooldowns',
    'outputs': [
        {'name': 'cooldownEnd', 'type': 'uint104'},
        {'name': 'underlyingAmount', 'type': 'uint152'},
    ],
    'stateMutability': 'view',
    'type': 'function',
}]
