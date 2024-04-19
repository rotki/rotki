import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_THEGRAPH, THEGRAPH_CPT_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# example delegate() call: https://etherscan.io/tx/0x6ed3377db652151fb8e4794dd994a921a2d029ad317bd3f2a2916af239490fec
TOPIC_STAKE_DELEGATED: Final = b'\xcd\x03f\xdc\xe5$}\x87O\xfc`\xa7b\xaaz\xbb\xb8,\x16\x95\xbb\xb1q`\x9c\x1b\x88a\xe2y\xebs'  # noqa: E501
# example undelegate() call: https://etherscan.io/tx/0x5ca5244868d9c0d8c30a1cad0feaf137bd28acd9c3f669a09a3a199fd75ad25a
# example undelegate() call: https://arbiscan.io/tx/0xaa1d02b966d38fb7ade7768eae3dafc4bd4948090eadbb72f51fe6bab5f099cc
TOPIC_STAKE_DELEGATED_LOCKED: Final = b'\x040\x18?\x84\xd9\xc4P#\x86\xd4\x99\xda\x80eC\xde\xe1\xd9\xde\x83\xc0\x8b\x01\xe3\x9am!\x16\xc4;%'  # noqa: E501
# example withdrawDelegated() call: https://etherscan.io/tx/0x49307751de5ba4cf98fccbdd1ab8387fd60a7ce120800212c216bf0a6a04acfa
TOPIC_STAKE_DELEGATED_WITHDRAWN: Final = b'\x1b.w7\xe0C\xc5\xcf\x1bX|\xebM\xae\xb7\xae\x00\x14\x8b\x9b\xda\x8fy\xf1\t>\xea\xd0\x8f\x14\x19R'  # noqa: E501


class ThegraphCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_asset: Asset,
            staking_contract: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.token = native_asset.resolve_to_evm_token()
        self.staking_contract = staking_contract

    def _decode_delegator_staking(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED:
            return self._decode_stake_delegated(context)
        elif context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED_LOCKED:
            return self._decode_stake_locked(context)
        elif context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED_WITHDRAWN:
            return self._decode_stake_withdrawn(context)
        return DEFAULT_DECODING_OUTPUT

    def _decode_stake_delegated(self, context: DecoderContext) -> DecodingOutput:
        deposit_event, burn_event = None, None
        delegator = hex_or_bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_DECODING_OUTPUT
        indexer = hex_or_bytes_to_address(context.tx_log.topics[1])
        stake_amount = hex_or_bytes_to_int(context.tx_log.data[:32])
        stake_amount_norm = token_normalized_value(
            token_amount=stake_amount,
            token=self.token,
        )
        # identify and override the original stake Transfer event
        for event in context.decoded_events:
            if (
                event.location_label == delegator and
                event.address == self.staking_contract and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                initial_amount_norm = event.balance.amount
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.balance = Balance(amount=stake_amount_norm)
                event.notes = f'Delegate {stake_amount_norm} GRT to indexer {indexer}'
                event.counterparty = CPT_THEGRAPH
                event.extra_data = {'indexer': indexer}
                event.product = EvmProduct.STAKING
                deposit_event = event

                # also account for the GRT burnt due to delegation tax
                tokens_burnt = initial_amount_norm - stake_amount_norm
                if tokens_burnt > 0:
                    burn_event = self.base.make_event_from_transaction(
                        transaction=context.transaction,
                        tx_log=context.tx_log,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=self.token,
                        balance=Balance(amount=tokens_burnt),
                        location_label=delegator,
                        notes=f'Burn {tokens_burnt} GRT as delegation tax',
                        counterparty=CPT_THEGRAPH,
                        address=context.tx_log.address,
                    )
                    maybe_reshuffle_events(
                        ordered_events=[deposit_event, burn_event],
                        events_list=context.decoded_events,
                    )
                    return DecodingOutput(event=burn_event)
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_stake_locked(self, context: DecoderContext) -> DecodingOutput:
        delegator = hex_or_bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_DECODING_OUTPUT
        indexer = hex_or_bytes_to_address(context.tx_log.topics[1])
        tokens_amount = hex_or_bytes_to_int(context.tx_log.data[:32])
        lock_timeout_secs = hex_or_bytes_to_int(context.tx_log.data[64:128])
        tokens_amount_norm = token_normalized_value(
            token_amount=tokens_amount,
            token=self.token,
        )
        # create a new informational event about undelegation and the expiring lock on tokens
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.token,
            balance=Balance(),
            location_label=delegator,
            notes=(
                f'Undelegate {tokens_amount_norm} GRT from indexer {indexer}.'
                f' Lock expires in {lock_timeout_secs} seconds'
            ),
            counterparty=CPT_THEGRAPH,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def _decode_stake_withdrawn(self, context: DecoderContext) -> DecodingOutput:
        delegator = hex_or_bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_DECODING_OUTPUT
        indexer = hex_or_bytes_to_address(context.tx_log.topics[1])
        tokens_amount_norm = token_normalized_value(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[:32]),
            token=self.token,
        )
        # create action item that will modify the relevant Transfer event that will appear later
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=self.token,
            amount=tokens_amount_norm,
            to_event_type=HistoryEventType.STAKING,
            to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
            to_notes=f'Withdraw {tokens_amount_norm} GRT from indexer {indexer}',
            to_counterparty=CPT_THEGRAPH,
        )
        return DecodingOutput(action_items=[action_item])

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (THEGRAPH_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.staking_contract: (self._decode_delegator_staking,)}
