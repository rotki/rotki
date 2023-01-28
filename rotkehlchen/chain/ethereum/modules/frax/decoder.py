from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from web3 import Web3

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

from .constants import CPT_FRAX
from .fraxlend_pairs_cache import read_fraxlend_pairs

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


ADD_COLLATERAL = bytes(Web3.keccak(text='AddCollateral(address,address,uint256)'))


class FraxDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.fraxlend_pairs = read_fraxlend_pairs()
        self.ethereum = ethereum_inquirer

    def _decode_fraxlend_collateral_events(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
    ) -> None:
        """Decode information related to adding collateral to fraxlend pairs"""
        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_FRAX)
                continue

            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    tx_log.address in self.fraxlend_pairs
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_FRAX
                event.notes = (
                    f'Deposit {event.balance.amount} {crypto_asset.symbol} '
                    f'in Fraxlend pair {tx_log.address}'
                )

    def _decode_fraxlend_events(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        """Decode information related to fraxlend events"""
        if tx_log.topics[0] == ADD_COLLATERAL:
            self._decode_fraxlend_collateral_events(
                tx_log=tx_log,
                decoded_events=decoded_events,
            )
        return None, []

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            address: (self._decode_fraxlend_events,)
            for address in self.fraxlend_pairs
        }

    def counterparties(self) -> list[str]:
        return [CPT_FRAX]

    def reload_data(self) -> Optional[Mapping[ChecksumEvmAddress, tuple[Any, ...]]]:
        """Make sure fraxlend pairs are recently queried from the chain, saved in the DB
        and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        """
        self.ethereum.assure_fraxlend_pairs_cache_is_queried()
        new_fraxlend_pairs = read_fraxlend_pairs()
        fraxlend_pairs_diff = new_fraxlend_pairs - self.fraxlend_pairs
        if fraxlend_pairs_diff == set():
            return None

        new_mapping: Mapping[ChecksumEvmAddress, tuple[Callable]] = {
            address: (self._decode_fraxlend_events,)
            for address in fraxlend_pairs_diff
        }
        self.fraxlend_pairs = new_fraxlend_pairs
        return new_mapping
