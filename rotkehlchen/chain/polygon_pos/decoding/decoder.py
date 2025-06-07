import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.polygon_pos.modules.monerium.constants import V1_TO_V2_MONERIUM_MAPPINGS
from rotkehlchen.chain.polygon_pos.tokens import POLYGON_MONERIUM_LEGACY_ADDRESSES
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.chain.polygon_pos.transactions import PolygonPOSTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MONERIUM_V2_CONTRACTS_BLOCK: Final = 60733237


class PolygonPOSTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            transactions: 'PolygonPOSTransactions',
    ):
        super().__init__(
            database=database,
            evm_inquirer=polygon_pos_inquirer,
            transactions=transactions,
            value_asset=A_POLYGON_POS_MATIC.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseDecoderTools(
                database=database,
                evm_inquirer=polygon_pos_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
                exceptions_mappings=V1_TO_V2_MONERIUM_MAPPINGS,
            ),
            addresses_exceptions=dict.fromkeys(POLYGON_MONERIUM_LEGACY_ADDRESSES, MONERIUM_V2_CONTRACTS_BLOCK),  # noqa: E501
        )

    # -- methods that need to be implemented by child classes --

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
