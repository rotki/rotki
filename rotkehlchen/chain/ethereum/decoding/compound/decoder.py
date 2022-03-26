from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import symbol_to_ethereum_token
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import (
    ActionItem,
    TxEventSettings,
    TxMultitakeTreatment,
)
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.assets import A_COMP
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


MINT_COMPOUND_TOKEN = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
REDEEM_COMPOUND_TOKEN = b'\xe5\xb7T\xfb\x1a\xbb\x7f\x01\xb4\x99y\x1d\x0b\x82\n\xe3\xb6\xaf4$\xac\x1cYv\x8e\xdbS\xf4\xec1\xa9)'  # noqa: E501

CPT_COMPOUND = 'compound'


class CompoundDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        self.base = base_tools

    def _decode_mint(
            self,
            tx_log: EthereumTxReceiptLog,
            decoded_events: List[HistoryBaseEntry],
            compound_token: EthereumToken,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        minter = hex_or_bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(minter):
            return None, None

        mint_amount_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        minted_amount_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        underlying_token = symbol_to_ethereum_token(compound_token.symbol[1:])
        mint_amount = token_normalized_value(mint_amount_raw, underlying_token)
        minted_amount = token_normalized_value(minted_amount_raw, compound_token)
        for event in decoded_events:
            # Find the transfer event which should have come before the minting
            if event.event_type == HistoryEventType.SPEND and event.asset == underlying_token and event.balance.amount == mint_amount:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_COMPOUND
                event.notes = f'Deposit {mint_amount} {underlying_token.symbol} to compound'
                break

        # also create an action item for the receive of the cTokens
        action_item = ActionItem(
            action='transform',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=compound_token,
            amount=minted_amount,
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            to_notes=f'Receive {minted_amount} {compound_token.symbol} from compound',
            to_counterparty=CPT_COMPOUND,
        )
        return None, action_item

    def _decode_redeem(
            self,
            tx_log: EthereumTxReceiptLog,
            decoded_events: List[HistoryBaseEntry],
            compound_token: EthereumToken,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        redeemer = hex_or_bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(redeemer):
            return None, None

        redeem_amount_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        redeem_tokens_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        underlying_token = symbol_to_ethereum_token(compound_token.symbol[1:])
        redeem_amount = token_normalized_value(redeem_amount_raw, underlying_token)
        redeem_tokens = token_normalized_value(redeem_tokens_raw, compound_token)
        out_event = in_event = None
        for event in decoded_events:
            # Find the transfer event which should have come before the redeeming
            if event.event_type == HistoryEventType.RECEIVE and event.asset == underlying_token and event.balance.amount == redeem_amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_COMPOUND
                event.notes = f'Withdraw {redeem_amount} {underlying_token.symbol} from compound'
                in_event = event
            elif event.event_type == HistoryEventType.SPEND and event.asset == compound_token and event.balance.amount == redeem_tokens:  # noqa: E501
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_COMPOUND
                event.notes = f'Return {redeem_tokens} {compound_token.symbol} to compound'
                out_event = event

        maybe_reshuffle_events(out_event=out_event, in_event=in_event)
        return None, None

    def decode_compound_token_movement(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
            compound_token: EthereumToken,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == MINT_COMPOUND_TOKEN:
            return self._decode_mint(tx_log=tx_log, decoded_events=decoded_events, compound_token=compound_token)  # noqa: E501

        if tx_log.topics[0] == REDEEM_COMPOUND_TOKEN:
            return self._decode_redeem(tx_log=tx_log, decoded_events=decoded_events, compound_token=compound_token)  # noqa: E501

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        compound_tokens = GlobalDBHandler().get_ethereum_tokens(protocol='compound')
        mapping: Dict[ChecksumEthAddress, Tuple[Any, ...]] = {}
        for token in compound_tokens:
            if token == A_COMP:
                continue

            mapping[token.ethereum_address] = (self.decode_compound_token_movement, token)
        return mapping

    def counterparties(self) -> List[str]:
        return [CPT_COMPOUND]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_COMPOUND): TxEventSettings(  # noqa: E501
                count_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_COMPOUND): TxEventSettings(  # noqa: E501
                count_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
        }
