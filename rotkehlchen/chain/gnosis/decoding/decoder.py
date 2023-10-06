import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import EnricherContext
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GnosisTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            gnosis_inquirer: 'GnosisInquirer',
            transactions: 'GnosisTransactions',
    ):
        super().__init__(
            database=database,
            evm_inquirer=gnosis_inquirer,
            transactions=transactions,
            value_asset=A_XDAI.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseDecoderTools(
                database=database,
                evm_inquirer=gnosis_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
        )

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument
        return None
