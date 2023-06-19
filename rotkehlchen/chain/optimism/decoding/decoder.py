import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.decoding.base import BaseDecoderToolsWithDSProxy
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import from_wei

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
            base_tools=BaseDecoderToolsWithDSProxy(
                database=database,
                evm_inquirer=optimism_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
        )
        self.dbevmtx = DBOptimismTx(database)

    def _calculate_gas_burned(self, tx: OptimismTransaction) -> FVal:  # type: ignore[override]
        return from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee))

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument # noqa: E501
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument # noqa: E501
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument # noqa: E501
        return None
