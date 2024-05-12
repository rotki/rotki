import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH, A_STETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_LIDO_ETH, LIDO_STETH_SUBMITTED, STETH_MAX_ROUND_ERROR_WEI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.steth_evm_address = A_STETH.resolve_to_evm_token().evm_address

    def _decode_lido_staking_in_steth(self, context: DecoderContext) -> DecodingOutput:
        """Decode the submit of eth to lido contract for obtaining steth in return"""
        sender_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        collateral_amount = token_normalized_value_decimals(
            token_amount=amount_raw,
            token_decimals=18,
        )

        # Searching for the exact paired stETH token reception for validating the decoding
        steth_minted_tokens = None
        # Here searching for the paired stETH mint operation, with a hacky way for the issue:
        # https://github.com/lidofinance/lido-dao/issues/442
        for tx_log in context.all_logs:
            if (
                tx_log.address == self.steth_evm_address and
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                hex_or_bytes_to_address(tx_log.topics[1]) == ZERO_ADDRESS and  # from
                hex_or_bytes_to_address(tx_log.topics[2]) == sender_address and  # to
                abs(amount_raw - hex_or_bytes_to_int(tx_log.data[:32])) < STETH_MAX_ROUND_ERROR_WEI
            ):
                steth_minted_tokens = token_normalized_value_decimals(
                    token_amount=hex_or_bytes_to_int(tx_log.data[:32]),
                    token_decimals=18,
                )
                break
        else:  # did not break/find anything
            log.error(
                f'At lido steth submit decoding of tx {context.transaction.tx_hash.hex()}'
                f'did not find the related stETH token generation',
            )
            return DEFAULT_DECODING_OUTPUT

        # Searching for the already decoded event,
        # containing the ETH transfer of the submit transaction
        paired_event = None
        for event in context.decoded_events:
            if (
                event.address == self.steth_evm_address and
                event.asset == A_ETH and
                event.balance.amount == collateral_amount and
                event.event_type == HistoryEventType.SPEND and
                event.location_label == sender_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Submit {collateral_amount} ETH to Lido for receiving stETH in exchange'  # noqa: E501
                event.counterparty = CPT_LIDO_ETH
                #  preparing next action to be processed when erc20 transfer will be decoded by rotki  # noqa: E501
                #  needed because submit levent is emitted prior of erc20 transfer, so it is not decoded yet  # noqa: E501
                # TODO: to be confirmed with ROTKI team if it is not possible to have the erc20 event available before this decoder is called  # noqa: E501
                paired_event = event
                action_from_event_type = HistoryEventType.RECEIVE
                action_to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                action_to_notes = f'Receive {steth_minted_tokens} stETH in exchange of the deposited ETH'  # noqa: E501
                break

        action_items = []  # also create an action item for the reception of the stETH tokens
        if paired_event is not None and action_from_event_type is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=action_from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_STETH,
                amount=steth_minted_tokens,
                to_event_subtype=action_to_event_subtype,
                to_notes=action_to_notes,
                to_counterparty=CPT_LIDO_ETH,
                paired_event_data=(paired_event, True),
                extra_data={'staked_eth': str(collateral_amount)},
            ))
        else:  # did not break/find anything
            log.error(
                f'At lido steth submit decoding of tx {context.transaction.tx_hash.hex()}'
                f'did not find the decoded event of the ETH transfer',
            )
            return DEFAULT_DECODING_OUTPUT

        return DecodingOutput(action_items=action_items, matched_counterparty=CPT_LIDO_ETH)

    def _decode_lido_eth_staking_contract(self, context: DecoderContext) -> DecodingOutput:
        """Decode interactions with stETH ans wstETH contracts"""

        if (
            context.tx_log.topics[0] == LIDO_STETH_SUBMITTED and
            self.base.any_tracked([
                hex_or_bytes_to_address(context.tx_log.topics[1]),  # sender address
            ])
        ):
            return self._decode_lido_staking_in_steth(
                context=context,
            )
        else:
            return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.steth_evm_address: (self._decode_lido_eth_staking_contract,),
        }

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return {
            self.steth_evm_address: CPT_LIDO_ETH,
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIDO_ETH, label='Lido eth', image='lido.svg'),)
