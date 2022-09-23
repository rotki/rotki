from typing import TYPE_CHECKING, Callable, List

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import PICKLE_JAR_PROTOCOL, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_PICKLE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


class PickleFinanceDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        jars = GlobalDBHandler().get_ethereum_tokens(protocol=PICKLE_JAR_PROTOCOL)
        self.pickle_contracts = {jar.evm_address for jar in jars}

    def _maybe_enrich_pickle_transfers(  # pylint: disable=no-self-use
            self,
            token: EvmToken,  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> bool:
        """Enrich tranfer transactions to address for jar deposits and withdrawals"""
        crypto_asset = event.asset.resolve_to_crypto_asset()
        if not (
            hex_or_bytes_to_address(tx_log.topics[2]) in self.pickle_contracts or
            hex_or_bytes_to_address(tx_log.topics[1]) in self.pickle_contracts or
            tx_log.address in self.pickle_contracts
        ):
            return False

        if (  # Deposit give asset
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) in self.pickle_contracts
        ):
            if EvmToken(ethaddress_to_identifier(tx_log.address)) != event.asset:
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=event.asset.resolve_to_crypto_asset(),
            )
            if event.balance.amount == amount:
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_PICKLE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in pickle contract'  # noqa: E501
        elif (  # Deposit receive wrapped
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            tx_log.address in self.pickle_contracts
        ):
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=event.asset.resolve_to_crypto_asset(),
            )
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_PICKLE
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} after depositing in pickle contract'  # noqa: E501
        elif (  # Withdraw send wrapped
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS and
            hex_or_bytes_to_address(tx_log.topics[1]) in transaction.from_address
        ):
            if event.asset != EvmToken(ethaddress_to_identifier(tx_log.address)):
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=event.asset.resolve_to_crypto_asset(),
            )
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_PICKLE
                event.notes = f'Return {event.balance.amount} {crypto_asset.symbol} to the pickle contract'  # noqa: E501
        elif (  # Withdraw receive asset
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[1]) in self.pickle_contracts
        ):
            if event.asset != EvmToken(ethaddress_to_identifier(tx_log.address)):
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=event.asset.resolve_to_crypto_asset(),
            )
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_PICKLE
                event.notes = f'Unstake {event.balance.amount} {crypto_asset.symbol} from the pickle contract'  # noqa: E501

        return True

    # -- DecoderInterface methods

    def enricher_rules(self) -> List[Callable]:
        return [
            self._maybe_enrich_pickle_transfers,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_PICKLE]
