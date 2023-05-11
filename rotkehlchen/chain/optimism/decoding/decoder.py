import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import EnricherContext
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
        )

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument # noqa: E501
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument # noqa: E501
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument # noqa: E501
        return None
