import logging
from abc import abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, Optional

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import (
    CHAIN_TO_WRAPPED_TOKEN,
    asset_normalized_value,
    get_single_underlying_token,
)
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import (
    CPT_AAVE_V3,
    DISABLE_COLLATERAL,
    ENABLE_COLLATERAL,
    LIQUIDATION_CALL,
    WITHDRAW,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Commonv2v3LikeDecoder(EvmDecoderInterface):
    def __init__(
            self,
            counterparty: Literal['aave-v2', 'aave-v3', 'spark'],
            label: Literal['AAVE v2', 'AAVE v3', 'Spark'],
            pool_addresses: Sequence['ChecksumEvmAddress'],
            deposit_signature: bytes,
            borrow_signature: bytes,
            repay_signature: bytes,
            native_gateways: tuple['ChecksumEvmAddress', ...],
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        self.counterparty = counterparty
        self.pool_addresses = pool_addresses
        self.deposit_signature = deposit_signature
        self.borrow_signature = borrow_signature
        self.repay_signature = repay_signature
        self.native_gateways = native_gateways
        self.label = label
        self.wrapped_native_token = CHAIN_TO_WRAPPED_TOKEN[evm_inquirer.blockchain].resolve_to_evm_token()  # noqa: E501
        EvmDecoderInterface.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    @abstractmethod
    def decode_liquidation(self, context: DecoderContext) -> None:
        """Decode AAVE v2/v3 liquidations. When a liquidation happens the user returns the debt
        token and part of the collateral deposited is lost too. Those two events happen as
        transfers in a transaction started by the liquidator."""

    def _address_is_aave_contract(self, queried_address: 'ChecksumEvmAddress') -> bool:
        """Utility function for checking if a queried_address is an address of an
        aave token. Returns True if it is an aave token, or False if it is not."""
        return GlobalDBHandler.get_protocol_for_asset(
            asset_identifier=evm_address_to_identifier(
                address=queried_address,
                chain_id=self.node_inquirer.chain_id,
                token_type=TokenKind.ERC20,
            ),
        ) == self.counterparty

    def _token_is_aave_contract(self, asset: 'Asset') -> bool:
        """Utility function for checking if a asset is an aave token.
        Returns True if it is an aave token, or False if it is not."""
        return GlobalDBHandler.get_protocol_for_asset(
            asset_identifier=asset.identifier,
        ) == self.counterparty

    def _decode_collateral_events(
            self,
            token: 'EvmToken',
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
    ) -> Optional['EvmEvent']:
        """Decode aave v2/v3 collateral events"""
        user = bytes_to_address(tx_log.topics[2])
        if not self.base.is_tracked(user):
            return None
        return self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=token,
            amount=ZERO,
            location_label=user,
            notes=f'{"Enable" if tx_log.topics[0] == ENABLE_COLLATERAL else "Disable"} {token.symbol} as collateral on {self.label}',  # noqa: E501
            counterparty=self.counterparty,
            address=transaction.to_address,
        )

    def _decode_deposit(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> tuple[EvmEvent | None, EvmEvent | None]:
        """Decode aave v2/v3 deposit event. Returns the Deposit and Receive events."""
        user = bytes_to_address(tx_log.data[:32])
        try:
            on_behalf_of = bytes_to_address(tx_log.topics[2])
        except DeserializationError:
            on_behalf_of = None

        # in the case of needing to wrap the native asset aave uses the
        # (NATIVE_CURRENCY)_GATEWAY contract and the user is the contract address
        if (
            (user not in self.native_gateways and not self.base.is_tracked(user)) and
            (on_behalf_of is None or not self.base.is_tracked(on_behalf_of))
        ):
            return None, None

        amount = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[32:64]),
            asset=token,
        )
        deposit_event, receive_event = None, None
        for event in decoded_events:
            if (
                event.address is not None and
                (event.location_label == user or (event.location_label == on_behalf_of and user in self.native_gateways)) and  # noqa: E501
                (self.counterparty == CPT_AAVE_V3 or event.amount == amount) and  # For aave v3 we can't match amounts exactly  # noqa: E501
                event.event_subtype == HistoryEventSubType.NONE and (
                    self._address_is_aave_contract(queried_address=event.address) or
                    event.address == ZERO_ADDRESS or
                    event.address in self.native_gateways
                )
            ):
                if (
                    event.event_type == HistoryEventType.SPEND and
                    (event.asset == token or (user in self.native_gateways and event.asset == self.node_inquirer.native_token)) and  # noqa: E501
                    event.address != ZERO_ADDRESS
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} into {self.label}'  # noqa: E501
                    if on_behalf_of is not None and user not in self.native_gateways and on_behalf_of != user:  # noqa: E501
                        event.notes += f' on behalf of {on_behalf_of}'
                    event.counterparty = self.counterparty
                    deposit_event = event
                elif (
                    event.address == ZERO_ADDRESS and
                    self._token_is_aave_contract(event.asset) and
                    (
                        (underlying_token := get_single_underlying_token(event.asset.resolve_to_evm_token())) is not None and  # noqa: E501
                        (underlying_token == token or (user in self.native_gateways and underlying_token == self.wrapped_native_token))  # noqa: E501
                    )
                ):
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Receive {event.amount} {resolved_asset.symbol} from {self.label}'  # noqa: E501
                    event.counterparty = self.counterparty
                    receive_event = event

        return deposit_event, receive_event

    def _decode_withdrawal(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> tuple[EvmEvent | None, EvmEvent | None]:
        """Decode aave v2/v3 withdrawal event. Returns the Return and Withdraw events."""
        user = bytes_to_address(tx_log.topics[2])
        to = bytes_to_address(tx_log.topics[3])
        return_event, withdraw_event = None, None
        if (
            not (is_wnative_user := user in self.native_gateways) and
            not self.base.any_tracked([user, to])
        ):
            return None, None
        amount = asset_normalized_value(
            amount=int.from_bytes(tx_log.data),
            asset=token,
        )
        symbol = self.node_inquirer.native_token.symbol if is_wnative_user else token.symbol
        notes = f'Withdraw {amount} {symbol} from {self.label}'
        if to != user:
            notes += f' to {to}'

        for event in decoded_events:
            if (
                event.address is not None and
                event.event_type in {HistoryEventType.SPEND, HistoryEventType.RECEIVE} and
                event.event_subtype == HistoryEventSubType.NONE and (
                    self._address_is_aave_contract(queried_address=event.address) or
                    event.address == ZERO_ADDRESS or
                    event.address in self.native_gateways
                )
            ):
                if (
                    (event.location_label == to or (event.asset == self.node_inquirer.native_token and is_wnative_user)) and  # noqa: E501
                    event.event_type == HistoryEventType.RECEIVE and
                    event.address != ZERO_ADDRESS
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    if is_wnative_user is False:  # else location label is correctly set by the transfer decoder  # noqa: E501
                        event.location_label = user

                    event.notes = notes
                    withdraw_event = event
                    event.counterparty = self.counterparty
                elif (
                    event.event_type != HistoryEventType.RECEIVE and
                    (event.address == ZERO_ADDRESS or event.address in self.native_gateways) and
                    self._token_is_aave_contract(event.asset)
                ):
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {event.amount} {event.asset.symbol_or_name()} to {self.label}'  # noqa: E501
                    return_event = event
                    event.counterparty = self.counterparty

        return return_event, withdraw_event

    def _decode_borrow(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> tuple[EvmEvent | None, EvmEvent | None]:
        """Decode aave v2/v3 borrow event. Returns the Receive and Borrow events."""
        on_behalf_of = bytes_to_address(tx_log.topics[2])
        user = bytes_to_address(tx_log.data[:32])
        if not self.base.any_tracked([user, on_behalf_of]):
            return None, None

        amount = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[32:64]),
            asset=token,
        )
        rate_mode = int.from_bytes(tx_log.data[64:96])
        # Aave uses ray math https://docs.aave.com/developers/v/1.0/developing-on-aave/important-considerations#ray-math  # noqa: E501
        # To get the rate we have to divide the value by 1e27. And then multiply by 100 to get the percentage.  # noqa: E501
        rate = int.from_bytes(tx_log.data[96:128]) / FVal(RAY) * 100
        notes = f'Borrow {amount} {token.symbol} from {self.label} with {"stable" if rate_mode == 1 else "variable"} APY {rate.num:.2f}%'  # noqa: E501
        if on_behalf_of != user:
            notes += f' on behalf of {on_behalf_of}'
        debt_event, receive_event = None, None
        for event in decoded_events:
            if (
                event.address is not None and
                event.amount == amount and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user and
                event.event_type == HistoryEventType.RECEIVE and (
                    self._address_is_aave_contract(queried_address=event.address) or
                    event.address == ZERO_ADDRESS or
                    event.address in self.native_gateways
                )
            ):
                if (
                    event.asset == token and
                    event.address != ZERO_ADDRESS
                ):
                    event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                    event.notes = notes
                    event.counterparty = self.counterparty
                    debt_event = event
                elif (
                    event.address == ZERO_ADDRESS and
                    self._token_is_aave_contract(event.asset)
                ):
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Receive {amount} {resolved_asset.symbol} from {self.label}'
                    event.counterparty = self.counterparty
                    receive_event = event

        return receive_event, debt_event

    def _decode_repay(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> tuple[EvmEvent | None, EvmEvent | None]:
        """Decode aave v2/v3 repay event. Returns the Return and Repay events."""
        user = bytes_to_address(tx_log.topics[2])
        repayer = bytes_to_address(tx_log.topics[3])
        return_event, repay_event = None, None
        if not self.base.any_tracked([user, repayer]):
            return None, None

        for event in decoded_events:
            if (
                event.address is not None and
                event.location_label == repayer and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and (
                    self._address_is_aave_contract(queried_address=event.address) or
                    event.address == ZERO_ADDRESS or
                    event.address in self.native_gateways
                )
            ):
                if (
                    event.address == ZERO_ADDRESS and
                    self._token_is_aave_contract(event.asset)
                ):
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.counterparty = self.counterparty
                    event.notes = f'Return {event.amount} {resolved_asset.symbol} to {self.label}'
                    return_event = event
                    if repayer != user:
                        event.notes += f' for {user}'
                elif event.address != ZERO_ADDRESS:
                    event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                    event.counterparty = self.counterparty
                    event.notes = f'Repay {event.amount} {token.symbol} on {self.label}'
                    repay_event = event
                    if repayer != user:
                        event.notes += f' for {user}'

        return return_event, repay_event

    def _decode_lending_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes AAVE v2/v3 Lending Pool events"""
        if context.tx_log.topics[0] not in (
            LIQUIDATION_CALL,
            ENABLE_COLLATERAL,
            DISABLE_COLLATERAL,
            WITHDRAW,
            self.deposit_signature,
            self.borrow_signature,
            self.repay_signature,
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == LIQUIDATION_CALL:
            # the liquidation event has two tokens and needs to be checked per event
            self.decode_liquidation(context)
            return DEFAULT_EVM_DECODING_OUTPUT

        token = EvmToken(evm_address_to_identifier(
            address=bytes_to_address(context.tx_log.topics[1]),
            token_type=TokenKind.ERC20,
            chain_id=self.node_inquirer.chain_id,
        ))

        if context.tx_log.topics[0] in (ENABLE_COLLATERAL, DISABLE_COLLATERAL):
            event = self._decode_collateral_events(token, context.transaction, context.tx_log)
            return EvmDecodingOutput(
                events=[event] if event is not None else None,
                matched_counterparty=self.counterparty,
            )

        if context.tx_log.topics[0] == self.deposit_signature:
            paired_events = self._decode_deposit(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == WITHDRAW:
            paired_events = self._decode_withdrawal(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == self.borrow_signature:
            paired_events = self._decode_borrow(token, context.tx_log, context.decoded_events)
        else:  # Repay
            paired_events = self._decode_repay(token, context.tx_log, context.decoded_events)

        if None in paired_events:
            log.warning(  # can happen in cases where one of the events comes later such as in test_aave_v3_withdraw_with_bigger_interest  # noqa: E501
                f'Could not find all paired events in {self.counterparty} tx {context.transaction.tx_hash!s}'  # noqa: E501
                f' on {self.node_inquirer.chain_name}.',
            )

        maybe_reshuffle_events(  # Make sure that the paired events are in order
            ordered_events=paired_events,
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=self.counterparty)

    def _decode_incentives_common(
            self,
            context: 'DecoderContext',
            to_idx: int,
            claimer_raw: bytes,
            reward_token_address: ChecksumEvmAddress,
            amount_raw: bytes,
    ) -> EvmDecodingOutput:
        user_tracked = self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1]))
        to_tracked = self.base.is_tracked(to_address := bytes_to_address(context.tx_log.topics[to_idx]))  # noqa: E501
        claimer_tracked = self.base.is_tracked(claimer := bytes_to_address(claimer_raw))

        if not user_tracked and not to_tracked and not claimer_tracked:
            return DEFAULT_EVM_DECODING_OUTPUT

        reward_token = self.base.get_or_create_evm_token(address=reward_token_address)
        amount = asset_normalized_value(
            amount=int.from_bytes(amount_raw),
            asset=reward_token,
        )

        for event in context.decoded_events:
            if (  # not checking subtype NONE as in the stkAAVE case it can already be decoded as RECEIVE_WRAPPED  # noqa: E501
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == reward_token and
                    event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = self.counterparty
                event.notes = f'Claim {amount} {reward_token.resolve_to_asset_with_symbol().symbol}'  # noqa: E501

                if not to_tracked:
                    event.notes += f' for {to_address}'
                    event.location_label = claimer
                    if user != to_address:
                        event.notes += f' on behalf of {user}'

                else:
                    event.location_label = to_address

                event.notes += f' from {self.label} incentives'
                event.address = context.tx_log.address

                break

        else:
            log.error(
                f'Failed to find the {self.label} incentive reward transfer for {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash!s}.',  # noqa: E501
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(matched_counterparty=self.counterparty)

    # DecoderInterface method
    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.pool_addresses, (self._decode_lending_pool_events,))
