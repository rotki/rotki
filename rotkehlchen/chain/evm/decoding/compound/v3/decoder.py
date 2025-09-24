import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import WITHDRAW_TOPIC, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    COMPOUND_V3_SUPPLY,
    COMPOUND_V3_SUPPLY_COLLATERAL,
    COMPOUND_V3_WITHDRAW_COLLATERAL,
    CPT_COMPOUND_V3,
    REWARD_CLAIMED,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Compoundv3CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            rewards_address: 'ChecksumEvmAddress',
            bulker_address: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.rewards_address = rewards_address
        self.bulker_address = bulker_address
        self.underlying_tokens: dict[EvmToken, EvmToken | None] = {}

    def _get_compound_underlying_token(self, compound_token: EvmToken) -> EvmToken | None:
        """Get the underlying token for a compound token."""
        if compound_token not in self.underlying_tokens:
            if (
                compound_token.underlying_tokens is None or
                len(compound_token.underlying_tokens) == 0
            ):
                log.debug(f'No underlying tokens found for {compound_token}')
                self.underlying_tokens[compound_token] = None
            else:
                try:  # if not in cached mapping, fetch from DB and add it
                    self.underlying_tokens[compound_token] = EvmToken(evm_address_to_identifier(
                        address=compound_token.underlying_tokens[0].address,
                        chain_id=self.evm_inquirer.chain_id,
                        token_type=compound_token.underlying_tokens[0].token_kind,
                    ))
                except (WrongAssetType, UnknownAsset) as e:
                    log.error(f'Could not derive underlying token from {compound_token}: {e}')

        return self.underlying_tokens.get(compound_token)  # return from cached mapping

    def decode_reward_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode a compound v3 reward claiming"""
        if context.tx_log.topics[0] != REWARD_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_DECODING_OUTPUT

        reward_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=bytes_to_address(context.tx_log.topics[3]),
            chain_id=self.base.evm_inquirer.chain_id,
            token_kind=TokenKind.ERC20,
            evm_inquirer=self.base.evm_inquirer,
        )
        amount_raw = int.from_bytes(context.tx_log.data)
        amount = asset_normalized_value(amount_raw, reward_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == recipient and event.asset == reward_token and event.address == self.rewards_address and event.amount == amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_COMPOUND_V3
                event.notes = f'Collect {event.amount} {reward_token.symbol} from compound'
                break

        return DEFAULT_DECODING_OUTPUT

    def _correct_supply_or_withdraw_event(
            self,
            decoded_events: list['EvmEvent'],
            transaction: 'EvmTransaction',  # pylint: disable=unused-argument
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Post decoding function to correct supply/withdraw event's receive amount in notes."""
        for event in decoded_events:
            if ((
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED
            ) or (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED
            )) and event.counterparty == CPT_COMPOUND_V3 and event.notes is not None:
                event.notes = event.notes.format(amount=event.amount)  # set the amount
                break
        return decoded_events

    def _decode_supply_or_repay_event(
            self,
            context: DecoderContext,
            compound_token: 'EvmToken',
    ) -> DecodingOutput:
        """Decode a compound v3 supply or repay event. Takes decoder context and
        the compound v3 wrapped token of the supplied/withdrawn underlying token."""
        if (underlying_token := self._get_compound_underlying_token(compound_token)) is None:
            log.error(
                f'At compound v3 supply/withdraw decoding of tx '
                f'{context.transaction.tx_hash.hex()} the underlying token was not found.',
            )
            return DEFAULT_DECODING_OUTPUT

        receiving_ctoken = False
        for tx_log in context.all_logs:
            if (
                tx_log.address == compound_token.evm_address and
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(tx_log.topics[1]) == ZERO_ADDRESS and  # from
                bytes_to_address(tx_log.topics[2]) == bytes_to_address(context.tx_log.topics[2])  # to  # noqa: E501
            ):
                receiving_ctoken = True
                break

        may_wrap_eth = underlying_token.symbol == 'WETH' and self.evm_inquirer.native_token == A_ETH  # noqa: E501
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data),
            asset=underlying_token,
        )
        paired_event, action_from_event_type, action_to_event_subtype, action_to_notes, asset_matches, compound_token_matches, underlying_asset_symbol = None, None, None, None, False, False, ''  # noqa: E501
        for event in context.decoded_events:
            if event.asset == underlying_token:
                asset_matches = True
                underlying_asset_symbol = underlying_token.symbol
                compound_token_matches = event.address == compound_token.evm_address
            elif may_wrap_eth:
                asset_matches = True
                underlying_asset_symbol = 'ETH'
                compound_token_matches = event.address == self.bulker_address

            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    asset_matches and amount == event.amount and
                    compound_token_matches
            ):
                event.counterparty = CPT_COMPOUND_V3
                if receiving_ctoken:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {amount} {underlying_asset_symbol} into Compound v3'
                    paired_event = event
                    action_from_event_type = HistoryEventType.RECEIVE
                    action_to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    action_to_notes = f'Receive {{amount}} {compound_token.symbol} from Compound v3'  # {amount} to be replaced in post decoding  # noqa: E501
                else:
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                    event.notes = f'Repay {amount} {underlying_asset_symbol} on Compound v3'

                break
        else:  # did not break/find anything
            log.error(
                'At compound v3 supply/withdraw decoding of tx '
                f'{context.transaction.tx_hash.hex()} the action item data was not found.',
            )
            return DEFAULT_DECODING_OUTPUT

        # create an action item for the receive of the cTokens. It's possible that
        # there is no cToken received if you just supply collateral to the COMET contract
        action_items = []
        if paired_event is not None and action_from_event_type is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=action_from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=compound_token,
                to_event_subtype=action_to_event_subtype,
                to_notes=action_to_notes,
                to_counterparty=CPT_COMPOUND_V3,
                paired_events_data=((paired_event,), True),
            ))

        return DecodingOutput(action_items=action_items)

    def _decode_withdraw_or_borrow_event(
            self,
            context: DecoderContext,
            compound_token: EvmToken,
    ) -> DecodingOutput:
        """Decode a compound v3 withdraw or borrow event. Takes decoder context and
        the compound v3 wrapped token of the withdrawn/borrowed underlying token."""
        if (underlying_token := self._get_compound_underlying_token(compound_token)) is None:
            log.error(
                f'At compound v3 supply/withdraw decoding of tx '
                f'{context.transaction.tx_hash.hex()} the underlying token was not found.',
            )
            return DEFAULT_DECODING_OUTPUT

        may_wrap_eth = underlying_token.symbol == 'WETH' and self.evm_inquirer.native_token == A_ETH  # noqa: E501
        sending_ctoken = False
        for tx_log in context.all_logs:
            if (
                    tx_log.address == compound_token.evm_address and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    (  # check the from sender matches
                        (send_from_address := bytes_to_address(tx_log.topics[1])) == bytes_to_address(context.tx_log.topics[2]) or  # noqa: E501
                        (may_wrap_eth and send_from_address == bytes_to_address(context.tx_log.topics[1]))  # noqa: E501
                    ) and
                bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS  # to
            ):
                sending_ctoken = True
                break

        paired_event, action_from_event_type, action_to_event_subtype, action_to_notes, asset_matches, compound_token_matches = None, None, None, None, False, False  # noqa: E501
        for event in context.decoded_events:
            if event.asset == underlying_token:
                asset_matches = True
                compound_token_matches = event.address == compound_token.evm_address
            elif may_wrap_eth:
                asset_matches = True
                compound_token_matches = event.address == self.bulker_address

            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    asset_matches and compound_token_matches
            ):
                if sending_ctoken:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Withdraw {event.amount} {event.asset.symbol_or_name()} from Compound v3'  # noqa: E501
                    paired_event = event
                    action_from_event_type = HistoryEventType.SPEND
                    action_to_event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    action_to_notes = f'Return {{amount}} {compound_token.symbol} to Compound v3'  # {amount} to be replaced in post decoding  # noqa: E501
                else:
                    event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                    event.notes = f'Borrow {event.amount} {event.asset.symbol_or_name()} from Compound v3'  # noqa: E501

                event.counterparty = CPT_COMPOUND_V3
                break
        else:
            log.error(
                f'Could not find any compound v3 withdraw or borrow event in tx '
                f'{context.transaction.tx_hash.hex()}.',
            )

        action_items = []  # also create an action item for the spend of the cTokens
        if paired_event is not None and action_from_event_type is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=action_from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=compound_token,
                to_event_subtype=action_to_event_subtype,
                to_notes=action_to_notes,
                to_counterparty=CPT_COMPOUND_V3,
                paired_events_data=((paired_event,), False),
            ))

        return DecodingOutput(action_items=action_items)

    def _decode_collateral_movement(
            self,
            context: DecoderContext,
            compound_token: EvmToken,
    ) -> DecodingOutput:
        """Decode compound v3 supply/withdraw collateral events"""
        collateral_asset = EvmToken(evm_address_to_identifier(
            address=bytes_to_address(context.tx_log.topics[3]),
            chain_id=self.evm_inquirer.chain_id,
            token_type=TokenKind.ERC20,
        ))
        collateral_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data),
            asset=collateral_asset,
        )

        for event in context.decoded_events:
            if (
                event.event_type in {HistoryEventType.SPEND, HistoryEventType.RECEIVE} and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == collateral_amount and
                event.asset == collateral_asset and
                event.address == compound_token.evm_address
            ):
                transfer_event = event
                event.counterparty = CPT_COMPOUND_V3
                if event.event_type == HistoryEventType.SPEND:
                    notes_action = 'Enable'
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {collateral_amount} {collateral_asset.symbol} into Compound v3'  # noqa: E501
                else:
                    notes_action = 'Disable'
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {collateral_amount} {collateral_asset.symbol} from Compound v3'  # noqa: E501

                collateral_event = self.base.make_event_next_index(
                    tx_hash=context.transaction.tx_hash,
                    timestamp=context.transaction.timestamp,
                    event_type=HistoryEventType.INFORMATIONAL,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=ZERO,
                    asset=event.asset,
                    location_label=event.location_label,
                    counterparty=event.counterparty,
                    notes=f'{notes_action} {collateral_amount} {collateral_asset.symbol} as collateral on Compound v3',  # noqa: E501
                    address=event.address,
                )
                break
        else:
            log.error(
                f'Could not find any compound v3 supply/withdraw collateral event in tx '
                f'{context.transaction.tx_hash.hex()}.',
            )
            return DEFAULT_DECODING_OUTPUT

        context.decoded_events.append(collateral_event)
        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=[transfer_event, collateral_event],
        )
        return DEFAULT_DECODING_OUTPUT

    def decode_compound_token_movement(
            self,
            context: DecoderContext,
            compound_token: EvmToken,
    ) -> DecodingOutput:
        """Decode a compound v3 token movement"""
        if (
            context.tx_log.topics[0] not in {
                COMPOUND_V3_SUPPLY, COMPOUND_V3_SUPPLY_COLLATERAL,
                WITHDRAW_TOPIC, COMPOUND_V3_WITHDRAW_COLLATERAL,
            } or self.base.any_tracked([
                bytes_to_address(context.tx_log.topics[1]),  # from_address
                bytes_to_address(context.tx_log.topics[2]),  # to_address
            ]) is False
        ):
            return DEFAULT_DECODING_OUTPUT

        if context.tx_log.topics[0] == COMPOUND_V3_SUPPLY:
            return self._decode_supply_or_repay_event(
                context=context,
                compound_token=compound_token,
            )
        elif context.tx_log.topics[0] == WITHDRAW_TOPIC:
            return self._decode_withdraw_or_borrow_event(
                context=context,
                compound_token=compound_token,
            )
        else:
            return self._decode_collateral_movement(
                context=context,
                compound_token=compound_token,
            )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.rewards_address: (self.decode_reward_claim,)} | {
            token.evm_address: (self.decode_compound_token_movement, token)
            for token in GlobalDBHandler.get_evm_tokens(
                chain_id=self.evm_inquirer.chain_id,
                protocol=CPT_COMPOUND_V3,
            )
        }

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return dict.fromkeys(GlobalDBHandler.get_addresses_by_protocol(
            chain_id=self.evm_inquirer.chain_id,
            protocol=CPT_COMPOUND_V3,
        ), CPT_COMPOUND_V3)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_COMPOUND_V3: [(0, self._correct_supply_or_withdraw_event)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_COMPOUND_V3,
            label='Compound V3',
            image='compound.svg',
        ),)
