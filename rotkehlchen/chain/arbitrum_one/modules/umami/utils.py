
import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import ERC4626_ABI
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_umami_vault_token_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets token price for Umami vault.
    Multiplies vault's price per share by the underlying token's USD price.
    """
    try:
        price_per_share = evm_inquirer.call_contract(
            contract_address=vault_token.evm_address,
            abi=ERC4626_ABI,
            method_name='pps',
        )
    except RemoteError as e:
        log.error(f'Failed to get price per share for umami vault {vault_token.evm_address}: {e}')
        return ZERO_PRICE

    formatted_pps = token_normalized_value_decimals(
        token_amount=price_per_share,
        token_decimals=vault_token.decimals,
    )
    underlying_price = inquirer.find_usd_price(Asset(vault_token.underlying_tokens[0].get_identifier(evm_inquirer.chain_id)))  # noqa: E501
    return Price(underlying_price * formatted_pps)
