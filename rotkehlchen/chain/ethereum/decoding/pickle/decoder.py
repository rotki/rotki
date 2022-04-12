from typing import TYPE_CHECKING, Callable, Dict, List

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.pickle.constants import PICKLE_CONTRACTS
from rotkehlchen.chain.ethereum.decoding.structures import (
    ActionItem,
    TxEventSettings,
    TxMultitakeTreatment,
)
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.ethereum import ZERO_ADDRESS
from rotkehlchen.types import EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

CPT_PICKLE = 'pickle finance'


class PickleDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _maybe_enrich_pickle_transfers(  # pylint: disable=no-self-use
            self,
            token: EthereumToken,  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            event: HistoryBaseEntry,
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> bool:
        """Enrich tranfer transactions to address for jar deposits and withdrawals"""
        if not (
            hex_or_bytes_to_address(tx_log.topics[2]) in PICKLE_CONTRACTS or
            hex_or_bytes_to_address(tx_log.topics[1]) in PICKLE_CONTRACTS or
            tx_log.address in PICKLE_CONTRACTS
        ):
            return False

        if (  # Deposit give asset
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) in PICKLE_CONTRACTS
        ):
            if EthereumToken(tx_log.address) != event.asset:
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
            if event.balance.amount == amount:
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_PICKLE
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in pickle contract'  # noqa: E501
        elif (  # Deposit receive wrapped
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            tx_log.address in PICKLE_CONTRACTS
        ):
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_PICKLE
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol} after depositing in pickle contract'  # noqa: E501
        elif (  # Withdraw send wrapped
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS and
            hex_or_bytes_to_address(tx_log.topics[1]) in transaction.from_address
        ):
            if event.asset != EthereumToken(tx_log.address):
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_PICKLE
                event.notes = f'Return {event.balance.amount} {event.asset.symbol} to the pickle contract'  # noqa: E501
        elif (  # Withdraw receive asset
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            event.location_label == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[2]) == transaction.from_address and
            hex_or_bytes_to_address(tx_log.topics[1]) in PICKLE_CONTRACTS
        ):
            if event.asset != EthereumToken(tx_log.address):
                return True
            amount_raw = hex_or_bytes_to_int(tx_log.data)
            amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
            if event.balance.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_PICKLE
                event.notes = f'Unstake {event.balance.amount} {event.asset.symbol} from the pickle contract'  # noqa: E501

        return True

    # -- DecoderInterface methods

    def enricher_rules(self) -> List[Callable]:
        return [
            self._maybe_enrich_pickle_transfers,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_PICKLE]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_PICKLE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_PICKLE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
        }
