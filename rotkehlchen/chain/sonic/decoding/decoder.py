from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.constants.assets import A_S

if TYPE_CHECKING:
    from rotkehlchen.chain.sonic.node_inquirer import SonicInquirer
    from rotkehlchen.chain.sonic.transactions import SonicTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.types import ChecksumEvmAddress


class SonicTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: DBHandler,
            sonic_inquirer: SonicInquirer,
            transactions: SonicTransactions,
            premium: Premium | None = None,
    ):
        super().__init__(
            database=database,
            evm_inquirer=sonic_inquirer,
            transactions=transactions,
            value_asset=A_S.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseEvmDecoderTools(
                database=database,
                evm_inquirer=sonic_inquirer,
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
