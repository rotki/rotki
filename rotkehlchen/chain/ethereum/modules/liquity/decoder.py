import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.evm_event import LIQUITY_STAKING_DETAILS
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    ACTIVE_POOL,
    BALANCE_UPDATE,
    BORROWER_OPERATIONS,
    CPT_LIQUITY,
    DEPLOY_USER_PROXY_LQTY_V2,
    DEPOSIT_LQTY_V2,
    LIQUITY_STAKING,
    LIQUITY_V2_WRAPPER,
    LUSD_BORROWING_FEE_PAID,
    STABILITY_POOL,
    STABILITY_POOL_EVENTS,
    STABILITY_POOL_GAIN_WITHDRAW,
    STABILITY_POOL_LQTY_PAID_TO_DEPOSITOR,
    STABILITY_POOL_LQTY_PAID_TO_FRONTEND,
    STAKING_ETH_SENT,
    STAKING_LQTY_CHANGE,
    STAKING_LQTY_EVENTS,
    STAKING_REWARDS_ASSETS,
    WITHDRAW_LQTY_V2,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LiquityDecoder(EvmDecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.lusd = A_LUSD.resolve_to_crypto_asset()
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.lqty = A_LQTY.resolve_to_evm_token()

    def _decode_trove_operations(
            self,
            context: DecoderContext,
            post_decoding: bool = False,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != BALANCE_UPDATE:
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.maybe_get_proxy_owner(context.transaction.to_address) is not None and post_decoding is False:  # type: ignore[arg-type]  # transaction.to_address is not None here  # noqa: E501
            # If this is a transaction made via a DS Proxy, it needs to be handled in a
            # post-decoding rule. Returning matched_counterparty only here and not for other
            # cases since the post decoding rule needs to run only for ds proxies.
            # This comment applies to all decoding functions in this file.
            return EvmDecodingOutput(matched_counterparty=CPT_LIQUITY)

        debt_event: EvmEvent | None = None
        fee_event: EvmEvent | None = None
        for event in context.decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_LIQUITY)
                continue

            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.FEE and event.counterparty == CPT_LIQUITY and event.asset == self.lusd:  # noqa: E501
                fee_event = event
                if debt_event:  # debt event appeared before fee event. We need to make changes
                    # You borrow debt + fee, and right after pay the fee. If we
                    # don't do that the fee payment is a missing acquisition
                    debt_event.amount += fee_event.amount
                    debt_event.notes = f'Generate {debt_event.amount} LUSD from liquity'

            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_LUSD:
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_LIQUITY
                debt_event = event

                if fee_event:  # fee event appears before the debt event, we need to make changes
                    # You borrow debt + fee, and right after pay the fee. If we
                    # don't do that the fee payment is a missing acquisition
                    event.amount += fee_event.amount

                event.notes = f'Generate {event.amount} LUSD from liquity'

            elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_LUSD:  # noqa: E501
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Pay back {event.amount} LUSD debt to liquity'
            elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Deposit {event.amount} {crypto_asset.symbol} as collateral for liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} collateral from liquity'  # noqa: E501

        maybe_reshuffle_events(  # make sure debt generation event comes before fee
            ordered_events=[debt_event, fee_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stability_pool_event(
            self,
            context: DecoderContext,
            post_decoding: bool = False,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in STABILITY_POOL_EVENTS:
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.maybe_get_proxy_owner(context.transaction.to_address) is not None and post_decoding is False:  # type: ignore[arg-type]  # transaction.to_address is not None here  # noqa: E501
            return EvmDecodingOutput(matched_counterparty=CPT_LIQUITY)

        deposit_event, withdraw_event, reward_events = None, None, []
        collected_eth, collected_lqty = ZERO, ZERO
        if context.tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW:
            collected_eth = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=self.eth,
            )
        elif context.tx_log.topics[0] in {STABILITY_POOL_LQTY_PAID_TO_DEPOSITOR, STABILITY_POOL_LQTY_PAID_TO_FRONTEND}:  # noqa: E501
            collected_lqty = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=self.lqty,
            )
            if collected_lqty == ZERO:
                return DEFAULT_EVM_DECODING_OUTPUT

            if context.tx_log.topics[0] == STABILITY_POOL_LQTY_PAID_TO_FRONTEND:
                frontend_address = bytes_to_address(context.tx_log.topics[1])
                event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_LQTY,
                    amount=collected_lqty,
                    location_label=context.transaction.from_address,
                    notes=f'Paid {collected_lqty} LQTY as a frontend fee to {frontend_address}',
                    counterparty=CPT_LIQUITY,
                    address=context.tx_log.address,
                )
                return EvmDecodingOutput(events=[event])

        for event in context.decoded_events:  # modify the send/receive events
            if event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f"Deposit {event.amount} {self.lusd.symbol} in liquity's stability pool"  # noqa: E501
                deposit_event = event
            elif event.event_type == HistoryEventType.RECEIVE:
                if (
                    (
                        event.asset == self.eth and
                        event.amount == collected_eth and
                        context.tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW
                    ) or (
                        event.asset == self.lqty and
                        event.amount == collected_lqty and
                        context.tx_log.topics[0] == STABILITY_POOL_LQTY_PAID_TO_DEPOSITOR
                    )
                ):
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_LIQUITY
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f"Collect {event.amount} {resolved_asset.symbol} from liquity's stability pool"  # noqa: E501
                    reward_events.append(event)
                elif event.asset == self.lusd:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f"Withdraw {event.amount} {self.lusd.symbol} from liquity's stability pool"  # noqa: E501
                    withdraw_event = event
            elif event.counterparty == CPT_LIQUITY and event.event_type == HistoryEventType.STAKING:  # noqa: E501  # already decoded events
                if event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET:
                    deposit_event = event
                elif event.event_subtype == HistoryEventSubType.REMOVE_ASSET:
                    withdraw_event = event
                elif event.event_subtype == HistoryEventSubType.REWARD:
                    reward_events.append(event)

        maybe_reshuffle_events(
            ordered_events=[deposit_event, withdraw_event, *reward_events],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_borrower_operations(
            self,
            context: DecoderContext,
            post_decoding: bool = False,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != LUSD_BORROWING_FEE_PAID:
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.maybe_get_proxy_owner(context.transaction.to_address) is not None and post_decoding is False:  # type: ignore[arg-type]  # transaction.to_address is not None here  # noqa: E501
            return EvmDecodingOutput(matched_counterparty=CPT_LIQUITY)

        borrower = self.base.get_address_or_proxy_owner(bytes_to_address(context.tx_log.topics[1]))
        if borrower is None or self.base.is_tracked(borrower) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (fee_amount := asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=self.lusd,
        )) == ZERO:  # for many operations it emits a zero event log
            return DEFAULT_EVM_DECODING_OUTPUT

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_LUSD,
            amount=fee_amount,
            location_label=borrower,
            notes=f'Paid {fee_amount} LUSD as a borrowing fee',
            counterparty=CPT_LIQUITY,
            address=context.tx_log.address,
        )
        max_seq_index = 0  # put ordering logic here too since some times fee is seen last
        for decoded_event in context.decoded_events:
            max_seq_index = max(max_seq_index, decoded_event.sequence_index)
        event.sequence_index = max_seq_index + 1
        return EvmDecodingOutput(events=[event])

    def _decode_lqty_staking_deposits(
            self,
            context: DecoderContext,
            post_decoding: bool = False,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in STAKING_LQTY_EVENTS:
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.maybe_get_proxy_owner(context.transaction.to_address) is not None and post_decoding is False:  # type: ignore[arg-type]  # transaction.to_address is not None here  # noqa: E501
            return EvmDecodingOutput(matched_counterparty=CPT_LIQUITY)

        proxy_or_user_address, lqty_amount = None, ZERO
        if context.tx_log.topics[0] == STAKING_LQTY_CHANGE:
            proxy_or_user_address = bytes_to_address(context.tx_log.topics[1])
            lqty_amount = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=self.lqty,
            )

        deposit_withdraw_event, reward_events = None, []
        for event in context.decoded_events:
            if (
                context.tx_log.topics[0] == STAKING_LQTY_CHANGE and
                event.asset == A_LQTY and
                proxy_or_user_address in (event.address, event.location_label)
            ):
                extra_data = {
                    LIQUITY_STAKING_DETAILS: {
                        'staked_amount': str(lqty_amount),
                        'asset': self.lqty.identifier,
                    },
                }
                if event.event_type == HistoryEventType.SPEND:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f'Stake {event.amount} {self.lqty.symbol} in the Liquity protocol'  # noqa: E501
                    event.extra_data = extra_data
                    deposit_withdraw_event = event
                elif event.event_type == HistoryEventType.RECEIVE:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f'Unstake {event.amount} {self.lqty.symbol} from the Liquity protocol'  # noqa: E501
                    event.extra_data = extra_data
                    deposit_withdraw_event = event
            elif (
                context.tx_log.topics[0] == STAKING_ETH_SENT and
                event.asset in STAKING_REWARDS_ASSETS and
                event.event_type == HistoryEventType.RECEIVE
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_LIQUITY
                event.notes = f"Receive reward of {event.amount} {event.asset.resolve_to_crypto_asset().symbol} from Liquity's staking"  # noqa: E501
                reward_events.append(event)
            elif event.counterparty == CPT_LIQUITY and event.event_type == HistoryEventType.STAKING:  # noqa: E501
                if event.event_subtype == HistoryEventSubType.REWARD:  # already decoded reward events  # noqa: E501
                    reward_events.append(event)
                elif event.event_subtype in (HistoryEventSubType.DEPOSIT_ASSET, HistoryEventSubType.REMOVE_ASSET):  # already decoded deposit/withdraw event # noqa: E501
                    deposit_withdraw_event = event

        maybe_reshuffle_events(
            ordered_events=[deposit_withdraw_event, *reward_events],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_v2_staking(
            self,
            context: DecoderContext,
            is_deposit: bool,
    ) -> EvmDecodingOutput:
        user = self.base.get_address_or_proxy_owner(bytes_to_address(context.tx_log.topics[1]))
        recipient = self.base.get_address_or_proxy_owner(
            bytes_to_address(context.tx_log.data[0:32]),
        )
        if user is None or recipient is None or not self.base.any_tracked([user, recipient]):
            return DEFAULT_EVM_DECODING_OUTPUT

        if is_deposit:
            offset = 0
            verb = 'Stake'
            preposition = 'in'
            event_type = HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.DEPOSIT_ASSET
        else:
            offset = 32
            verb = 'Unstake'
            preposition = 'from'
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.REMOVE_ASSET

        lqty_deposit_withdraw_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=self.lqty,
        )
        lusd_received = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[64 + offset:96 + offset]),
            asset=self.lusd,
        )
        eth_received = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[128 + offset:160 + offset]),
            asset=A_ETH.resolve_to_crypto_asset(),
        )
        deposit_withdraw_event, lusd_reward_event, eth_reward_event, reward_events = None, None, None, []  # noqa: E501
        for event in context.decoded_events:
            if (
                event.asset == self.lqty and
                event.amount == lqty_deposit_withdraw_amount and
                event.event_type in (event_type, HistoryEventType.STAKING) and
                event.event_subtype in (HistoryEventSubType.NONE, event_subtype)
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = event_subtype
                event.counterparty = CPT_LIQUITY
                event.notes = f'{verb} {event.amount} LQTY {preposition} the Liquity V2 protocol'
                deposit_withdraw_event = event
            elif (
                event.asset == self.lusd and
                event.amount == lusd_received and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_LIQUITY
                event.notes = f"Collect {event.amount} LUSD from Liquity's stability pool"
                lusd_reward_event = event
                reward_events.append(event)
            elif (
                event.asset == A_ETH and
                event.amount == eth_received and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_LIQUITY
                event.notes = f"Collect {event.amount} ETH from Liquity's stability pool"
                eth_reward_event = event
                reward_events.append(event)

        new_events = []
        for amount_received, asset, existing_reward_event in (
                (lusd_received, self.lqty, lusd_reward_event),
                (eth_received, A_ETH, eth_reward_event),
        ):  # Means proxy received it, so create the event manually
            if amount_received != ZERO and existing_reward_event is None:
                reward_event = self.base.make_event_next_index(
                    tx_ref=context.transaction.tx_hash,
                    timestamp=context.transaction.timestamp,
                    event_type=HistoryEventType.STAKING,
                    event_subtype=HistoryEventSubType.REWARD,
                    asset=asset,
                    amount=amount_received,
                    location_label=user,
                    counterparty=CPT_LIQUITY,
                    notes=(
                        f"Collect {amount_received} {asset.resolve_to_crypto_asset().symbol} "
                        f"from Liquity's stability pool into the user's Liquity proxy"
                    ),
                    address=context.tx_log.address,
                )
                new_events.append(reward_event)
                reward_events.append(reward_event)

        maybe_reshuffle_events(
            ordered_events=[deposit_withdraw_event, *reward_events],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=new_events)

    def _decode_v2_deploy_proxy(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(
            events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.CREATE,
                asset=self.node_inquirer.native_token,
                amount=ZERO,
                location_label=user_address,
                counterparty=CPT_LIQUITY,
                address=LIQUITY_V2_WRAPPER,
                notes=f'Deploy Liquity proxy for {user_address} at {(proxy_address := bytes_to_address(context.tx_log.topics[2]))}',  # noqa: E501
                extra_data={'proxy_address': proxy_address},
            )],
        )

    def _decode_liquity_v2_wrapper(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode Liquity V2 wrapper transactions"""
        if context.tx_log.topics[0] == DEPOSIT_LQTY_V2:
            return self._decode_deposit_v2_staking(context, is_deposit=True)
        elif context.tx_log.topics[0] == WITHDRAW_LQTY_V2:
            return self._decode_deposit_v2_staking(context, is_deposit=False)
        elif context.tx_log.topics[0] == DEPLOY_USER_PROXY_LQTY_V2:
            return self._decode_v2_deploy_proxy(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ACTIVE_POOL: (self._decode_trove_operations,),
            STABILITY_POOL: (self._decode_stability_pool_event,),
            LIQUITY_STAKING: (self._decode_lqty_staking_deposits,),
            BORROWER_OPERATIONS: (self._decode_borrower_operations,),
            LIQUITY_V2_WRAPPER: (self._decode_liquity_v2_wrapper,),
        }

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """
        Handles post decoding for liquity. It re-applies liquity decoding methods on top of
        the full list of decoded events.

        In case of usage of a DS Proxy transfers `proxy` <-> `liquity contracts` and
        transfers `proxy` <-> `user address` are in a bad order, so we have to have all erc20 / eth
        transfers decoded before applying liquity-specific logic.

        Can't use action items here because action items require to know all properties of an
        event that we expect to appear in the future, and we unfortunately can't know them.
        """
        for tx_log in all_logs:
            if tx_log.address == ACTIVE_POOL:
                decoding_rule = self._decode_trove_operations
            elif tx_log.address == STABILITY_POOL:
                decoding_rule = self._decode_stability_pool_event
            elif tx_log.address == LIQUITY_STAKING:
                decoding_rule = self._decode_lqty_staking_deposits
            elif tx_log.address == BORROWER_OPERATIONS:
                decoding_rule = self._decode_borrower_operations
            else:
                continue

            decoding_output = decoding_rule(
                context=DecoderContext(
                    tx_log=tx_log,
                    transaction=transaction,
                    action_items=[],
                    all_logs=all_logs,
                    decoded_events=decoded_events,
                ),
                post_decoding=True,
            )
            if decoding_output.events is not None:
                decoded_events.extend(decoding_output.events)

        return decoded_events

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_LIQUITY: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIQUITY, label='Liquity', image='liquity.svg'),)
