import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_single_underlying_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.common import Commonv2v3LikeDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from ..constants import CPT_AAVE_V3, MINT
from .constants import BORROW, BURN, DEPOSIT, REPAY, REWARDS_CLAIMED, SWAPPED

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Aavev3LikeCommonDecoder(Commonv2v3LikeDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_addresses: Sequence['ChecksumEvmAddress'],
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            treasury: 'ChecksumEvmAddress',
            incentives: 'ChecksumEvmAddress',
            collateral_swap_address: 'ChecksumEvmAddress | None' = None,
            label: Literal['AAVE v3', 'Spark'] = 'AAVE v3',
            counterparty: Literal['aave-v3', 'spark'] = CPT_AAVE_V3,
    ):
        Commonv2v3LikeDecoder.__init__(
            self,
            counterparty=counterparty,
            label=label,
            pool_addresses=pool_addresses,
            deposit_signature=DEPOSIT,
            borrow_signature=BORROW,
            repay_signature=REPAY,
            native_gateways=native_gateways,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.treasury = treasury
        self.incentives = incentives
        self.collateral_swap_address = collateral_swap_address

    def decode_liquidation(self, context: 'DecoderContext') -> None:
        """
        Decode AAVE v3 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if not self.base.is_tracked(bytes_to_address(context.tx_log.topics[3])):  # liquidator  # noqa: E501
            return

        amounts = [  # payback amount and liquidation amount
            asset_normalized_value(
                amount=int.from_bytes(tx_log.data[:32]),
                asset=EvmToken(evm_address_to_identifier(
                    address=tx_log.address,
                    token_type=TokenKind.ERC20,
                    chain_id=self.node_inquirer.chain_id,
                )),
            ) for tx_log in context.all_logs
            if tx_log.topics[0] == BURN and tx_log.topics[1] == context.tx_log.topics[3]
        ]

        if len(amounts) != 2:
            log.warning(
                f'Found invalid number of payback and liquidation amounts '
                f'in {self.label} liquidation: {context.transaction.tx_hash.hex()}',
            )
            return

        for event in context.decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if amounts[1] == event.amount and event.address == ZERO_ADDRESS:
                # we are transferring the debt token
                event.event_type = HistoryEventType.LOSS
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An {self.label} position got liquidated for {event.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = self.counterparty
                event.address = context.tx_log.address
            elif amounts[0] == event.amount and event.address == ZERO_ADDRESS:
                # we are transferring the aTOKEN
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.amount} {asset.symbol} for an {self.label} position'
                event.counterparty = self.counterparty
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differentiate paybacks happening in liquidations.  # noqa: E501
            elif event.address == self.treasury:  # fee
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Spend {event.amount} {asset.symbol} as an {self.label} fee'
                event.counterparty = self.counterparty

    def _decode_incentives(self, context: 'DecoderContext') -> EvmDecodingOutput:
        if context.tx_log.topics[0] != REWARDS_CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        return self._decode_incentives_common(
            context=context,
            to_idx=3,
            claimer_raw=context.tx_log.data[0:32],
            reward_token_address=bytes_to_address(context.tx_log.topics[2]),
            amount_raw=context.tx_log.data[32:64],
        )

    def _decode_interest(
            self,
            decoded_events: list['EvmEvent'],
            transaction: 'EvmTransaction',
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Post-decode AAVE v3 interest events.
        1. First find and identify the decoded events (supply/receive or withdraw/return)
        2. Also, if there is a mint on simple transfer, decode it as interest
        3. Then find the mint/burn event in the logs, if found decode it as interest
        4. Finally, adjust the existing events in the end to make supply/withdraw amount equal to
           receive/return amount, because the interest event is created separately.

        Returns the final list of the decoded events."""
        supply_events, withdraw_events, return_events, receive_events = [], [], [], []
        swap_event = migrateout_event = migratein_event = swap_receive_event = maybe_earned_event = None  # noqa: E501
        # list of every interest event we've decoded in this transaction. We iterate this later
        # to append any remaining interest events after all pairings are done.
        interest_events_in_order: list[EvmEvent] = []
        # interest_event_lookup tells us which interest event belongs to that same asset/user
        # so we can insert it right after that pair instead of leaving it somewhere unrelated
        # in the sequence.
        interest_event_lookup: dict[Asset, list[EvmEvent]] = defaultdict(list)
        used_interest_event_ids: set[int] = set()

        for event in decoded_events:  # identify the events decoded till now
            if (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            ):
                supply_events.append(event)
            elif (
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED
            ):
                withdraw_events.append(event)
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED and
                    self._token_is_aave_contract(event.asset)
            ):
                receive_events.append(event)
            elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and
                    self._token_is_aave_contract(event.asset)
            ):
                return_events.append(event)
            elif (
                    event.event_type == HistoryEventType.MIGRATE and
                    event.event_subtype == HistoryEventSubType.SPEND
            ):
                migrateout_event = event
            elif (
                event.counterparty == CPT_AAVE_V3 and
                event.event_type == HistoryEventType.TRADE and
                event.extra_data is not None
            ):
                swap_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    self._token_is_aave_contract(event.asset)
            ):  # we received aTokens when transferring, so it can be an interest event
                if migrateout_event is not None:  # this is migrating from v2
                    event.event_type = HistoryEventType.MIGRATE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} from migrating an AAVE v2 position to v3'  # noqa: E501
                    event.address = None  # no need to have zero address
                    migratein_event = event
                elif swap_event is not None and swap_event.extra_data is not None:  # logic for collateral swap  # noqa: E501
                    if (
                        received_addr := swap_event.extra_data.get('received_addr')
                    ) is None:
                        log.error(
                            f'Aave V3 swap event in {transaction} missing extradata. Skipping',
                        )
                        continue

                    received_token = event.asset.resolve_to_evm_token()
                    if not any(received_addr == x.address for x in received_token.underlying_tokens or []):  # noqa: E501
                        log.error(f'{received_addr} is not in the underlying tokens for {received_token}: {received_token.underlying_tokens=}')  # noqa: E501
                        continue

                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.notes = f'Receive {event.amount} {received_token.symbol} as the result of collateral swap in AAVE v3'  # noqa: E501
                    swap_event.extra_data = None
                    swap_receive_event = event

                else:
                    event.event_subtype = HistoryEventSubType.INTEREST
                    event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} as interest earned from {self.label}'  # noqa: E501
                    maybe_earned_event = event  # this may also be the mint transfer event which was already decoded (for some chains and assets) -- remember it to check it down later  # noqa: E501

                event.counterparty = self.counterparty
                if event.event_subtype == HistoryEventSubType.INTEREST:
                    interest_events_in_order.append(event)
                    interest_event_lookup[event.asset].append(event)

        if swap_event and swap_receive_event:
            maybe_reshuffle_events(  # groups together the receive/interest event and then the collateral swap  # noqa: E501
                ordered_events=[e for e in decoded_events if e.event_subtype == HistoryEventSubType.INTEREST and e.asset == swap_event.asset] + [swap_event, swap_receive_event],  # noqa: E501
                events_list=decoded_events,
            )

        if migrateout_event and migratein_event:
            maybe_reshuffle_events(
                ordered_events=[migrateout_event, migratein_event],
                events_list=decoded_events,
            )
            return decoded_events

        # categorize the events, based on token_event and wrapped_event
        if len(supply_events) != 0 and len(receive_events) != 0:
            token_events = supply_events
            wrapped_events = receive_events
        elif len(withdraw_events) != 0:
            token_events = withdraw_events
            if len(return_events) != 0:
                wrapped_events = return_events
            elif len(receive_events) != 0:
                wrapped_events = receive_events
            elif maybe_earned_event is not None:
                wrapped_events = [maybe_earned_event]
                receive_events = [maybe_earned_event]
            else:
                log.error(f'Could not categorize the {self.label} events during interest decoding for transaction {transaction}')  # noqa: E501
                return decoded_events

        else:  # if not identified, return the decoded events
            return decoded_events

        user_address = token_events[0].location_label  # cannot be empty here.
        wrapped_events_assets = {evt.asset for evt in wrapped_events}
        earned_event = None
        for _log in all_logs:
            if (  # find the mint or burn event of aToken
                _log.topics[0] in (MINT, BURN) and (
                    # topics[2] is on_behalf_of, should be equal to the value we got above
                    bytes_to_address(_log.topics[2]) == user_address
                ) and (
                    balance_increase := asset_normalized_value(
                        amount=int.from_bytes(_log.data[32:64]),
                        asset=(earned_token := self.base.get_or_create_evm_token(
                            address=_log.address,
                        )),
                    )
                ) > 0
            ):  # parse the mint amount and balance_increase
                if _log.topics[0] == BURN and (earned_token := get_single_underlying_token(earned_token)) is None:  # type: ignore[assignment]  # we ignore if None  # noqa: E501
                    log.error(f'Failed to find underlying token for Aave v3 token {earned_token}. Skipping')  # noqa: E501
                    continue

                if (  # check if we need to create the earned event
                        maybe_earned_event is None or
                        maybe_earned_event.asset not in wrapped_events_assets or
                        balance_increase != maybe_earned_event.amount or
                        user_address != maybe_earned_event.location_label
                ):
                    decoded_events.append(earned_event := self.base.make_event_from_transaction(
                        transaction=transaction,
                        tx_log=_log,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.INTEREST,
                        asset=earned_token,
                        amount=balance_increase,
                        location_label=user_address,
                        notes=f'Receive {balance_increase} {earned_token.symbol} as interest earned from {self.label}',  # noqa: E501
                        counterparty=self.counterparty,
                    ))
                    interest_events_in_order.append(earned_event)
                    interest_event_lookup[earned_event.asset].append(earned_event)

        if len(supply_events) != 0 and len(receive_events) != 0:  # re-assign the receive amount  # noqa: E501
            for receive_event in receive_events:
                if (interest_amount := self._get_interest_amount_for_event(
                    event=receive_event,
                    interest_event_lookup=interest_event_lookup,
                )) == ZERO:
                    continue

                receive_event.amount = FVal((receive_event.amount - interest_amount).num.normalize())  # noqa: E501
                receive_event.notes = f'Receive {receive_event.amount} {receive_event.asset.resolve_to_asset_with_symbol().symbol} from {self.label}'  # noqa: E501

        if len(withdraw_events) != 0 and earned_event is not None:
            if len(return_events) != 0:  # re-assign the withdraw amounts
                for withdraw_event in withdraw_events:
                    if withdraw_event.asset.resolve_to_crypto_asset().symbol != earned_event.asset.resolve_to_crypto_asset().symbol:  # noqa: E501
                        continue  # we check symbols here due to monerium having multiple versions

                    withdraw_event.amount = FVal((withdraw_event.amount - earned_event.amount).num.normalize())  # noqa: E501
                    withdraw_event.notes = f'Withdraw {withdraw_event.amount} {withdraw_event.asset.resolve_to_asset_with_symbol().symbol} from {self.label}'  # noqa: E501

            if len(receive_events) != 0:
                for receive_event in receive_events[:]:
                    if (withdraw_asset := get_single_underlying_token(receive_event.asset.resolve_to_evm_token())) is None:  # noqa: E501
                        log.error(f'Failed to find underlying token for Aave v3 token {receive_event.asset}. Skipping')  # noqa: E501
                        continue

                    # receiving aToken, while withdrawing means interest > returned amount
                    receive_events.remove(receive_event)
                    return_event = receive_event
                    return_events.append(return_event)
                    if return_event in interest_events_in_order:
                        interest_events_in_order.remove(return_event)

                    if (interest_entries := interest_event_lookup.get(return_event.asset)) is not None:  # noqa: E501
                        interest_event_lookup[return_event.asset] = [
                            evt for evt in interest_entries
                            if evt is not return_event
                        ]
                        if len(interest_event_lookup[return_event.asset]) == 0:
                            interest_event_lookup.pop(return_event.asset, None)

                    used_interest_event_ids.discard(return_event.sequence_index)
                    # re-assign the values to the return event
                    if (matching_withdraw := next((x for x in withdraw_events if x.asset.resolve_to_asset_with_symbol().symbol == withdraw_asset.symbol), None)) is None:  # noqa: E501
                        log.error(f'Failed to find matching withdraw event for asset {withdraw_asset} in transaction {transaction}. Skipping')  # noqa: E501
                        continue

                    return_event.amount = matching_withdraw.amount
                    return_event.event_type = HistoryEventType.SPEND
                    return_event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    return_event.notes = f'Return {return_event.amount} {return_event.asset.resolve_to_asset_with_symbol().symbol} to {self.label}'  # noqa: E501

        ordered_events: list[EvmEvent] = []
        if len(supply_events) > 0 and len(receive_events) > 0:  # group supply/receive pairs by asset  # noqa: E501
            self._pair_events_by_asset(
                primary_events=supply_events,
                secondary_events=receive_events,
                ordered_events=ordered_events,
                interest_event_lookup=interest_event_lookup,
                used_interest_event_ids=used_interest_event_ids,
                match_fn=lambda primary, secondary: (
                    (underlying_token := get_single_underlying_token(secondary.asset.resolve_to_evm_token())) is not None and  # noqa: E501
                    (underlying_token == primary.asset or (underlying_token == self.node_inquirer.wrapped_native_token and primary.asset == self.node_inquirer.native_token))  # noqa: E501
                ),
            )

        if len(withdraw_events) > 0 and len(return_events) > 0:  # group withdraw/return pairs by asset  # noqa: E501
            self._pair_events_by_asset(
                primary_events=return_events,
                secondary_events=withdraw_events,
                ordered_events=ordered_events,
                interest_event_lookup=interest_event_lookup,
                used_interest_event_ids=used_interest_event_ids,
                match_fn=lambda primary, secondary: (  # use symbols due to Monerium and its different versions  # noqa: E501
                    (underlying_token := get_single_underlying_token(primary.asset.resolve_to_evm_token())) is not None and  # noqa: E501
                    (underlying_token.symbol == secondary.asset.resolve_to_crypto_asset().symbol or (underlying_token == self.node_inquirer.wrapped_native_token and secondary.asset == self.node_inquirer.native_token))  # noqa: E501
                ),
            )

        for interest_event in interest_events_in_order:
            if interest_event.sequence_index not in used_interest_event_ids:
                ordered_events.append(interest_event)
                used_interest_event_ids.add(interest_event.sequence_index)

        maybe_reshuffle_events(
            ordered_events=ordered_events,
            events_list=decoded_events,
        )
        return decoded_events

    @staticmethod
    def _pair_events_by_asset(
            primary_events: list['EvmEvent'],
            secondary_events: list['EvmEvent'],
            ordered_events: list['EvmEvent'],
            interest_event_lookup: 'dict[Asset, list["EvmEvent"]]',
            used_interest_event_ids: set[int],
            match_fn: 'Callable[["EvmEvent", "EvmEvent"], bool]',
    ) -> None:
        """Helper to pair events by underlying asset and track assets for interest events."""
        for primary_event in primary_events:
            matched_asset = {primary_event.asset}
            found_match = False
            for secondary_event in secondary_events:
                if match_fn(primary_event, secondary_event):
                    matched_asset.add(secondary_event.asset)
                    ordered_events.extend([primary_event, secondary_event])
                    found_match = True

            # add matching interest events for this asset pair
            if found_match:
                Aavev3LikeCommonDecoder._append_interest_events(
                    matched_asset=matched_asset,
                    location_label=primary_event.location_label,  # type: ignore  # we know it is an address
                    ordered_events=ordered_events,
                    interest_event_lookup=interest_event_lookup,
                    used_interest_event_ids=used_interest_event_ids,
                )

    @staticmethod
    def _append_interest_events(
            matched_asset: set['Asset'],
            location_label: 'ChecksumEvmAddress | None',
            ordered_events: list['EvmEvent'],
            interest_event_lookup: 'dict[Asset, list[EvmEvent]]',
            used_interest_event_ids: set[int],
    ) -> None:
        """Attach interest events matching the provided identifiers/location."""
        for asset in matched_asset:
            for interest_event in interest_event_lookup.get(asset, []):
                if (
                    interest_event.location_label != location_label or
                    interest_event.sequence_index in used_interest_event_ids
                ):
                    continue

                ordered_events.append(interest_event)
                used_interest_event_ids.add(interest_event.sequence_index)

    @staticmethod
    def _get_interest_amount_for_event(
            event: 'EvmEvent',
            interest_event_lookup: 'dict[Asset, list[EvmEvent]]',
    ) -> FVal:
        """Return the total interest amount already decoded for the same asset."""
        if (interest_events := interest_event_lookup.get(event.asset)) is None:
            return ZERO

        return FVal(sum(
            (interest_event.amount for interest_event in interest_events
            if interest_event.location_label == event.location_label),
            start=ZERO,
        ))

    def _collateral_swap(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Decode a collateral swap event from aave.

        This swapped event logs the underlying token swapped. At this point we have decoded
        only the spend event and not the receive events. Since what the user receives is
        the wrapped aave token we can't use the action item because we don't know which
        aave token we will receive. The receive event is decoded in _decode_interest that happens
        in the post decoding.
        """
        if context.tx_log.topics[0] != SWAPPED:
            return DEFAULT_EVM_DECODING_OUTPUT

        swapped_addr = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if (
                event.asset.is_evm_token() and
                event.amount == asset_normalized_value(
                    amount=int.from_bytes(context.tx_log.data[0:32]),  # swapped amount
                    asset=(resolved_token := event.asset.resolve_to_evm_token()),
                ) and
                any(token.address == swapped_addr for token in resolved_token.underlying_tokens or [])  # noqa: E501
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_AAVE_V3
                event.notes = f'Swap {event.amount} {resolved_token.symbol} AAVE v3 collateral'
                event.extra_data = {'received_addr': bytes_to_address(context.tx_log.topics[2])}  # used to decode the other leg of the trade. Is removed before saving the event in the db.  # noqa: E501
                break
        else:
            log.error(f'Failed to find aave v3 collateral swap in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    # DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        addresses = super().addresses_to_decoders() | {
            self.incentives: (self._decode_incentives,),
        }

        if self.collateral_swap_address:
            addresses |= {self.collateral_swap_address: (self._collateral_swap,)}

        return addresses

    @staticmethod  # DecoderInterface method
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_AAVE_V3,
            image='aave.svg',
        ),)

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(GlobalDBHandler.get_addresses_by_protocol(  # type: ignore[return-value]  # they are inherently strings
            chain_id=self.node_inquirer.chain_id,
            protocol=self.counterparty,
        ), self.counterparty) | dict.fromkeys(self.pool_addresses, self.counterparty)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_AAVE_V3: [(0, self._decode_interest)]}
