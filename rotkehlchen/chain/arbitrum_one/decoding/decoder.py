import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.arbitrum_one_tx import DBArbitrumOneTx
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .interfaces import ArbitrumDecoderInterface

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.arbitrum_one.transactions import ArbitrumOneTransactions
    from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
    from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
    from rotkehlchen.chain.evm.decoding.structures import EnricherContext
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ArbitrumOneTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            arbitrum_inquirer: 'ArbitrumOneInquirer',
            transactions: 'ArbitrumOneTransactions',
    ):
        self.transaction_type_mappings: dict[int, list[tuple[int, Callable]]] = defaultdict(list)
        super().__init__(
            database=database,
            evm_inquirer=arbitrum_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseDecoderTools(
                database=database,
                evm_inquirer=arbitrum_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
            dbevmtx_class=DBArbitrumOneTx,
        )

    def _chain_specific_post_decoding_rules(
            self,
            transaction: 'ArbitrumOneTransaction',  # type: ignore[override]
    ) -> list[tuple[int, Callable]]:
        return self.transaction_type_mappings.get(transaction.tx_type, [])

    def _chain_specific_decoder_initialization(
            self,
            decoder: 'DecoderInterface',
    ) -> None:
        """Initialize the transaction type mappings"""
        if not isinstance(decoder, ArbitrumDecoderInterface):
            return  # not all are arbitrum specific. Some common decoders exist for all chains

        txtype_mapping = decoder.decoding_by_tx_type()
        for txtype, rules in txtype_mapping.items():
            self.transaction_type_mappings[txtype].extend(rules)

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
