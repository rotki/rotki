from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import (
    DISABLE_COLLATERAL,
    ENABLE_COLLATERAL,
    LIQUIDATION_CALL,
    WITHDRAW,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


class Commonv2v3Decoder(DecoderInterface):
    def __init__(
            self,
            counterparty: Literal['aave-v2', 'aave-v3'],
            label: Literal['AAVE v2', 'AAVE v3'],
            pool_address: 'ChecksumEvmAddress',
            deposit_signature: bytes,
            borrow_signature: bytes,
            repay_signature: bytes,
            eth_gateways: tuple['ChecksumEvmAddress', ...],
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        self.counterparty = counterparty
        self.pool_address = pool_address
        self.deposit_signature = deposit_signature
        self.borrow_signature = borrow_signature
        self.repay_signature = repay_signature
        self.eth_gateways = eth_gateways
        self.label = label
        DecoderInterface.__init__(
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

    def _decode_collateral_events(
            self,
            token: 'EvmToken',
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
    ) -> Optional['EvmEvent']:
        """Decode aave v2/v3 collateral events"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        if not self.base.is_tracked(user):
            return None
        return self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=token,
            balance=Balance(),
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
    ) -> None:
        """Decode aave v2/v3 deposit event"""
        user = hex_or_bytes_to_address(tx_log.data[:32])
        on_behalf_of = hex_or_bytes_to_address(tx_log.topics[2]) if hex_or_bytes_to_str(tx_log.topics[2]) != '' else None  # noqa: E501
        # in the case of needing to wrap ETH to WETH aave uses the ETH_GATEWAY contract and the
        # user is the contract address
        if (
            (user not in self.eth_gateways and not self.base.is_tracked(user)) and
            (on_behalf_of is None or not self.base.is_tracked(on_behalf_of))
        ):
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data[32:64]),
            asset=token,
        )
        notes = f'Deposit {amount} {token.symbol} into {self.label}'
        if on_behalf_of is not None and user not in self.eth_gateways and on_behalf_of != user:
            notes += f' on behalf of {on_behalf_of}'

        for event in decoded_events:
            if (
                (event.location_label == user or (event.location_label == on_behalf_of and user in self.eth_gateways)) and  # noqa: E501
                event.balance.amount == amount and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if event.event_type == HistoryEventType.SPEND:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = notes
                    event.counterparty = self.counterparty
                else:
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Receive {event.balance.amount} {resolved_asset.symbol} from {self.label}'  # noqa: E501
                    event.counterparty = self.counterparty
                # Set protocol for both events
                event.counterparty = self.counterparty

    def _decode_withdrawal(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2/v3 withdrawal event"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        to = hex_or_bytes_to_address(tx_log.topics[3])
        return_event, withdraw_event = None, None
        if not self.base.any_tracked([user, to]):
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data),
            asset=token,
        )
        notes = f'Withdraw {amount} {token.symbol} from {self.label}'
        if to != user:
            notes += f' to {to}'
        for event in decoded_events:
            if (
                event.event_type in {HistoryEventType.SPEND, HistoryEventType.RECEIVE} and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if (
                    event.location_label == to and
                    event.event_type == HistoryEventType.RECEIVE
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.location_label = user
                    event.notes = notes
                    withdraw_event = event
                else:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Return {event.balance.amount} {resolved_asset.symbol} to {self.label}'  # noqa: E501
                    return_event = event
                # Set protocol for both events
                event.counterparty = self.counterparty

        maybe_reshuffle_events(  # Make sure that the out event comes first
            ordered_events=[return_event, withdraw_event],
            events_list=decoded_events,
        )

    def _decode_borrow(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2/v3 borrow event"""
        on_behalf_of = hex_or_bytes_to_address(tx_log.topics[2])
        user = hex_or_bytes_to_address(tx_log.data[:32])
        if not self.base.any_tracked([user, on_behalf_of]):
            return

        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data[32:64]),
            asset=token,
        )
        rate_mode = hex_or_bytes_to_int(tx_log.data[64:96])
        # Aave uses ray math https://docs.aave.com/developers/v/1.0/developing-on-aave/important-considerations#ray-math  # noqa: E501
        # To get the rate we have to divide the value by 1e27. And then multiply by 100 to get the percentage.  # noqa: E501
        rate = hex_or_bytes_to_int(tx_log.data[96:128]) / FVal(RAY) * 100
        notes = f'Borrow {amount} {token.symbol} from {self.label} with {"stable" if rate_mode == 1 else "variable"} APY {rate.num:.2f}%'  # noqa: E501
        if on_behalf_of != user:
            notes += f' on behalf of {on_behalf_of}'
        for event in decoded_events:
            if (
                event.balance.amount == amount and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user and
                event.event_type == HistoryEventType.RECEIVE
            ):
                if event.asset == token:
                    event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                    event.notes = notes
                else:
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Receive {amount} {resolved_asset.symbol} from {self.label}'
                # Set protocol for both events
                event.counterparty = self.counterparty

    def _decode_repay(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2/v3 repay event"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        repayer = hex_or_bytes_to_address(tx_log.topics[3])
        if not self.base.any_tracked([user, repayer]):
            return

        for event in decoded_events:
            if (
                event.location_label == repayer and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if event.address == ZERO_ADDRESS:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Return {event.balance.amount} {resolved_asset.symbol} to {self.label}'  # noqa: E501
                else:
                    event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                    event.notes = f'Repay {event.balance.amount} {token.symbol} on {self.label}'

                # Set protocol and notes for both events
                event.counterparty = self.counterparty
                if repayer != user:
                    event.notes += f' for {user}'

    def _decode_lending_pool_events(self, context: DecoderContext) -> DecodingOutput:
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
            return DEFAULT_DECODING_OUTPUT

        if context.tx_log.topics[0] == LIQUIDATION_CALL:
            # the liquidation event has two tokens and needs to be checked per event
            self.decode_liquidation(context)
            return DEFAULT_DECODING_OUTPUT

        token = EvmToken(evm_address_to_identifier(
            address=hex_or_bytes_to_address(context.tx_log.topics[1]),
            token_type=EvmTokenKind.ERC20,
            chain_id=self.evm_inquirer.chain_id,
        ))

        if context.tx_log.topics[0] in (ENABLE_COLLATERAL, DISABLE_COLLATERAL):
            event = self._decode_collateral_events(token, context.transaction, context.tx_log)
            return DecodingOutput(event=event)
        if context.tx_log.topics[0] == self.deposit_signature:
            self._decode_deposit(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == WITHDRAW:
            self._decode_withdrawal(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == self.borrow_signature:
            self._decode_borrow(token, context.tx_log, context.decoded_events)
        else:  # Repay
            self._decode_repay(token, context.tx_log, context.decoded_events)

        return DEFAULT_DECODING_OUTPUT

    # DecoderInterface method
    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address(self.pool_address): (self._decode_lending_pool_events,),
        }
