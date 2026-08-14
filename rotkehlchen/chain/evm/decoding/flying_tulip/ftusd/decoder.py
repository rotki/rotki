import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3, ZERO_ADDRESS
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
    CLAIMED_TOPIC,
    FLYING_TULIP_FTUSD_DEPLOYMENTS,
    MINTED_TOPIC,
    OUTFLOW_EXECUTED_TOPIC,
    OUTFLOW_QUEUED_TOPIC,
    REDEEMED_TOPIC,
    VAULT_RELAYER_FEE_PAID_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FlyingTulipFtusdCommonDecoder(FlyingTulipCommonDecoder):
    """Decode ftUSD mint/redeem and sftUSD staking activity.

    ftUSD is minted from and redeemed into collateral through the MintAndRedeem
    contract. The protocol fee is taken inside the conversion rate, so the event
    amounts match the user's transfers exactly. Staking deposits ftUSD into the
    EpochRewardsVault, an ERC-4626 vault whose shares are the sftUSD token, and
    rewards are paid out in FT via a separate claim.
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
        self.deployment = FLYING_TULIP_FTUSD_DEPLOYMENTS[evm_inquirer.chain_id]
        self.ftusd = self.base.get_or_create_evm_token(address=self.deployment.ftusd_token)
        self.ft_token = self.base.get_or_create_evm_token(address=self.deployment.ft_token)
        # transfers are only matched against these protocol counterparties, so
        # an unrelated equal-amount transfer in the same tx cannot be claimed
        self.mint_redeem_addresses = frozenset((self.deployment.mint_and_redeem,)) | self.deployment.wrappers  # noqa: E501
        self.payout_addresses = frozenset((self.deployment.staking_vault,)) | self.deployment.wrappers  # noqa: E501

    def _decode_mint_redeem(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode ftUSD mints and redemptions as swaps between collateral and ftUSD."""
        if context.tx_log.topics[0] == MINTED_TOPIC:
            collateral_amount_raw = int.from_bytes(context.tx_log.data[64:96])
            ftusd_amount_raw = int.from_bytes(context.tx_log.data[96:128])
        elif context.tx_log.topics[0] == REDEEMED_TOPIC:
            ftusd_amount_raw = int.from_bytes(context.tx_log.data[64:96])
            collateral_amount_raw = int.from_bytes(context.tx_log.data[128:160])
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        from_address = bytes_to_address(context.tx_log.topics[1])
        to_address = bytes_to_address(context.tx_log.topics[2])
        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.topics[3]),
        )
        collateral_amount = token_normalized_value(
            token_amount=collateral_amount_raw,
            token=collateral,
        )
        ftusd_amount = token_normalized_value(token_amount=ftusd_amount_raw, token=self.ftusd)
        if context.tx_log.topics[0] == MINTED_TOPIC:
            out_asset, out_amount, in_asset, in_amount = collateral, collateral_amount, self.ftusd, ftusd_amount  # noqa: E501
        else:
            out_asset, out_amount, in_asset, in_amount = self.ftusd, ftusd_amount, collateral, collateral_amount  # noqa: E501

        out_event = in_event = None
        for event in context.decoded_events:  # find both legs before mutating anything
            if (
                    out_event is None and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == from_address and
                    event.asset == out_asset and
                    event.amount == out_amount and
                    event.address in self.mint_redeem_addresses
            ):
                out_event = event
            elif (
                    in_event is None and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == to_address and
                    event.asset == in_asset and
                    event.amount == in_amount and
                    event.address in self.mint_redeem_addresses
            ):
                in_event = event
            if out_event is not None and in_event is not None:
                break

        if in_event is None and out_event is not None and (queued_amount := self._find_queued_outflow(  # noqa: E501
            context=context,
            recipient=to_address,
            token=in_asset,
        )) is not None:
            # A rate-limited payout: the circuit breaker holds the output and
            # pays it out in a later transaction, so only the spend leg exists.
            out_event.event_type = HistoryEventType.DEPOSIT
            out_event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
            out_event.notes = f'Swap {out_amount} {out_asset.symbol} in {FLYING_TULIP_LABEL} for {queued_amount} {in_asset.symbol} queued by the circuit breaker'  # noqa: E501
            out_event.counterparty = CPT_FLYING_TULIP
            out_event.address = context.tx_log.address
            return DEFAULT_EVM_DECODING_OUTPUT

        if out_event is None or in_event is None:
            # Only decode complete swaps: with a single leg (the other party is
            # untracked) the wallet movement is left as a plain transfer.
            log.warning(
                'Failed to find both sides of a %s ftUSD mint/redeem in transaction %s',
                FLYING_TULIP_LABEL,
                context.transaction,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event.event_type = HistoryEventType.TRADE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.notes = f'Swap {out_amount} {out_asset.symbol} in {FLYING_TULIP_LABEL}'
        out_event.counterparty = CPT_FLYING_TULIP
        out_event.address = context.tx_log.address
        in_event.event_type = HistoryEventType.TRADE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.notes = f'Receive {in_amount} {in_asset.symbol} as the result of a swap in {FLYING_TULIP_LABEL}'  # noqa: E501
        in_event.counterparty = CPT_FLYING_TULIP
        in_event.address = context.tx_log.address

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    def _find_queued_outflow(
            self,
            context: DecoderContext,
            recipient: ChecksumEvmAddress,
            token: EvmToken,
    ) -> FVal | None:
        """Return the amount of a rate-limited payout the circuit breaker queued
        for the recipient in this transaction, if any. The queued funds are paid
        out from the circuit breaker in a later transaction.
        """
        for tx_log in context.all_logs:
            if (
                    tx_log.address == self.deployment.circuit_breaker and
                    tx_log.topics[0] == OUTFLOW_QUEUED_TOPIC and
                    bytes_to_address(tx_log.topics[2]) == token.evm_address and
                    bytes_to_address(tx_log.topics[3]) == recipient
            ):
                return token_normalized_value(
                    token_amount=int.from_bytes(tx_log.data[0:32]),
                    token=token,
                )

        return None

    def _decode_circuit_breaker(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the delayed payout of a rate-limited mint/redeem/unstake."""
        if context.tx_log.topics[0] != OUTFLOW_EXECUTED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.topics[3]),
        )
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=token,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == recipient and
                    event.asset == token and
                    event.amount == amount and
                    event.address == self.deployment.circuit_breaker
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.notes = f'Receive {amount} {token.symbol} released from the {FLYING_TULIP_LABEL} circuit breaker queue'  # noqa: E501
                event.counterparty = CPT_FLYING_TULIP
                break
        else:
            log.warning(
                'Failed to find the released payout of a %s circuit breaker '
                'queue in transaction %s',
                FLYING_TULIP_LABEL,
                context.transaction,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_staking_vault(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == VAULT_RELAYER_FEE_PAID_TOPIC:
            return self._decode_relayer_fee(context)
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            return self._decode_vault_deposit(context)
        if context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            return self._decode_vault_withdrawal(context)
        if context.tx_log.topics[0] == CLAIMED_TOPIC:
            return self._decode_reward_claim(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_relayer_fee(self, context: DecoderContext) -> EvmDecodingOutput:
        """Split the relayer fee out of the user's gross transfer into the vault.

        On relayed staking the user sends assets plus the relayer fee in a single
        transfer and the vault forwards the fee, so the fee is carved out here to
        let the deposit leg match the ERC-4626 Deposit event exactly. When the fee
        is paid from the protocol side (unstaking) the user's transfers are already
        net and nothing matches, so no event is created.
        """
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        fee_token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.data[0:32]),
        )
        fee_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=fee_token,
        )
        deposited_assets = {  # the amounts the vault deposits of this transaction report
            token_normalized_value(
                token_amount=int.from_bytes(tx_log.data[0:32]),
                token=fee_token,
            )
            for tx_log in context.all_logs
            if (
                tx_log.address == context.tx_log.address and
                tx_log.topics[0] == DEPOSIT_TOPIC
            )
        }
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == user and
                    event.asset == fee_token and
                    event.address == context.tx_log.address and  # the transfer into the vault
                    event.amount > fee_amount and
                    event.amount - fee_amount in deposited_assets  # ties the fee to its stake
            ):
                event.amount -= fee_amount
                context.decoded_events.append(self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=fee_token,
                    amount=fee_amount,
                    location_label=user,
                    notes=f'Spend {fee_amount} {fee_token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',  # noqa: E501
                    counterparty=CPT_FLYING_TULIP,
                    address=context.tx_log.address,
                ))
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vault_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.any_tracked([
            sender := bytes_to_address(context.tx_log.topics[1]),
            owner := bytes_to_address(context.tx_log.topics[2]),  # vault share owner
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        assets_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=self.ftusd,
        )
        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=(vault_token := self.base.get_or_create_evm_token(
                address=self.deployment.staking_vault,
            )),
        )
        out_event = in_event = None
        for event in context.decoded_events:
            if (
                    out_event is None and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == sender and
                    event.asset == self.ftusd and
                    event.amount == assets_amount and
                    event.address == context.tx_log.address  # the transfer into the vault
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {assets_amount} ftUSD in the {FLYING_TULIP_LABEL} sftUSD vault'  # noqa: E501
                event.counterparty = CPT_FLYING_TULIP
                event.address = context.tx_log.address
                out_event = event
            elif (
                    in_event is None and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    event.location_label == owner and
                    event.asset == vault_token and
                    event.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {shares_amount} sftUSD from depositing in the {FLYING_TULIP_LABEL} sftUSD vault'  # noqa: E501
                event.counterparty = CPT_FLYING_TULIP
                in_event = event
            if out_event is not None and in_event is not None:
                break

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _find_payout_relayer_fee(
            self,
            context: DecoderContext,
            user: ChecksumEvmAddress,
            token: EvmToken,
    ) -> FVal:
        """Return the relayer fee the vault paid out of a user's withdrawal or claim.

        On relayed flows the fee is deducted from the payout before it reaches
        the wallet, so it only shows in the vault's RelayerFeePaid log.
        """
        fee_log = None
        for tx_log in context.all_logs:
            if (
                    tx_log.address == self.deployment.staking_vault and
                    tx_log.topics[0] == VAULT_RELAYER_FEE_PAID_TOPIC and
                    tx_log.log_index < context.tx_log.log_index and
                    bytes_to_address(tx_log.topics[1]) == user and
                    bytes_to_address(tx_log.data[0:32]) == token.evm_address and
                    (fee_log is None or tx_log.log_index > fee_log.log_index)
            ):  # the vault emits the fee log right before its payout event, so
                fee_log = tx_log  # the nearest preceding one belongs to this payout

        if fee_log is None or any(
            # Another payout or deposit between the fee log and this payout
            # means the fee belongs to that earlier action, not to this one.
            tx_log.address == self.deployment.staking_vault and
            tx_log.topics[0] in (DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3, CLAIMED_TOPIC) and
            fee_log.log_index < tx_log.log_index < context.tx_log.log_index
            for tx_log in context.all_logs
        ):
            return ZERO

        return token_normalized_value(
            token_amount=int.from_bytes(fee_log.data[32:64]),
            token=token,
        )

    def _make_relayer_fee_event(
            self,
            context: DecoderContext,
            token: EvmToken,
            fee_amount: FVal,
            location_label: ChecksumEvmAddress,
    ) -> EvmEvent:
        return self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=token,
            amount=fee_amount,
            location_label=location_label,
            notes=f'Spend {fee_amount} {token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=self.deployment.staking_vault,
        )

    def _decode_vault_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.any_tracked([
            receiver := bytes_to_address(context.tx_log.topics[2]),
            owner := bytes_to_address(context.tx_log.topics[3]),  # vault share owner
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        assets_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=self.ftusd,
        )
        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=(vault_token := self.base.get_or_create_evm_token(
                address=self.deployment.staking_vault,
            )),
        )
        out_event = in_event = None
        for event in context.decoded_events:  # find both legs before mutating anything
            if (
                    out_event is None and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == owner and
                    event.asset == vault_token and
                    event.amount == shares_amount and
                    event.address == ZERO_ADDRESS  # the share burn
            ):
                out_event = event
            elif (
                    in_event is None and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == receiver and
                    event.asset == self.ftusd and
                    event.amount == assets_amount and
                    event.address in self.payout_addresses
            ):
                in_event = event
            if out_event is not None and in_event is not None:
                break

        queued_amount = None
        if in_event is None:
            queued_amount = self._find_queued_outflow(
                context=context,
                recipient=receiver,
                token=self.ftusd,
            )
            if queued_amount is None:
                # Do not half-decode: without a payout (and no queue marker) the
                # share burn is left as a plain transfer too.
                log.warning(
                    'Failed to find the payout of a %s sftUSD withdrawal in transaction %s',
                    FLYING_TULIP_LABEL,
                    context.transaction,
                )
                return DEFAULT_EVM_DECODING_OUTPUT

        if out_event is not None:
            out_event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            notes = f'Return {shares_amount} sftUSD to the {FLYING_TULIP_LABEL} sftUSD vault'
            if queued_amount is not None:
                # A rate-limited payout: the circuit breaker holds the ftUSD and
                # pays it out in a later transaction.
                notes += f' with the payout of {queued_amount} ftUSD queued by the circuit breaker'
            out_event.notes = notes
            out_event.counterparty = CPT_FLYING_TULIP

        fee_event = None
        if in_event is not None:
            # The Withdraw event's assets are net of any relayer fee, so gross
            # the withdrawal up and decode the fee explicitly. The net wallet
            # movement stays unchanged.
            withdrawn_amount = assets_amount
            if (fee_amount := self._find_payout_relayer_fee(
                context=context,
                user=owner,
                token=self.ftusd,
            )) > ZERO:
                withdrawn_amount += fee_amount
                in_event.amount = withdrawn_amount
                fee_event = self._make_relayer_fee_event(
                    context=context,
                    token=self.ftusd,
                    fee_amount=fee_amount,
                    location_label=receiver,
                )
                context.decoded_events.append(fee_event)
            in_event.event_type = HistoryEventType.WITHDRAWAL
            in_event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
            in_event.notes = f'Withdraw {withdrawn_amount} ftUSD from the {FLYING_TULIP_LABEL} sftUSD vault'  # noqa: E501
            in_event.counterparty = CPT_FLYING_TULIP
            in_event.address = context.tx_log.address

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_reward_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(receiver := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        paid_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=self.ft_token,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == receiver and
                    event.asset == self.ft_token and
                    event.amount == paid_amount and
                    event.address == context.tx_log.address  # paid out by the vault
            ):
                # The Claimed event's paid amount is net of any relayer fee, so
                # gross the reward up and decode the fee explicitly.
                claimed_amount = paid_amount
                if (fee_amount := self._find_payout_relayer_fee(
                    context=context,
                    user=bytes_to_address(context.tx_log.topics[1]),
                    token=self.ft_token,
                )) > ZERO:
                    claimed_amount += fee_amount
                    event.amount = claimed_amount
                    context.decoded_events.append(self._make_relayer_fee_event(
                        context=context,
                        token=self.ft_token,
                        fee_amount=fee_amount,
                        location_label=receiver,
                    ))
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Claim {claimed_amount} FT from {FLYING_TULIP_LABEL} ftUSD staking'
                event.counterparty = CPT_FLYING_TULIP
                return DEFAULT_EVM_DECODING_OUTPUT

        log.warning(  # the vault transfers the reward before emitting Claimed
            'Failed to find the reward transfer of a %s staking claim in transaction %s',
            FLYING_TULIP_LABEL,
            context.transaction,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.deployment.mint_and_redeem: (self._decode_mint_redeem,),
            self.deployment.staking_vault: (self._decode_staking_vault,),
            self.deployment.circuit_breaker: (self._decode_circuit_breaker,),
        }
