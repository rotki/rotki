import logging
from typing import TYPE_CHECKING, Any

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
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import (
    CPT_THEGRAPH,
    GRAPH_TOKEN_LOCK_WALLET_ABI,
    THEGRAPH_CPT_DETAILS,
    TOPIC_STAKE_DELEGATED,
    TOPIC_STAKE_DELEGATED_HORIZON,
    TOPIC_STAKE_DELEGATED_LOCKED,
    TOPIC_STAKE_DELEGATED_LOCKED_HORIZON,
    TOPIC_STAKE_DELEGATED_WITHDRAWN,
    TOPIC_STAKE_DELEGATED_WITHDRAWN_HORIZON,
    TOPIC_THAW_REQUEST_CREATED,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ThegraphCommonDecoder(EvmDecoderInterface, CustomizableDateMixin):
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
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.token = native_asset.resolve_to_evm_token()
        self.staking_contract = staking_contract

    def _decode_delegator_staking(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode delegator staking events for The Graph protocol.
        Handles events from both pre and post Horizon upgrade contracts.
        """
        if (topic := context.tx_log.topics[0]) == TOPIC_STAKE_DELEGATED:
            return self._decode_stake_delegated(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[2]),
                verifier=None,
            )
        elif topic == TOPIC_STAKE_DELEGATED_HORIZON:
            return self._decode_stake_delegated(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[3]),
                verifier=bytes_to_address(context.tx_log.topics[2]),
            )
        elif topic == TOPIC_STAKE_DELEGATED_LOCKED:
            return self._decode_stake_locked(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[2]),
                lock_duration_msg=f' Lock expires at epoch {int.from_bytes(context.tx_log.data[64:128])}',  # noqa: E501
            )
        elif topic == TOPIC_STAKE_DELEGATED_LOCKED_HORIZON:
            for log_entry in context.all_logs:
                if log_entry.topics[0] == TOPIC_THAW_REQUEST_CREATED:
                    lock_duration = f' Lock expires at {self.timestamp_to_date(Timestamp(int.from_bytes(log_entry.data[64:96])))}'  # noqa: E501
                    break
            else:
                log.error(f'Could not find ThawRequestCreated event for transaction {context.transaction}')  # noqa: E501
                lock_duration = ''

            return self._decode_stake_locked(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[3]),
                lock_duration_msg=lock_duration,
            )
        elif topic == TOPIC_STAKE_DELEGATED_WITHDRAWN:
            return self._decode_stake_withdrawn(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[2]),
            )
        elif topic == TOPIC_STAKE_DELEGATED_WITHDRAWN_HORIZON:
            return self._decode_stake_withdrawn(
                context=context,
                delegator=bytes_to_address(context.tx_log.topics[3]),
            )

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

    def _decode_stake_delegated(
            self,
            context: DecoderContext,
            delegator: ChecksumEvmAddress,
            verifier: ChecksumEvmAddress | None,
    ) -> EvmDecodingOutput:
        if not self.base.is_tracked(delegator):
            return DEFAULT_EVM_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        stake_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
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
                initial_amount = event.amount
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.amount = stake_amount
                event.notes = f'Delegate {stake_amount} GRT to indexer {indexer}'
                event.counterparty = CPT_THEGRAPH
                event.extra_data = {'indexer': indexer}
                if verifier is not None:
                    event.extra_data['verifier'] = verifier

                # also account for the GRT burnt due to delegation tax
                if (tokens_burnt := initial_amount - stake_amount) > 0:
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
                        ordered_events=[event, burn_event],
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

    def _decode_stake_locked(
            self,
            context: DecoderContext,
            delegator: ChecksumEvmAddress,
            lock_duration_msg: str,
    ) -> EvmDecodingOutput:
        if not self.base.is_tracked(delegator):
            return DEFAULT_EVM_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        tokens_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token=self.token,
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.token,
            amount=ZERO,
            location_label=delegator,
            notes=f'Undelegate {tokens_amount} GRT from indexer {indexer}.{lock_duration_msg}',
            counterparty=CPT_THEGRAPH,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_stake_withdrawn(
            self,
            context: DecoderContext,
            delegator: ChecksumEvmAddress,
    ) -> EvmDecodingOutput:
        if not self.base.is_tracked(delegator):
            return DEFAULT_EVM_DECODING_OUTPUT

        action_items, indexer, token_amount = [], bytes_to_address(context.tx_log.topics[1]), token_normalized_value(  # noqa: E501
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token=self.token,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == token_amount and
                    event.asset == self.token
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {token_amount} GRT from indexer {indexer}'
                event.counterparty = CPT_THEGRAPH
                break
        else:
            # create action item that will modify
            # the relevant Transfer event that will appear later
            action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.token,
                amount=token_amount,
                to_event_type=HistoryEventType.STAKING,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                to_notes=f'Withdraw {token_amount} GRT from indexer {bytes_to_address(context.tx_log.topics[1])}',  # noqa: E501
                to_counterparty=CPT_THEGRAPH,
            ))

        return EvmDecodingOutput(action_items=action_items)

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (THEGRAPH_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.staking_contract: (self._decode_delegator_staking,)}
