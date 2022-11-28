import logging
from typing import TYPE_CHECKING, Callable

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTransaction

from .constants import CPT_GITCOIN

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinDecoder(DecoderInterface):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        self.base = base_tools

    def _maybe_enrich_gitcoin_transfers(  # pylint: disable=no-self-use
            self,
            token: EvmToken,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,  # pylint: disable=unused-argument
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> bool:
        """
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if transaction.to_address not in (
                '0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
                '0x7d655c57f71464B6f83811C55D84009Cd9f5221C',
        ):
            return False
        crypto_asset = event.asset.resolve_to_crypto_asset()
        if event.event_type == HistoryEventType.SPEND:
            to_address = event.counterparty
            event.notes = f'Donate {event.balance.amount} {crypto_asset.symbol} to {to_address} via gitcoin'  # noqa: E501
        else:  # can only be RECEIVE
            from_address = event.counterparty
            event.notes = f'Receive donation of {event.balance.amount} {crypto_asset.symbol} from {from_address} via gitcoin'  # noqa: E501

        event.event_subtype = HistoryEventSubType.DONATE
        event.counterparty = CPT_GITCOIN
        return True

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_GITCOIN]
