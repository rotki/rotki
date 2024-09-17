import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.common import Commonv2v3Decoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_AAVE_V3, MINT
from .constants import BORROW, BURN, DEPOSIT, REPAY, REWARDS_CLAIMED

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Aavev3CommonDecoder(Commonv2v3Decoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_address: 'ChecksumEvmAddress',
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            treasury: 'ChecksumEvmAddress',
            incentives: 'ChecksumEvmAddress',
    ):
        Commonv2v3Decoder.__init__(
            self,
            counterparty=CPT_AAVE_V3,
            label='AAVE v3',
            pool_address=pool_address,
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

    def decode_liquidation(self, context: 'DecoderContext') -> None:
        """
        Decode AAVE v3 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if not self.base.is_tracked(hex_or_bytes_to_address(context.tx_log.topics[3])):  # liquidator  # noqa: E501
            return

        amounts = [  # payback amount and liquidation amount
            asset_normalized_value(
                amount=hex_or_bytes_to_int(log.data[:32]),
                asset=EvmToken(evm_address_to_identifier(
                    address=log.address,
                    token_type=EvmTokenKind.ERC20,
                    chain_id=self.evm_inquirer.chain_id,
                )),
            ) for log in context.all_logs
            if log.topics[0] == BURN and log.topics[1] == context.tx_log.topics[3]
        ]

        if len(amounts) != 2:
            log.warning(
                f'Found invalid number of payback and liquidation amounts '
                f'in AAVE v3 liquidation: {context.transaction.tx_hash.hex()}',
            )
            return

        for event in context.decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if amounts[1] == event.balance.amount and event.address == ZERO_ADDRESS:
                # we are transfering the debt token
                event.event_type = HistoryEventType.LOSS
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An {self.label} position got liquidated for {event.balance.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = CPT_AAVE_V3
                event.address = context.tx_log.address
            elif amounts[0] == event.balance.amount and event.address == ZERO_ADDRESS:
                # we are transfering the aTOKEN
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.balance.amount} {asset.symbol} for an {self.label} position'  # noqa: E501
                event.counterparty = CPT_AAVE_V3
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differentiate paybacks happening in liquidations.  # noqa: E501
            elif event.address == self.treasury:  # fee
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Spend {event.balance.amount} {asset.symbol} as an {self.label} fee'
                event.counterparty = CPT_AAVE_V3

    def _decode_incentives(self, context: 'DecoderContext') -> DecodingOutput:
        if context.tx_log.topics[0] != REWARDS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        return self._decode_incentives_common(
            context=context,
            to_idx=3,
            claimer_raw=context.tx_log.data[0:32],
            reward_token_address_32bytes=context.tx_log.topics[2],
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
        supply_event, withdraw_event, return_event, receive_event = None, None, None, None
        for event in decoded_events:  # identify the events decoded till now
            if (
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
            ):
                supply_event = event
            elif (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.REMOVE_ASSET
            ):
                withdraw_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED
            ):
                receive_event = event
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED
            ):
                return_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                self._token_is_aave_contract(event.asset)
            ):  # we received aTokens when transfering, so it's an interest event
                event.event_subtype = HistoryEventSubType.INTEREST
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol_or_name()} as interest earned from {self.label}'  # noqa: E501
                event.counterparty = CPT_AAVE_V3

        # categorize the events, based on token_event and wrapped_event
        if supply_event is not None and receive_event is not None:
            token_event = supply_event
            wrapped_event = receive_event
        elif withdraw_event is not None:
            token_event = withdraw_event
            if return_event is not None:
                wrapped_event = return_event
            elif receive_event is not None:
                wrapped_event = receive_event
        else:  # if not identified, return the decoded events
            return decoded_events

        token = token_event.asset.resolve_to_evm_token()
        a_token = wrapped_event.asset.resolve_to_evm_token()
        earned_event, corrected_amount = None, None
        for _log in all_logs:
            if (  # find the mint or burn event of aToken
                _log.topics[0] in (MINT, BURN) and (
                    # topics[2] is on_behalf_of, should be equal to the value we got above
                    hex_or_bytes_to_address(_log.topics[2]) == token_event.location_label
                ) and (
                    balance_increase := asset_normalized_value(
                        amount=hex_or_bytes_to_int(_log.data[32:64]),
                        asset=token,
                    )
                ) > 0
            ):  # parse the mint amount and balance_increase
                earned_token_address = a_token.evm_address
                if _log.topics[0] == BURN:
                    # when we get some interest less than the total token to be returned, the net
                    # burned token is slightly less. So save its corrected amount and assign it later  # noqa: E501
                    corrected_amount = asset_normalized_value(
                        amount=hex_or_bytes_to_int(_log.data[:32]),
                        asset=token,
                    )
                    earned_token_address = token.evm_address
                decoded_events.append(earned_event := self.base.make_event_from_transaction(
                    transaction=transaction,
                    tx_log=_log,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.INTEREST,
                    asset=(earned_token := get_or_create_evm_token(
                        userdb=self.evm_inquirer.database,
                        evm_address=earned_token_address,
                        chain_id=self.evm_inquirer.chain_id,
                        evm_inquirer=self.evm_inquirer,
                    )),
                    balance=Balance(amount=balance_increase),
                    location_label=token_event.location_label,
                    notes=f'Receive {balance_increase} {earned_token.symbol} as interest earned from {self.label}',  # noqa: E501
                    counterparty=self.counterparty,
                ))

        if supply_event is not None and receive_event is not None:  # re-assign the receive amount
            receive_event.balance.amount = supply_event.balance.amount
            receive_event.notes = f'Receive {supply_event.balance.amount} {a_token.symbol} from {self.label}'  # noqa: E501

        if withdraw_event is not None:
            if return_event is not None:  # re-assign the withdraw amount
                withdraw_event.balance.amount = return_event.balance.amount
                withdraw_event.notes = f'Withdraw {return_event.balance.amount} {token.symbol} from {self.label}'  # noqa: E501
            elif receive_event is not None:
                # receiving aToken, while withdrawing means interest > returned amount
                return_event = receive_event  # save it as return event
                receive_event = None  # remove the receive event
                # re-assign the values to the return event
                return_event.balance.amount = withdraw_event.balance.amount
                return_event.event_type = HistoryEventType.SPEND
                return_event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                return_event.notes = f'Return {withdraw_event.balance.amount} {a_token.symbol} to {self.label}'  # noqa: E501

        if earned_event is not None and corrected_amount is not None and return_event is not None:
            return_event.balance.amount = corrected_amount

        maybe_reshuffle_events(
            ordered_events=[supply_event, return_event, withdraw_event, receive_event, earned_event],  # noqa: E501
            events_list=decoded_events,
        )
        return decoded_events

    # DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.incentives: (self._decode_incentives,),
        }

    @staticmethod  # DecoderInterface method
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AAVE_V3,
            label=CPT_AAVE_V3.capitalize().replace('-v', ' V'),
            image='aave.svg',
        ),)

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {token.evm_address: CPT_AAVE_V3 for token in GlobalDBHandler.get_evm_tokens(
            chain_id=self.evm_inquirer.chain_id,
            protocol=CPT_AAVE_V3,
        )} | {self.pool_address: CPT_AAVE_V3}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_AAVE_V3: [(0, self._decode_interest)]}
