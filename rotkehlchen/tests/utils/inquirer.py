from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import ChainID


def inquirer_inject_ethereum_set_order(
        inquirer,
        add_defi_oracles,
        current_price_oracles_order,
        ethereum_manager,
) -> None:
    inquirer.inject_evm_managers([(ChainID.ETHEREUM, ethereum_manager)])
    if add_defi_oracles is True:
        uniswap_v2_oracle = UniswapV2Oracle(ethereum_manager.node_inquirer)
        uniswap_v3_oracle = UniswapV3Oracle(ethereum_manager.node_inquirer)
        Inquirer().add_defi_oracles(
            uniswap_v2=uniswap_v2_oracle,
            uniswap_v3=uniswap_v3_oracle,
        )
    else:  # make sure only not on-chain oracles are in there
        current_price_oracles_order = current_price_oracles_order[:-3]

    inquirer.set_oracles_order(current_price_oracles_order)
