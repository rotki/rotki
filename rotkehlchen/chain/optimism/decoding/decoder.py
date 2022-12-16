import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument # noqa: E501
    return None


class OptimismTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            optimism_inquirer: 'OptimismInquirer',
            transactions: 'OptimismTransactions',
    ):
        super().__init__(
            database=database,
            evm_inquirer=optimism_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            address_is_exchange_fn=_address_is_exchange,
        )
