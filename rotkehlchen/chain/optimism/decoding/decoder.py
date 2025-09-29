import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderToolsWithProxy
from rotkehlchen.chain.evm.l2_with_l1_fees.decoding.decoder import L2WithL1FeesTransactionDecoder
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismTransactionDecoder(L2WithL1FeesTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            optimism_inquirer: 'OptimismInquirer',
            transactions: 'OptimismTransactions',
            premium: 'Premium | None' = None,
    ):
        super().__init__(
            database=database,
            node_inquirer=optimism_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseEvmDecoderToolsWithProxy(
                database=database,
                evm_inquirer=optimism_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
            premium=premium,
            dbevmtx_class=DBL2WithL1FeesTx,
        )

    # -- methods that need to be implemented by child classes --

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
