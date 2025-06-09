import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.gnosis.modules.monerium.constants import V1_TO_V2_MONERIUM_MAPPINGS
from rotkehlchen.chain.gnosis.tokens import GNOSIS_MONERIUM_LEGACY_ADDRESSES
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MONERIUM_V2_CONTRACTS_BLOCK: Final = 35656951


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
                exceptions_mappings=V1_TO_V2_MONERIUM_MAPPINGS,
            ),
            addresses_exceptions=dict.fromkeys(GNOSIS_MONERIUM_LEGACY_ADDRESSES, MONERIUM_V2_CONTRACTS_BLOCK),  # noqa: E501
        )

    # -- methods that need to be implemented by child classes --

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None
