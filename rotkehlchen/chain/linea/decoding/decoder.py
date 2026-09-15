import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
from rotkehlchen.chain.evm.l2_with_l1_fees.decoding.decoder import L2WithL1FeesTransactionDecoder
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.linea.node_inquirer import LineaInquirer
    from rotkehlchen.chain.linea.transactions import LineaTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LineaTransactionDecoder(L2WithL1FeesTransactionDecoder):

    def __init__(
            self,
            database: DBHandler,
            linea_inquirer: LineaInquirer,
            transactions: LineaTransactions,
            premium: Premium | None = None,
    ):
        super().__init__(
            database=database,
            node_inquirer=linea_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseEvmDecoderTools(
                database=database,
                evm_inquirer=linea_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
            premium=premium,
        )

    # -- methods that need to be implemented by child classes --

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
