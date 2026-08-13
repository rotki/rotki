import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import WITHDRAW_TOPIC
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import (
    CPT_FLYING_TULIP,
    FLYING_TULIP_LABEL,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.decoder import FlyingTulipCommonDecoder
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    FLYING_TULIP_LEND_DEPLOYMENTS,
    PM_BORROW_TOPIC,
    PM_DEPOSIT_FOR_TOPIC,
    PM_DEPOSIT_TOPIC,
    PM_REPAY_FOR_TOPIC,
    PM_REPAY_TOPIC,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

LEND_LABEL: Final = f'{FLYING_TULIP_LABEL} Lend'


class FlyingTulipLendCommonDecoder(FlyingTulipCommonDecoder):
    """Decode deposits, withdrawals, borrows and repayments of Flying Tulip's
    lending market (the ftDNMM positions manager).

    Decoding happens in a post-decoding rule because relayed (session)
    transactions move the wallet transfer after the positions manager event and
    deduct the relayer fee from it in-flight, so both sides need to be visible
    to reconcile them. Each positions manager event is matched against an
    actual wallet transfer, and any difference between the two is decoded as a
    relayer fee. Events without a wallet transfer (the ones the leverage RFQ
    engines emit while rebalancing funds inside a position) are skipped,
    mirroring how the protocol itself attributes them.
    """

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.deployment = FLYING_TULIP_LEND_DEPLOYMENTS[evm_inquirer.chain_id]

    def _reconcile_spend(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            consumed: set[int],
            token: EvmToken,
            amount: FVal,
            location_label: ChecksumEvmAddress | None,
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> None:
        """Turn the wallet transfer funding a positions manager event into it.

        Relayed transactions send the relayer fee together with the funds in a
        single transfer, so a transfer larger than the event's amount is split
        into the protocol movement plus a fee event.
        """
        candidate = None
        for event in decoded_events:
            if (
                    id(event) not in consumed and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    (location_label is None or event.location_label == location_label)
            ):
                if event.amount == amount:
                    candidate = event
                    break
                if event.amount > amount and candidate is None:
                    candidate = event

        if candidate is None:
            return  # a movement inside the protocol that never touched the wallet

        consumed.add(id(candidate))
        if (fee_amount := candidate.amount - amount) > ZERO:
            candidate.amount = amount
            decoded_events.append(self.base.make_event_next_index(
                tx_ref=transaction.tx_hash,
                timestamp=transaction.timestamp,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=token,
                amount=fee_amount,
                location_label=candidate.location_label,
                notes=f'Spend {fee_amount} {token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',
                counterparty=CPT_FLYING_TULIP,
                address=self.deployment.positions_manager,
            ))
        candidate.event_type = to_event_type
        candidate.event_subtype = to_event_subtype
        candidate.notes = notes
        candidate.counterparty = CPT_FLYING_TULIP
        candidate.address = self.deployment.positions_manager

    def _reconcile_receive(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            consumed: set[int],
            token: EvmToken,
            amount: FVal,
            location_label: ChecksumEvmAddress,
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> None:
        """Turn the wallet transfer paying out a positions manager event into it.

        Relayed transactions deduct the relayer fee from the payout before it
        reaches the wallet, so a transfer smaller than the event's amount is
        grossed up to it and the difference decoded as a fee event, keeping the
        net wallet movement unchanged.
        """
        candidate = None
        for event in decoded_events:
            if (
                    id(event) not in consumed and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.location_label == location_label
            ):
                if event.amount == amount:
                    candidate = event
                    break
                if event.amount < amount and candidate is None:
                    candidate = event

        if candidate is None:
            return  # a movement inside the protocol that never touched the wallet

        consumed.add(id(candidate))
        if (fee_amount := amount - candidate.amount) > ZERO:
            candidate.amount = amount
            decoded_events.append(self.base.make_event_next_index(
                tx_ref=transaction.tx_hash,
                timestamp=transaction.timestamp,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=token,
                amount=fee_amount,
                location_label=location_label,
                notes=f'Spend {fee_amount} {token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',
                counterparty=CPT_FLYING_TULIP,
                address=self.deployment.positions_manager,
            ))
        candidate.event_type = to_event_type
        candidate.event_subtype = to_event_subtype
        candidate.notes = notes
        candidate.counterparty = CPT_FLYING_TULIP
        candidate.address = self.deployment.positions_manager

    def _handle_positions_manager_events(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        consumed: set[int] = set()  # ids of transfer events already claimed by an event
        for tx_log in all_logs:
            if tx_log.address != self.deployment.positions_manager:
                continue

            beneficiary = None
            if (topic := tx_log.topics[0]) in (PM_DEPOSIT_TOPIC, WITHDRAW_TOPIC, PM_BORROW_TOPIC, PM_REPAY_TOPIC):  # noqa: E501
                if not self.base.is_tracked(user := bytes_to_address(tx_log.topics[1])):
                    continue
                token = self.base.get_or_create_evm_token(
                    address=bytes_to_address(tx_log.topics[2]),
                )
            elif topic in (PM_DEPOSIT_FOR_TOPIC, PM_REPAY_FOR_TOPIC):
                payer = bytes_to_address(tx_log.topics[1])
                user = beneficiary = bytes_to_address(tx_log.topics[2])
                if (
                        payer in self.deployment.engines or  # position-internal rebalancing
                        not self.base.any_tracked([payer, beneficiary])
                ):
                    continue
                token = self.base.get_or_create_evm_token(
                    address=bytes_to_address(tx_log.topics[3]),
                )
            else:
                continue

            amount = token_normalized_value(
                token_amount=int.from_bytes(tx_log.data[0:32]),
                token=token,
            )
            if topic in (PM_DEPOSIT_TOPIC, PM_DEPOSIT_FOR_TOPIC, PM_REPAY_TOPIC, PM_REPAY_FOR_TOPIC):  # noqa: E501
                if topic in (PM_DEPOSIT_TOPIC, PM_DEPOSIT_FOR_TOPIC):
                    notes = f'Deposit {amount} {token.symbol} in {LEND_LABEL}'
                    to_event_type = HistoryEventType.DEPOSIT
                    to_event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                else:
                    notes = f'Repay {amount} {token.symbol} in {LEND_LABEL}'
                    to_event_type = HistoryEventType.SPEND
                    to_event_subtype = HistoryEventSubType.PAYBACK_DEBT
                if beneficiary is not None and not self.base.is_tracked(beneficiary):
                    notes += f' for {beneficiary}'
                self._reconcile_spend(
                    transaction=transaction,
                    decoded_events=decoded_events,
                    consumed=consumed,
                    token=token,
                    amount=amount,
                    location_label=user if beneficiary is None else None,
                    to_event_type=to_event_type,
                    to_event_subtype=to_event_subtype,
                    notes=notes,
                )
            else:  # WITHDRAW_TOPIC or PM_BORROW_TOPIC
                if topic == WITHDRAW_TOPIC:
                    notes = f'Withdraw {amount} {token.symbol} from {LEND_LABEL}'
                    to_event_type = HistoryEventType.WITHDRAWAL
                    to_event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                else:
                    notes = f'Borrow {amount} {token.symbol} from {LEND_LABEL}'
                    to_event_type = HistoryEventType.RECEIVE
                    to_event_subtype = HistoryEventSubType.GENERATE_DEBT
                self._reconcile_receive(
                    transaction=transaction,
                    decoded_events=decoded_events,
                    consumed=consumed,
                    token=token,
                    amount=amount,
                    location_label=user,
                    to_event_type=to_event_type,
                    to_event_subtype=to_event_subtype,
                    notes=notes,
                )

        return decoded_events

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(
            (self.deployment.positions_manager, *self.deployment.meta_actions),
            CPT_FLYING_TULIP,
        )

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_FLYING_TULIP: [(0, self._handle_positions_manager_events)]}
