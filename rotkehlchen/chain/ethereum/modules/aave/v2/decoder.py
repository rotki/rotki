from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

from ..constants import CPT_AAVE_V2

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent

ENABLE_COLLATERAL = b'\x00\x05\x8aV\xea\x94e<\xdfO\x15-"z\xce"\xd4\xc0\n\xd9\x9e*C\xf5\x8c\xb7\xd9\xe3\xfe\xb2\x95\xf2'  # noqa: E501
DISABLE_COLLATERAL = b'D\xc5\x8d\x816[f\xddK\x1a\x7f6\xc2Z\xa9{\x8cq\xc3a\xeeI7\xad\xc1\xa0\x00\x00"}\xb5\xdd'  # noqa: E501
DEPOSIT = b'\xdehW!\x95D\xbb[wF\xf4\x8e\xd3\x0b\xe68o\xef\xc6\x1b/\x86L\xac\xf5Y\x89;\xf5\x0f\xd9Q'
WITHDRAW = b'1\x15\xd1D\x9a{s,\x98l\xba\x18$N\x89zE\x0fa\xe1\xbb\x8dX\x9c\xd2\xe6\x9el\x89$\xf9\xf7'  # noqa: E501
BORROW = b'\xc6\xa8\x980\x9e\x82>\xe5\x0b\xacd\xe4\\\xa8\xad\xbaf\x90\xe9\x9exA\xc4]uN*8\xe9\x01\x9d\x9b'  # noqa: E501
REPAY = b'L\xdd\xe6\xe0\x9b\xb7U\xc9\xa5X\x9e\xba\xecd\x0b\xbf\xed\xff\x13b\xd4\xb2U\xeb\xf83\x97\x82\xb9\x94/\xaa'  # noqa: E501
DEFAULT_DECODING_OUTPUT = DecodingOutput(counterparty=CPT_AAVE_V2)


class Aavev2Decoder(DecoderInterface):

    def _decode_collateral_events(
            self,
            token: 'EvmToken',
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
    ) -> Optional['EvmEvent']:
        user = hex_or_bytes_to_address(tx_log.topics[2])
        if self.base.is_tracked(user) is False:
            return None
        return self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=token,
            balance=Balance(),
            location_label=user,
            notes=f'{"Enable" if tx_log.topics[0] == ENABLE_COLLATERAL else "Disable"} {token.symbol} as collateral on AAVE v2',  # noqa: E501
            counterparty=CPT_AAVE_V2,
            address=transaction.to_address,
        )

    def _decode_deposit(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2 deposit event"""
        user = hex_or_bytes_to_address(tx_log.data[:32])
        on_behalf_of = hex_or_bytes_to_address(tx_log.data[64:96]) if hex_or_bytes_to_str(tx_log.data[64:96]) != '' else None  # noqa: E501
        if (
            self.base.is_tracked(user) is False and
            (on_behalf_of is None or self.base.is_tracked(on_behalf_of) is False)
        ):
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data[32:64]),
            asset=token,
        )
        notes = f'Deposit {amount} {token.symbol} into AAVE v2'
        if on_behalf_of is not None:
            notes += f' on behalf of {on_behalf_of}'
        for event in decoded_events:
            if (
                event.location_label == user and
                event.balance.amount == amount and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if event.event_type == HistoryEventType.SPEND:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = notes
                    event.counterparty = CPT_AAVE_V2
                else:
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Receive {event.balance.amount} {resolved_asset.symbol} from AAVE v2'  # noqa: E501
                    event.counterparty = CPT_AAVE_V2
                # Set protocol for both events
                event.counterparty = CPT_AAVE_V2

    def _decode_withdrawal(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2 withdrawal event"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        to = hex_or_bytes_to_address(tx_log.topics[3])
        if self.base.is_tracked(user) is False and self.base.is_tracked(to) is False:
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data),
            asset=token,
        )
        notes = f'Withdraw {amount} {token.symbol} from AAVE v2'
        if to != user:
            notes += f' to {to}'
        for event in decoded_events:
            if (
                event.balance.amount == amount and
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
                else:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Return {amount} {resolved_asset.symbol} to AAVE v2'  # noqa: E501
                # Set protocol for both events
                event.counterparty = CPT_AAVE_V2

    def _decode_borrow(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2 borrow event"""
        on_behalf_of = hex_or_bytes_to_address(tx_log.topics[2])
        user = hex_or_bytes_to_address(tx_log.data[:32])
        if self.base.is_tracked(user) is False and self.base.is_tracked(on_behalf_of) is False:  # noqa: E501
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data[32:64]),
            asset=token,
        )
        rate_mode = hex_or_bytes_to_int(tx_log.data[64:96])
        # Aave uses ray math https://docs.aave.com/developers/v/1.0/developing-on-aave/important-considerations#ray-math  # noqa: E501
        # To get the rate we have to divide the value by 1e27. And then multiply by 100 to get the percentage.  # noqa: E501
        rate = hex_or_bytes_to_int(tx_log.data[96:128]) / FVal(RAY) * 100
        notes = f'Borrow {amount} {token.symbol} from AAVE v2 with {"stable" if rate_mode == 1 else "variable"} APY {rate.num:.2f}%'  # noqa: E501
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
                    event.notes = f'Receive {amount} {resolved_asset.symbol} from AAVE v2'  # noqa: E501
                # Set protocol for both events
                event.counterparty = CPT_AAVE_V2

    def _decode_repay(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2 repay event"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        repayer = hex_or_bytes_to_address(tx_log.topics[3])
        if self.base.is_tracked(user) is False and self.base.is_tracked(repayer) is False:  # noqa: E501
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data),
            asset=token,
        )
        notes = f'Repay {amount} {token.symbol} on AAVE v2'
        if repayer != user:
            notes += f' for {user}'

        for event in decoded_events:
            if (
                event.location_label == repayer and
                event.balance.amount == amount and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if event.address == ZERO_ADDRESS:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f'Return {amount} {resolved_asset.symbol} to AAVE v2'
                    if repayer != user:
                        event.notes += f' for {user}'
                else:
                    event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                    event.notes = notes
                # Set protocol for both events
                event.counterparty = CPT_AAVE_V2

    def _decode_lending_pool_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes AAVE V2 Lending Pool events"""
        tx_log = context.tx_log
        decoded_events = context.decoded_events
        event_signature = tx_log.topics[0]
        if event_signature not in (ENABLE_COLLATERAL, DISABLE_COLLATERAL, DEPOSIT, WITHDRAW, BORROW, REPAY):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        token = EvmToken(evm_address_to_identifier(
            address=hex_or_bytes_to_address(tx_log.topics[1]),
            token_type=EvmTokenKind.ERC20,
            chain_id=self.evm_inquirer.chain_id,
        ))

        if tx_log.topics[0] in (ENABLE_COLLATERAL, DISABLE_COLLATERAL):
            event = self._decode_collateral_events(token, context.transaction, tx_log)
            return DecodingOutput(event=event)
        if tx_log.topics[0] == DEPOSIT:
            self._decode_deposit(token, tx_log, decoded_events)
        elif tx_log.topics[0] == WITHDRAW:
            self._decode_withdrawal(token, tx_log, decoded_events)
        elif tx_log.topics[0] == BORROW:
            self._decode_borrow(token, tx_log, decoded_events)
        else:  # Repay
            self._decode_repay(token, tx_log, decoded_events)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.evm_inquirer.contracts.contract('AAVE_V2_LENDING_POOL').address: (self._decode_lending_pool_events,),  # noqa: E501
        }

    def counterparties(self) -> list[str]:
        return [CPT_AAVE_V2]
