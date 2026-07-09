import logging
from typing import Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    CPT_KINETIQ,
    INSTANT_UNSTAKE_EXECUTED_TOPIC,
    KINETIQ_CPT_DETAILS,
    KINETIQ_EARN_QUEUE,
    KINETIQ_EARN_VAULT,
    KINETIQ_STAKING_MANAGERS,
    ONCHAIN_WITHDRAW_CANCELLED_TOPIC,
    ONCHAIN_WITHDRAW_REQUESTED_TOPIC,
    ONCHAIN_WITHDRAW_SOLVED_TOPIC,
    REDELEGATION_REQUESTED_TOPIC,
    STAKE_RECEIVED_TOPIC,
    VAULT_ENTER_TOPIC,
    VAULT_EXIT_TOPIC,
    VKHYPE_TOKEN_ID,
    WITHDRAWAL_CONFIRMED_TOPIC,
    WITHDRAWAL_QUEUED_TOPIC,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KinetiqDecoder(EvmDecoderInterface):
    """Decoder for the Kinetiq liquid staking protocol on hyperliquid

    Users stake native HYPE via a StakingManager and receive its LST (kHYPE for the
    flagship deployment, flowHYPE/HiHYPE/asxnHYPE/hylqHYPE for the institutional
    partner deployments which run the same contract). Unstaking happens either through
    the withdrawal queue (queueWithdrawal + confirmWithdrawal after the withdrawal
    delay) or instantly against the buffer for a fee.
    """

    def _decode_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode staking native HYPE for the staking manager's LST"""
        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.amount == hype_amount and
                    event.location_label == staker
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Stake {hype_amount} HYPE in Kinetiq'
                event.counterparty = CPT_KINETIQ
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.location_label == staker and
                    event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_evm_token().symbol} from staking in Kinetiq'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the HYPE spend and LST receive events for Kinetiq stake', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_queue_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode queueing an LST withdrawal from the staking manager"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        withdrawal_id = int.from_bytes(context.tx_log.topics[3])
        lst_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.amount == lst_amount and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Queue unstaking of {lst_amount} {event.asset.resolve_to_evm_token().symbol} for {hype_amount} HYPE from Kinetiq with withdrawal request id {withdrawal_id}'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                event.extra_data = {'withdrawal_id': withdrawal_id}
                break
        else:
            log.error('Failed to find the LST transfer event for Kinetiq queued withdrawal', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_confirm_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode confirming a queued withdrawal and receiving the unstaked HYPE.

        Multiple withdrawal requests can be confirmed in a single transaction but the
        HYPE is sent to the user in a single internal transaction, so the receive event
        is transformed only once, keeping its total amount.
        """
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Unstake {event.amount} HYPE from Kinetiq'
                event.counterparty = CPT_KINETIQ
                break
        else:  # can happen for the second and later confirmations of a batch
            if int.from_bytes(context.tx_log.data[:32]) != 0:  # only log if HYPE was expected
                found_transformed = any(
                    event.counterparty == CPT_KINETIQ and
                    event.event_type == HistoryEventType.WITHDRAWAL
                    for event in context.decoded_events
                )
                if not found_transformed:
                    log.error('Failed to find the HYPE receive event for Kinetiq confirmed withdrawal', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_instant_unstake(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode instantly unstaking the LST for HYPE against the buffer for a fee"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        lst_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.amount == lst_amount and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Instantly unstake {lst_amount} {event.asset.resolve_to_evm_token().symbol} from Kinetiq'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.amount == hype_amount and
                    event.location_label == user
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Receive {hype_amount} HYPE from unstaking in Kinetiq'
                event.counterparty = CPT_KINETIQ
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the LST spend and HYPE receive events for Kinetiq instant unstake', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_redelegation(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a validator redelegation request. This is an operator action moving
        delegated HYPE between hypercore validators and moves no user funds."""
        if not self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_validator = bytes_to_address(context.tx_log.topics[2])
        to_validator = bytes_to_address(context.tx_log.topics[3])
        amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_HYPE,
            amount=amount,
            location_label=sender,
            notes=f'Request redelegation of {amount} HYPE from validator {from_validator} to validator {to_validator} in Kinetiq',  # noqa: E501
            counterparty=CPT_KINETIQ,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_earn_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a deposit into the Kinetiq Earn vault (a Veda BoringVault).
        The user deposits kHYPE via the vault's teller and receives vkHYPE shares."""
        if context.tx_log.topics[0] != VAULT_ENTER_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(depositor := bytes_to_address(context.tx_log.topics[3])):
            return DEFAULT_EVM_DECODING_OUTPUT

        deposit_token = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
        deposit_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token=deposit_token,
        )
        shares_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == deposit_token and
                    event.amount == deposit_amount and
                    event.location_label == depositor
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {deposit_amount} {deposit_token.symbol} in Kinetiq Earn'
                event.counterparty = CPT_KINETIQ
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == VKHYPE_TOKEN_ID and
                    event.amount == shares_amount and
                    event.location_label == depositor and
                    event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {shares_amount} vkHYPE from depositing in Kinetiq Earn'
                event.counterparty = CPT_KINETIQ
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the deposit and vkHYPE receive events for Kinetiq Earn deposit', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_earn_withdraw_request(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode requesting a withdrawal of vkHYPE shares via the on-chain withdraw queue"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        asset_out_token = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[3]))  # noqa: E501
        shares_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        assets_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token=asset_out_token,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == VKHYPE_TOKEN_ID and
                    event.amount == shares_amount and
                    event.location_label == user and
                    event.address == KINETIQ_EARN_QUEUE
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Request withdrawal of {shares_amount} vkHYPE worth {assets_amount} {asset_out_token.symbol} from Kinetiq Earn'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                event.extra_data = {
                    'request_id': '0x' + context.tx_log.topics[1].hex(),
                    'amount_of_assets': str(assets_amount),
                    'asset_out': asset_out_token.identifier,
                }
                break
        else:
            log.error('Failed to find the vkHYPE transfer event for Kinetiq Earn withdrawal request', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_earn_withdraw_cancel(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode cancelling a queued Kinetiq Earn withdrawal, getting the shares back"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == VKHYPE_TOKEN_ID and
                    event.location_label == user and
                    event.address == KINETIQ_EARN_QUEUE
            ):
                event.notes = f'Receive back {event.amount} vkHYPE from a cancelled Kinetiq Earn withdrawal request'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                break
        else:
            log.error('Failed to find the vkHYPE transfer event for Kinetiq Earn withdrawal cancellation', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_earn_withdraw_solve(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the execution of a queued Kinetiq Earn withdrawal. A solver (possibly
        the user themselves) burns the queued vkHYPE shares and the user receives the
        withdrawn asset, so the receive transfer is decoded after this log and is
        transformed via an action item."""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        for tx_log in context.all_logs:  # the withdrawn asset is only in the vault Exit log
            if tx_log.address == KINETIQ_EARN_VAULT and tx_log.topics[0] == VAULT_EXIT_TOPIC:
                asset_out_token = self.base.get_or_create_evm_token(bytes_to_address(tx_log.topics[2]))  # noqa: E501
                break
        else:
            log.error('Failed to find the vault exit log for Kinetiq Earn withdrawal solve', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(
            action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset_out_token,
                location_label=user,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                to_notes=f'Withdraw {{amount}} {asset_out_token.symbol} from Kinetiq Earn',
                to_counterparty=CPT_KINETIQ,
            )],
            matched_counterparty=CPT_KINETIQ,
        )

    def _decode_earn_queue_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == ONCHAIN_WITHDRAW_REQUESTED_TOPIC:
            return self._decode_earn_withdraw_request(context)
        if context.tx_log.topics[0] == ONCHAIN_WITHDRAW_CANCELLED_TOPIC:
            return self._decode_earn_withdraw_cancel(context)
        if context.tx_log.topics[0] == ONCHAIN_WITHDRAW_SOLVED_TOPIC:
            return self._decode_earn_withdraw_solve(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_staking_manager_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == STAKE_RECEIVED_TOPIC:
            return self._decode_stake(context)
        if context.tx_log.topics[0] == WITHDRAWAL_QUEUED_TOPIC:
            return self._decode_queue_withdrawal(context)
        if context.tx_log.topics[0] == WITHDRAWAL_CONFIRMED_TOPIC:
            return self._decode_confirm_withdrawal(context)
        if context.tx_log.topics[0] == INSTANT_UNSTAKE_EXECUTED_TOPIC:
            return self._decode_instant_unstake(context)
        if context.tx_log.topics[0] == REDELEGATION_REQUESTED_TOPIC:
            return self._decode_redelegation(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(
            KINETIQ_STAKING_MANAGERS,
            (self._decode_staking_manager_events,),
        ) | {
            KINETIQ_EARN_VAULT: (self._decode_earn_deposit,),
            KINETIQ_EARN_QUEUE: (self._decode_earn_queue_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (KINETIQ_CPT_DETAILS,)
