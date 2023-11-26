import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.optimism_superchain.decoding.decoder import (
    OptimismSuperchainTransactionDecoder,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.base.transactions import BaseTransactions
    from rotkehlchen.chain.evm.decoding.structures import EnricherContext
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseTransactionDecoder(OptimismSuperchainTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            base_inquirer: 'BaseInquirer',
            transactions: 'BaseTransactions',
    ):
        super().__init__(
            database=database,
            node_inquirer=base_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseDecoderTools(
                database=database,
                evm_inquirer=base_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
            dbevmtx_class=DBOptimismTx,
        )

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
