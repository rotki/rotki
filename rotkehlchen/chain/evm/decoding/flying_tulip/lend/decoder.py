import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC_V3, WITHDRAW_TOPIC
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import (
    CPT_FLYING_TULIP,
    FLYING_TULIP_LABEL,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.decoder import FlyingTulipCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CLOSE_LEVERAGE_FILLED_TOPIC,
    CLOSE_LEVERAGE_FLASH_FILLED_TOPIC,
    COLLATERAL_SWAP_FILLED_TOPIC,
    COLLATERAL_SWAP_FLASH_FILLED_TOPIC,
    FLYING_TULIP_LEND_DEPLOYMENTS,
    OPEN_LEVERAGE_FILLED_TOPIC,
    OPEN_LEVERAGE_FLASH_FILLED_TOPIC,
    PM_BORROW_TOPIC,
    PM_DEPOSIT_FOR_TOPIC,
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
        # transfers are only matched against these protocol counterparties, so
        # an unrelated equal-amount transfer in the same tx cannot be claimed
        self.protocol_addresses = (
            frozenset((self.deployment.positions_manager,)) |
            self.deployment.meta_actions |
            self.deployment.yield_wrappers
        )

    def _reconcile_spend(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            consumed: set[int],
            token: EvmToken,
            amount: FVal,
            allowed_labels: tuple[ChecksumEvmAddress, ...],
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
            allow_fee_split: bool,
    ) -> EvmEvent | None:
        """Turn the wallet transfer funding a positions manager event into it.

        Relayed transactions send the relayer fee together with the funds in a
        single transfer through the meta-action entry points, so a transfer to
        one of them that is larger than the event's amount is split into the
        protocol movement plus a fee event. A full repayment can also use less
        than the sent amount and refund the rest, in which case the refund
        transfer is folded back into the split so only the actual fee remains.
        """
        candidate = None
        for event in decoded_events:
            if (
                    event.sequence_index not in consumed and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.location_label in allowed_labels and
                    event.address in self.protocol_addresses
            ):
                if event.amount == amount:
                    candidate = event
                    break
                if (
                        event.amount > amount and
                        event.address in self.deployment.meta_actions and  # only relayed transfers carry a fee  # noqa: E501
                        allow_fee_split and
                        candidate is None
                ):
                    candidate = event

        if candidate is None:
            # a movement inside the protocol that never touched the wallet
            log.debug('Found no matching transfer for a lend event in %s', transaction)
            return None

        if (fee_amount := candidate.amount - amount) > ZERO:
            # Fold an eventual refund of unused funds (a transfer straight back
            # from the entry point) into the split before treating the rest as fee.
            refund_event = next((
                event for event in decoded_events
                if (
                    event.sequence_index not in consumed and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.location_label == candidate.location_label and
                    event.address == candidate.address and
                    event.amount <= fee_amount
                )
            ), None)
            if refund_event is not None:
                fee_amount -= refund_event.amount
                decoded_events.remove(refund_event)

            candidate.amount = amount
            if fee_amount > ZERO:
                decoded_events.append(self.base.make_event_next_index(
                    tx_ref=transaction.tx_hash,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=token,
                    amount=fee_amount,
                    location_label=candidate.location_label,
                    notes=f'Spend {fee_amount} {token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',  # noqa: E501
                    counterparty=CPT_FLYING_TULIP,
                    address=self.deployment.positions_manager,
                ))

        consumed.add(candidate.sequence_index)
        candidate.event_type = to_event_type
        candidate.event_subtype = to_event_subtype
        candidate.notes = notes
        candidate.counterparty = CPT_FLYING_TULIP
        candidate.address = self.deployment.positions_manager
        return candidate

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
            allow_fee_split: bool,
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
                    event.sequence_index not in consumed and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.location_label == location_label and
                    event.address in self.protocol_addresses
            ):
                if event.amount == amount:
                    candidate = event
                    break
                if (
                        event.amount < amount and
                        event.address in self.deployment.meta_actions and  # only relayed payouts carry a fee  # noqa: E501
                        allow_fee_split and
                        (candidate is None or event.amount > candidate.amount)
                ):  # the payout is the largest transfer below the event amount
                    candidate = event

        if candidate is None:
            # a movement inside the protocol that never touched the wallet
            log.debug('Found no matching transfer for a lend event in %s', transaction)
            return

        consumed.add(candidate.sequence_index)
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
        # Parse the relevant positions manager events first, so the fee-split
        # heuristics know how many events compete for the same token's transfers.
        parsed_events = []
        for tx_log in all_logs:
            if tx_log.address != self.deployment.positions_manager:
                continue

            payer = beneficiary = None
            if (topic := tx_log.topics[0]) in (DEPOSIT_TOPIC_V3, WITHDRAW_TOPIC, PM_BORROW_TOPIC, PM_REPAY_TOPIC):  # noqa: E501
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

            parsed_events.append((topic, user, payer, beneficiary, token, token_normalized_value(
                token_amount=int.from_bytes(tx_log.data[0:32]),
                token=token,
            )))

        # A relayed transfer covers a single event's funds plus the fee. When
        # several events compete for the same token's transfers, inferring the
        # fee (or a refund) from an amount difference is ambiguous, so the
        # split is only allowed for a token with exactly one event in the
        # whole transaction (otherwise only exact matches are decoded).
        spend_topics = (DEPOSIT_TOPIC_V3, PM_DEPOSIT_FOR_TOPIC, PM_REPAY_TOPIC, PM_REPAY_FOR_TOPIC)
        token_counts: dict[ChecksumEvmAddress, int] = defaultdict(int)
        for _, _, _, _, token, _ in parsed_events:
            token_counts[token.evm_address] += 1

        # sequence indexes of the transfer events already claimed by an event.
        # They are unique within a transaction and, unlike the DB identifier,
        # they exist while decoding, before any of these events is written.
        consumed: set[int] = set()
        for topic, user, payer, beneficiary, token, amount in parsed_events:
            if topic in spend_topics:
                if topic in (DEPOSIT_TOPIC_V3, PM_DEPOSIT_FOR_TOPIC):
                    notes = f'Deposit {amount} {token.symbol} in {LEND_LABEL}'
                    to_event_type = HistoryEventType.DEPOSIT
                    to_event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                else:
                    notes = f'Repay {amount} {token.symbol} in {LEND_LABEL}'
                    to_event_type = HistoryEventType.SPEND
                    to_event_subtype = HistoryEventSubType.PAYBACK_DEBT
                matched = self._reconcile_spend(
                    transaction=transaction,
                    decoded_events=decoded_events,
                    consumed=consumed,
                    token=token,
                    amount=amount,
                    allowed_labels=(user,) if payer is None or beneficiary is None else (payer, beneficiary),  # noqa: E501
                    to_event_type=to_event_type,
                    to_event_subtype=to_event_subtype,
                    notes=notes,
                    allow_fee_split=token_counts[token.evm_address] == 1,
                )
                if (
                        matched is not None and
                        beneficiary is not None and
                        matched.location_label != beneficiary
                ):
                    # The transfer stays the payer's, since that is whose wallet
                    # the funds left; the position owner is recorded beside it
                    # rather than in the label balances are debited from. The
                    # owner's own entry comes from _decode_deposit_for.
                    matched.notes = f'{notes} for {beneficiary}'
                    matched.extra_data = (matched.extra_data or {}) | {
                        'beneficiary': beneficiary,
                    }
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
                    allow_fee_split=token_counts[token.evm_address] == 1,
                )

        return decoded_events

    def _decode_deposit_for(self, context: DecoderContext) -> EvmDecodingOutput:
        """Give the owner of a position funded by someone else an entry of their own.

        A deposit made for another address is the payer's transfer, so it stays
        theirs, and the position it opens belongs to the beneficiary. This runs
        while decoding rather than in the post-decoding rule because a payer
        nobody tracks leaves no wallet transfer at all: the rule would never be
        reached, and the position would never be found by balance discovery.
        """
        if context.tx_log.topics[0] != PM_DEPOSIT_FOR_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        payer = bytes_to_address(context.tx_log.topics[1])
        if (
                payer == (beneficiary := bytes_to_address(context.tx_log.topics[2])) or
                not self.base.is_tracked(beneficiary) or
                # A relayed deposit is paid by an entry point on the owner's own
                # behalf, and their transfer is already decoded as the deposit.
                payer in self.protocol_addresses or
                payer in self.deployment.engines
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.topics[3]),
        )
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=token,
        )
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=token,
            amount=amount,
            location_label=beneficiary,
            notes=f'Receive a deposit of {amount} {token.symbol} in {LEND_LABEL} paid by {payer}',
            counterparty=CPT_FLYING_TULIP,
            address=context.tx_log.address,
        ))
        # this event is what makes the owner known to lending balance discovery, and it
        # can appear long after the deposit, so ask for a balance refresh right away
        return EvmDecodingOutput(refresh_balances=True)

    def _decode_leverage_fill(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode leverage RFQ engine fills into informational history entries.

        The funds of a leverage fill move inside the positions manager (opens
        are flash-funded), so there is no wallet transfer to transform. The
        informational entry gives the position activity Flying Tulip
        attribution and seeds balance discovery, through which the position's
        actual collateral and debt are queried from the positions manager.
        """
        if (topic := context.tx_log.topics[0]) in (OPEN_LEVERAGE_FILLED_TOPIC, OPEN_LEVERAGE_FLASH_FILLED_TOPIC):  # noqa: E501
            action = 'Open'
        elif topic in (CLOSE_LEVERAGE_FILLED_TOPIC, CLOSE_LEVERAGE_FLASH_FILLED_TOPIC):
            action = 'Close'
        elif topic in (COLLATERAL_SWAP_FILLED_TOPIC, COLLATERAL_SWAP_FLASH_FILLED_TOPIC):
            action = 'Swap collateral in'
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        sell_token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.data[0:32]),
        )
        sell_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token=sell_token,
        )
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=sell_token,
            amount=sell_amount,
            location_label=user,
            notes=f'{action} a {FLYING_TULIP_LABEL} leverage position selling {sell_amount} {sell_token.symbol}',  # noqa: E501
            counterparty=CPT_FLYING_TULIP,
            address=context.tx_log.address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.deployment.leverage_engine: (self._decode_leverage_fill,),
            self.deployment.positions_manager: (self._decode_deposit_for,),
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        # The yield wrappers are included so that transactions routed through
        # an unknown entry point (a Safe, an EIP-7702 batch) still trigger the
        # post-decoding rule through the payout transfer's counterparty.
        return dict.fromkeys(self.protocol_addresses, CPT_FLYING_TULIP)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        # Priority 1: run after the common priority-0 rules, since this rule can
        # append fee events and the framework stops post decoding on additions.
        return {CPT_FLYING_TULIP: [(1, self._handle_positions_manager_events)]}
