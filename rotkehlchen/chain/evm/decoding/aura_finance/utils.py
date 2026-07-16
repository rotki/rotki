import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_aura_pool_price(inquirer: Inquirer, token: EvmToken) -> Price:
    """Get the USD price for an Aura pool token by using its underlying BPT token price."""
    if token.underlying_tokens is None:
        log.warning(
            f'No underlying token found for aura pool token {token} on {token.chain_id.to_name()}. '  # noqa: E501
            'This indicates pools data has not been queried yet.',
        )
        return ZERO_PRICE

    underlying_asset = Asset(evm_address_to_identifier(
        address=token.underlying_tokens[0].address,
        chain_id=token.chain_id,
        token_type=TokenKind.ERC20,
    ))
    return inquirer.find_usd_price(underlying_asset)
