import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price
from rotkehlchen.utils.misc import from_wei

from .constants import KILN_INTEGRATION_ABI

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_kiln_receipt_token_price(
        token: EvmToken,
        evm_inquirer: EvmNodeInquirer,
        price_func: Callable[[Asset], Price],
) -> Price:
    """Price a Kiln pooled staking receipt token as its ETH exchange rate times the ETH price.
    The receipt token is the integration contract itself and its rate() is the ETH value
    of one token scaled by 1e18. Returns ZERO_PRICE if the rate can't be queried."""
    try:
        rate = evm_inquirer.call_contract(
            contract_address=token.evm_address,
            abi=KILN_INTEGRATION_ABI,
            method_name='rate',
        )
    except (RemoteError, BlockchainQueryError) as e:
        log.error('Failed to query the rate of Kiln receipt token', token=token.identifier, error=str(e))  # noqa: E501
        return ZERO_PRICE

    return Price(from_wei(rate) * price_func(A_ETH))
