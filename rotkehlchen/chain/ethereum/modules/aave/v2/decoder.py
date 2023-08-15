from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ChecksumEvmAddress,
    DecoderEventMappingType,
    EvmTokenKind,
    EvmTransaction,
)
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

from ..constants import AAVE_LABEL, CPT_AAVE_V2

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent

ENABLE_COLLATERAL = b'\x00\x05\x8aV\xea\x94e<\xdfO\x15-"z\xce"\xd4\xc0\n\xd9\x9e*C\xf5\x8c\xb7\xd9\xe3\xfe\xb2\x95\xf2'  # noqa: E501
DISABLE_COLLATERAL = b'D\xc5\x8d\x816[f\xddK\x1a\x7f6\xc2Z\xa9{\x8cq\xc3a\xeeI7\xad\xc1\xa0\x00\x00"}\xb5\xdd'  # noqa: E501
DEPOSIT = b'\xdehW!\x95D\xbb[wF\xf4\x8e\xd3\x0b\xe68o\xef\xc6\x1b/\x86L\xac\xf5Y\x89;\xf5\x0f\xd9Q'
WITHDRAW = b'1\x15\xd1D\x9a{s,\x98l\xba\x18$N\x89zE\x0fa\xe1\xbb\x8dX\x9c\xd2\xe6\x9el\x89$\xf9\xf7'  # noqa: E501
BORROW = b'\xc6\xa8\x980\x9e\x82>\xe5\x0b\xacd\xe4\\\xa8\xad\xbaf\x90\xe9\x9exA\xc4]uN*8\xe9\x01\x9d\x9b'  # noqa: E501
REPAY = b'L\xdd\xe6\xe0\x9b\xb7U\xc9\xa5X\x9e\xba\xecd\x0b\xbf\xed\xff\x13b\xd4\xb2U\xeb\xf83\x97\x82\xb9\x94/\xaa'  # noqa: E501
LIQUIDATION_CALL = b'\xe4\x13\xa3!\xe8h\x1d\x83\x1fM\xbc\xcb\xcay\r)R\xb5o\x97y\x08\xe4[\xe3s5S>\x00R\x86'  # noqa: E501
ETH_GATEWAYS = (
    string_to_evm_address('0xEFFC18fC3b7eb8E676dac549E0c693ad50D1Ce31'),
    string_to_evm_address('0xcc9a0B7c43DC2a5F023Bb9b738E45B0Ef6B06E04'),
)


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
        on_behalf_of = hex_or_bytes_to_address(tx_log.topics[2]) if hex_or_bytes_to_str(tx_log.topics[2]) != '' else None  # noqa: E501
        # in the case of needing to wrap ETH to WETH aave uses the ETH_GATEWAY contract and the
        # user is the contract address
        if (
            (user not in ETH_GATEWAYS and self.base.is_tracked(user) is False) and
            (on_behalf_of is None or self.base.is_tracked(on_behalf_of) is False)
        ):
            return
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(tx_log.data[32:64]),
            asset=token,
        )
        notes = f'Deposit {amount} {token.symbol} into AAVE v2'
        if on_behalf_of is not None and user not in ETH_GATEWAYS and on_behalf_of != user:
            notes += f' on behalf of {on_behalf_of}'

        for event in decoded_events:
            if (
                (event.location_label == user or (event.location_label == on_behalf_of and user in ETH_GATEWAYS)) and  # noqa: E501
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
        if not self.base.any_tracked([user, to]):
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

    def _decode_liquidation(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """
        Decode AAVE v2 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if self.base.is_tracked(hex_or_bytes_to_address(tx_log.topics[3])) is False:
            return

        for event in decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if asset_normalized_value(
                amount=hex_or_bytes_to_int(tx_log.data[32:64]),  # liquidated amount
                asset=asset,
            ) == event.balance.amount and asset.protocol == CPT_AAVE_V2:
                # we are transfering the aTOKEN
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An aave-v2 position got liquidated for {event.balance.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = CPT_AAVE_V2
                event.address = tx_log.address
            elif asset_normalized_value(
                amount=hex_or_bytes_to_int(tx_log.data[:32]),  # debt amount
                asset=asset,
            ) == event.balance.amount:
                # we are transfering the debt token
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.balance.amount} {asset.symbol} for an aave-v2 position'  # noqa: E501
                event.counterparty = CPT_AAVE_V2
                event.address = tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differenciate paybacks happening in liquidations.  # noqa: E501

    def _decode_repay(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Decode aave v2 repay event"""
        user = hex_or_bytes_to_address(tx_log.topics[2])
        repayer = hex_or_bytes_to_address(tx_log.topics[3])
        if not self.base.any_tracked([user, repayer]):
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
        if context.tx_log.topics[0] not in (LIQUIDATION_CALL, ENABLE_COLLATERAL, DISABLE_COLLATERAL, DEPOSIT, WITHDRAW, BORROW, REPAY):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if context.tx_log.topics[0] == LIQUIDATION_CALL:
            # the liquidation event has two tokens and needs to be checked per event
            self._decode_liquidation(context.tx_log, context.decoded_events)
            return DEFAULT_DECODING_OUTPUT

        token = EvmToken(evm_address_to_identifier(
            address=hex_or_bytes_to_address(context.tx_log.topics[1]),
            token_type=EvmTokenKind.ERC20,
            chain_id=self.evm_inquirer.chain_id,
        ))

        if context.tx_log.topics[0] in (ENABLE_COLLATERAL, DISABLE_COLLATERAL):
            event = self._decode_collateral_events(token, context.transaction, context.tx_log)
            return DecodingOutput(event=event)
        if context.tx_log.topics[0] == DEPOSIT:
            self._decode_deposit(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == WITHDRAW:
            self._decode_withdrawal(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == BORROW:
            self._decode_borrow(token, context.tx_log, context.decoded_events)
        else:  # Repay
            self._decode_repay(token, context.tx_log, context.decoded_events)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_AAVE_V2: {
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.GENERATE_DEBT: EventCategory.CLAIM_REWARD,
                HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
                HistoryEventSubType.RETURN_WRAPPED: EventCategory.RECEIVE,
            },
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
            },
            HistoryEventType.SPEND: {
                HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
                HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATE,
                HistoryEventSubType.PAYBACK_DEBT: EventCategory.REPAY,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
            },
            HistoryEventType.INFORMATIONAL: {
                HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'): (self._decode_lending_pool_events,),  # AAVE_V2_LENDING_POOL  # noqa: E501
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_AAVE_V2, label=AAVE_LABEL, image='aave.svg')]
