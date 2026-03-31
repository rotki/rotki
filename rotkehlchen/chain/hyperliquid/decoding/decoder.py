from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EvmDecodingRules, EVMTransactionDecoder
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.chain.hyperliquid.transactions import HyperliquidTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium


class HyperliquidTransactionDecoder(EVMTransactionDecoder):
    def __init__(
            self,
            database: 'DBHandler',
            hyperliquid_inquirer: 'HyperliquidInquirer',
            transactions: 'HyperliquidTransactions',
            premium: 'Premium | None' = None,
    ):
        super().__init__(
            database=database,
            evm_inquirer=hyperliquid_inquirer,
            transactions=transactions,
            value_asset=A_HYPE.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseEvmDecoderTools(
                database=database,
                evm_inquirer=hyperliquid_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
            premium=premium,
        )

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:  # pylint: disable=unused-argument
        return None

    def _add_builtin_decoders(self, rules: EvmDecodingRules) -> None:
        return None
