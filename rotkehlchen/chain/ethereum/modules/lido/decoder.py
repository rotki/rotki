import logging
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import CPT_LIDO, LIDO_STETH_SUBMITTED, STETH_MAX_ROUND_ERROR_WEI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.steth = A_STETH.resolve_to_evm_token()
        self.wsteth = A_WSTETH.resolve_to_evm_token()

    def _decode_lido_staking_in_steth(self, context: DecoderContext, sender: ChecksumEvmAddress) -> EvmDecodingOutput:  # noqa: E501
        """Decode the submit of eth to lido contract for obtaining steth in return"""
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        collateral_amount = token_normalized_value_decimals(
            token_amount=amount_raw,
            token_decimals=18,
        )

        # Searching for the already decoded event,
        # containing the ETH transfer of the submit transaction
        paired_event = None
        action_from_event_type = None
        for event in context.decoded_events:
            if (
                event.address == self.steth.evm_address and
                event.asset == A_ETH and
                event.amount == collateral_amount and
                event.event_type == HistoryEventType.SPEND and
                event.location_label == sender
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Submit {collateral_amount} ETH to Lido'
                event.counterparty = CPT_LIDO
                #  preparing next action to be processed when erc20 transfer will be decoded
                #  by rotki needed because submit event is emitted prior to the erc20 transfer
                paired_event = event
                action_from_event_type = HistoryEventType.RECEIVE
                action_to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                action_to_notes = 'Receive {amount} stETH in exchange for the deposited ETH'  # {amount} to be set by transform ActionItem  # noqa: E501
                break
        else:  # did not find anything
            log.error(
                f'At lido steth submit decoding of tx {context.transaction.tx_hash.hex()}'
                f' did not find the related ETH transfer',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        action_items = []  # also create an action item for the reception of the stETH tokens
        if paired_event is not None and action_from_event_type is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=action_from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_STETH,
                amount=collateral_amount,
                amount_error_tolerance=from_wei(STETH_MAX_ROUND_ERROR_WEI),  # passing the maximum rounding error for finding the related stETH transfer  # noqa: E501
                to_event_subtype=action_to_event_subtype,
                to_notes=action_to_notes,
                to_counterparty=CPT_LIDO,
                paired_events_data=((paired_event,), True),
                extra_data={'staked_eth': str(collateral_amount)},
            ))

        return EvmDecodingOutput(action_items=action_items, matched_counterparty=CPT_LIDO)

    def _decode_deposit_event(self, context: DecoderContext, depositor: ChecksumEvmAddress) -> EvmDecodingOutput:  # noqa: E501
        # A steth -> wsteth wrapping event has 4 logs associated with it.
        #
        # 1. A transfer of wsteth to the user
        # 2. An approval of steth to reduce the wsteth contract's allowance
        # 3. A transfer of steth tokens from the user to the wsteth contract
        # 4. A transfer of steth shares from the user to the wsteth contract
        #
        # We're currently decoding the ERC20 transfer associated with the first log
        # so we can find the other 3 logs by their offset.

        steth_transfer_log = get_log_with_offset(context, 2)
        steth_transfer = expect_erc20_transfer(steth_transfer_log, from_addr=depositor, to_addr=self.wsteth.evm_address)  # noqa: E501
        if steth_transfer is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        minted_wsteth_amount_raw = int.from_bytes(context.tx_log.data[:32])
        minted_wsteth_amount = token_normalized_value_decimals(
            token_amount=minted_wsteth_amount_raw,
            token_decimals=18,
        )
        in_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WSTETH,
            amount=minted_wsteth_amount,
            location_label=depositor,
            counterparty=CPT_LIDO,
            notes=f'Receive {minted_wsteth_amount} {self.wsteth.symbol}',
            address=self.wsteth.evm_address,
        )

        deposited_steth_amount = token_normalized_value_decimals(
            token_amount=steth_transfer[2],
            token_decimals=18,
        )
        out_action = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=deposited_steth_amount,
            to_event_type=HistoryEventType.DEPOSIT,
            to_event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            to_notes=f'Wrap {deposited_steth_amount} {self.steth.symbol} in {self.wsteth.symbol}',
            to_address=self.steth.evm_address,
            to_counterparty=CPT_LIDO,
            paired_events_data=((in_event,), False),
        )

        return EvmDecodingOutput(events=[in_event], action_items=[out_action])

    def _decode_withdraw_event(self, context: DecoderContext, withdrawer: ChecksumEvmAddress) -> EvmDecodingOutput:  # noqa: E501
        # A wsteth -> steth unwrapping event has 3 logs associated with it.
        #
        # 1. A burn of wsteth from the user
        # 2. A transfer of steth tokens from the wsteth contract to the user
        # 3. A transfer of steth shares from the wsteth contract to the user
        #
        # We're currently decoding the ERC20 transfer associated with the first log
        # so we can access the other 2 logs by their offset.

        steth_transfer_log = get_log_with_offset(context, 1)
        steth_transfer = expect_erc20_transfer(steth_transfer_log, from_addr=self.wsteth.evm_address, to_addr=withdrawer)  # noqa: E501
        if steth_transfer is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        burned_wsteth_amount_raw = int.from_bytes(context.tx_log.data[:32])
        burned_wsteth_amount = token_normalized_value_decimals(
            token_amount=burned_wsteth_amount_raw,
            token_decimals=18,
        )
        out_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WSTETH,
            amount=burned_wsteth_amount,
            location_label=withdrawer,
            counterparty=CPT_LIDO,
            notes=f'Unwrap {burned_wsteth_amount} {self.wsteth.symbol}',
            address=context.transaction.to_address,
        )

        withdrawn_steth_amount = token_normalized_value_decimals(
            token_amount=steth_transfer[2],
            token_decimals=18,
        )
        in_action = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=withdrawn_steth_amount,
            to_notes=f'Receive {withdrawn_steth_amount} {self.steth.symbol}',
            to_counterparty=CPT_LIDO,
            to_address=self.steth.evm_address,
            paired_events_data=((out_event,), True),
        )

        return EvmDecodingOutput(events=[out_event], action_items=[in_action])

    def _decode_lido_eth_staking_contract(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode interactions with stETH contract"""
        if (
            context.tx_log.topics[0] == LIDO_STETH_SUBMITTED and
            self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[1]))
        ):
            return self._decode_lido_staking_in_steth(context=context, sender=sender)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_lido_steth_wrapping(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode mints and burns of wstETH"""
        if (erc20_transfer := parse_erc20_transfer(context.tx_log)) is not None:
            from_address, to_address, _ = erc20_transfer
            if self.base.is_tracked(to_address) and from_address == ZERO_ADDRESS:
                return self._decode_deposit_event(context, to_address)
            elif self.base.is_tracked(from_address) and to_address == ZERO_ADDRESS:
                return self._decode_withdraw_event(context, from_address)
        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.steth.evm_address: (self._decode_lido_eth_staking_contract,),
            self.wsteth.evm_address: (self._decode_lido_steth_wrapping,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIDO, label='Lido eth', image='lido.svg'),)


