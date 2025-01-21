from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer


def get_spark_token_price(
        token: 'EvmToken',
        inquirer: 'Inquirer',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    assert token.underlying_tokens is not None and len(token.underlying_tokens) == 1, 'Spark token must have exactly one underlying token.'  # noqa: E501
    return inquirer.find_usd_price(
        asset=Asset(evm_address_to_identifier(
            address=token.underlying_tokens[0].address,
            chain_id=evm_inquirer.chain_id,
        )),
    )
