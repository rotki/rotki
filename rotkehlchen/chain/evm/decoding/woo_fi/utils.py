from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.utils import get_vault_price
from rotkehlchen.chain.evm.decoding.woo_fi.constants import (
    CPT_WOO_FI_LABEL,
    WOO_STAKE_V1_OR_VAULT_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import Price


def query_woo_fi_token_price(
        token: 'EvmToken',
        inquirer: 'Inquirer',
        evm_inquirer: 'EvmNodeInquirer',
) -> 'Price':
    """Gets the token price for a WOOFi supercharger vault or xWOO token."""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=token,
        evm_inquirer=evm_inquirer,
        display_name=CPT_WOO_FI_LABEL,
        vault_abi=WOO_STAKE_V1_OR_VAULT_ABI,
        pps_method='getPricePerFullShare',
    )