def get_log_with_offset(context: 'DecoderContext', offset: int) -> 'EvmTxReceiptLog':
    """Get a log with an offset relative to the current log in the context"""
    tx_start_log_index = context.all_logs[0].log_index
    steth_transfer_log_index = (context.tx_log.log_index - tx_start_log_index) + offset
    return context.all_logs[steth_transfer_log_index]


def parse_erc20_transfer(transfer_log: 'EvmTxReceiptLog') -> tuple[ChecksumEvmAddress, ChecksumEvmAddress, int] | None:  # noqa: E501
    """Parse an ERC20 transfer from its log

    Returns a tuple of `from`, `to` and `amount` if `transfer_log` is an ERC20 transfer
    or `None` otherwise
    """
    if transfer_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
        return None

    from_address = bytes_to_address(transfer_log.topics[1])
    to_address = bytes_to_address(transfer_log.topics[2])
    actual_amount = int.from_bytes(transfer_log.data[:32])

    return from_address, to_address, actual_amount


def expect_erc20_transfer(
        transfer_log: 'EvmTxReceiptLog',
        from_addr: Optional['ChecksumEvmAddress'] = None,
        to_addr: Optional['ChecksumEvmAddress'] = None,
        amount: int | None = None,
    ) -> tuple[ChecksumEvmAddress, ChecksumEvmAddress, int] | None:
    """Expect an ERC20 transfer log and optionally match `from`, `to` and `amount`

    Returns a tuple of `from`, `to` and `amount` if it matches or `None` otherwise
    """
    if (erc20_transfer := parse_erc20_transfer(transfer_log)) is None:
        return None

    if (
        (from_addr is not None and from_addr != erc20_transfer[0]) or
        (to_addr is not None and to_addr != erc20_transfer[1]) or
        (amount is not None and amount != erc20_transfer[2])
        ):
        return None

    return erc20_transfer
