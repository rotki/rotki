import logging
from typing import TYPE_CHECKING, Any, Final

from eth_typing.abi import ABI

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_THEGRAPH, THEGRAPH_CPT_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOPIC_STAKE_DELEGATED: Final = b'\xcd\x03f\xdc\xe5$}\x87O\xfc`\xa7b\xaaz\xbb\xb8,\x16\x95\xbb\xb1q`\x9c\x1b\x88a\xe2y\xebs'  # noqa: E501
TOPIC_STAKE_DELEGATED_LOCKED: Final = b'\x040\x18?\x84\xd9\xc4P#\x86\xd4\x99\xda\x80eC\xde\xe1\xd9\xde\x83\xc0\x8b\x01\xe3\x9am!\x16\xc4;%'  # noqa: E501
TOPIC_STAKE_DELEGATED_WITHDRAWN: Final = b'\x1b.w7\xe0C\xc5\xcf\x1bX|\xebM\xae\xb7\xae\x00\x14\x8b\x9b\xda\x8fy\xf1\t>\xea\xd0\x8f\x14\x19R'  # noqa: E501

GRAPH_TOKEN_LOCK_WALLET_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'beneficiary',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]


class ThegraphCommonDecoder(EvmDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
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

    def _decode_delegator_staking(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED:
            return self._decode_stake_delegated(context)
        elif context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED_LOCKED:
            return self._decode_stake_locked(context)
        elif context.tx_log.topics[0] == TOPIC_STAKE_DELEGATED_WITHDRAWN:
            return self._decode_stake_withdrawn(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def get_user_address(self, address: ChecksumEvmAddress, address_l2: ChecksumEvmAddress | None = None) -> ChecksumEvmAddress | None:  # noqa: E501
        """Get the user address (benficiary) from the vesting contract on L2 if it exists"""
        if self.node_inquirer.get_code(address) != '0x':
            try:
                raw_beneficiary_address = self.node_inquirer.call_contract(
                    contract_address=address,  # the vesting contract
                    abi=GRAPH_TOKEN_LOCK_WALLET_ABI,
                    method_name='beneficiary',
                )
                return deserialize_evm_address(raw_beneficiary_address)
            except RemoteError as e:
                log.error(f'During delegation transfer to arbitrum got error calling {address} beneficiary(): {e!s}')  # noqa: E501
                return None
        return address_l2 or address

    def _decode_stake_delegated(self, context: DecoderContext) -> EvmDecodingOutput:
        deposit_event, burn_event = None, None
        delegator = bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        stake_amount = int.from_bytes(context.tx_log.data[:32])
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
                initial_amount_norm = event.amount
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.amount = stake_amount_norm
                event.notes = f'Delegate {stake_amount_norm} GRT to indexer {indexer}'
                event.counterparty = CPT_THEGRAPH
                event.extra_data = {'indexer': indexer}
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
                        amount=tokens_burnt,
                        location_label=delegator,
                        notes=f'Burn {tokens_burnt} GRT as delegation tax',
                        counterparty=CPT_THEGRAPH,
                        address=context.tx_log.address,
                    )
                    maybe_reshuffle_events(
                        ordered_events=[deposit_event, burn_event],
                        events_list=context.decoded_events,
                    )
                    return EvmDecodingOutput(events=[burn_event])
                break

        # Reset the LAST_GRAPH_DELEGATIONS_CHECK_TS to Timestamp(0) to ensure the task runs more
        # frequently on decoding related events, rather than making users wait a whole day
        # to query event logs and get the balances detected.
        with self.node_inquirer.database.user_write() as write_cursor:
            self.node_inquirer.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
                value=Timestamp(0),
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stake_locked(self, context: DecoderContext) -> EvmDecodingOutput:
        delegator = bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        tokens_amount = int.from_bytes(context.tx_log.data[:32])
        lock_timeout_secs = int.from_bytes(context.tx_log.data[64:128])
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
            amount=ZERO,
            location_label=delegator,
            notes=(
                f'Undelegate {tokens_amount_norm} GRT from indexer {indexer}.'
                f' Lock expires in {lock_timeout_secs} seconds'
            ),
            counterparty=CPT_THEGRAPH,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_stake_withdrawn(self, context: DecoderContext) -> EvmDecodingOutput:
        delegator = bytes_to_address(context.tx_log.topics[2])
        if delegator is None or self.base.is_tracked(delegator) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        tokens_amount_norm = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
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
        return EvmDecodingOutput(action_items=[action_item])

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (THEGRAPH_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.staking_contract: (self._decode_delegator_staking,)}
