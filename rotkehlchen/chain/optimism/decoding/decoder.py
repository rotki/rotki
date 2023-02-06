import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.base import HistoryBaseEntry
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.structures import ActionItem
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
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
        )

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(
            self,
            token: 'EvmToken',
            tx_log: 'EvmTxReceiptLog',
            transaction: EvmTransaction,
            event: 'HistoryBaseEntry',
            action_items: list['ActionItem'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> None:
        return None

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument # noqa: E501
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument # noqa: E501
        return None
