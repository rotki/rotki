import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.kiln.constants import CPT_KILN, KILN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.kiln.utils import has_beacon
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    EXIT_TOPIC,
    FILLED_TICKET_TOPIC,
    KILN_EXIT_QUEUE_BEACON,
    KILN_EXIT_QUEUES,
    KILN_INTEGRATION_ABI,
    KILN_INTEGRATION_CONTRACTS,
    KILN_VPOOL_BEACON,
    PAYMENT_TOPIC,
    PRINTED_TICKET_TOPIC,
    STAKE_TOPIC,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import ActionItem
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KilnDecoder(EvmDecoderInterface):
    """Decoder for Kiln pooled staking.

    Users stake ETH in a partner's integration contract and get its receipt token, which is
    minted by the integration contract itself. Exiting burns the receipt token and prints one
    exit ticket NFT per operator pool in the pool's exit queue. Once the exit queue is funded,
    anyone can claim a ticket and the exit queue pays the ETH to the ticket owner. A ticket that
    is only partially funded is re-issued with a new id for the unclaimed remainder.

    The known integration contracts and exit queues are decoded by address. A decoding rule
    catches the ones that are not hardcoded, verifying them on chain through their beacon.
    """

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        # results of the on chain checks for contracts that are not hardcoded
        self.integration_checks: dict[ChecksumEvmAddress, bool] = {}
        self.exit_queue_checks: dict[ChecksumEvmAddress, bool] = {}

    def _is_kiln_integration(self, address: ChecksumEvmAddress) -> bool:
        """Check whether an unknown contract is a Kiln integration contract by
        checking that it deposits into a Kiln vPool. The result is cached unless
        the check could not be completed due to a remote error."""
        if (is_kiln := self.integration_checks.get(address)) is not None:
            return is_kiln

        integration = EvmContract(address=address, abi=KILN_INTEGRATION_ABI, deployed_block=0)
        try:  # multicall_2 without required success tells a revert apart from a remote error
            (success, result), = self.node_inquirer.multicall_2(
                calls=[(address, integration.encode(method_name='pools'))],
                require_success=False,
            )
        except RemoteError as e:
            log.error('Failed to query pools of possible Kiln integration', address=address, error=str(e))  # noqa: E501
            return False

        try:
            pools = integration.decode(result=result, method_name='pools')[0] if success else []
        except DeserializationError:  # e.g. a fallback function returning nothing
            pools = []

        try:
            is_kiln = len(pools) != 0 and has_beacon(
                evm_inquirer=self.node_inquirer,
                address=pools[0],
                beacon=KILN_VPOOL_BEACON,
            )
        except RemoteError as e:
            log.error('Failed to query the beacon of possible Kiln pool', address=pools[0], error=str(e))  # noqa: E501
            return False

        self.integration_checks[address] = is_kiln
        return is_kiln

    def _is_kiln_exit_queue(self, address: ChecksumEvmAddress) -> bool:
        """Check whether an unknown contract is a Kiln exit queue by its beacon.
        The result is cached unless the check could not be completed."""
        if address in KILN_EXIT_QUEUES:
            return True

        if (is_kiln := self.exit_queue_checks.get(address)) is not None:
            return is_kiln

        try:
            is_kiln = has_beacon(
                evm_inquirer=self.node_inquirer,
                address=address,
                beacon=KILN_EXIT_QUEUE_BEACON,
            )
        except RemoteError as e:
            log.error('Failed to query the beacon of possible Kiln exit queue', address=address, error=str(e))  # noqa: E501
            return False

        self.exit_queue_checks[address] = is_kiln
        return is_kiln

    def _get_receipt_token(self, context: DecoderContext) -> EvmToken:
        """Get the receipt token of the integration contract emitting the current log,
        making sure it is tagged with the Kiln protocol so that it can be priced."""
        return self.base.get_or_create_evm_token(
            address=context.tx_log.address,
            protocol=CPT_KILN,
            encounter=TokenEncounterInfo(tx_ref=context.transaction.tx_hash),
        )

    @staticmethod
    def _is_ticket_of(event: EvmEvent, exit_queue: ChecksumEvmAddress) -> bool:
        """Whether the event moves an exit ticket NFT of the given exit queue"""
        return event.asset.identifier.startswith(f'eip155:1/erc721:{exit_queue}/')

    def _decode_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode staking ETH in an integration contract for its receipt token"""
        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        receipt_token = self._get_receipt_token(context)
        eth_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_ETH and
                    event.amount == eth_amount and
                    event.location_label == staker
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Stake {eth_amount} ETH in Kiln'
                event.counterparty = CPT_KILN
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == receipt_token and
                    event.address == ZERO_ADDRESS and
                    event.location_label == staker
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} {receipt_token.symbol} from staking in Kiln'
                event.counterparty = CPT_KILN
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the ETH spend and receipt token receive events for Kiln stake', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KILN)

    def _decode_exit_request(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode an exit request, burning the receipt token for exit tickets.

        The exit tickets are printed before the Exit log, so their logs and NFT transfer
        events are all available here.
        """
        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        tickets: list[tuple[ChecksumEvmAddress, int]] = []
        max_exitable_eth: dict[int, int] = {}
        for tx_log in context.all_logs:
            if (
                    tx_log.topics[0] == PRINTED_TICKET_TOPIC and
                    bytes_to_address(tx_log.topics[1]) == staker
            ):
                tickets.append((tx_log.address, ticket_id := int.from_bytes(tx_log.data[32:64])))
                max_exitable_eth[ticket_id] = int.from_bytes(tx_log.data[128:160])
                self.exit_queue_checks[tx_log.address] = True  # printed by a Kiln vPool

        receipt_token = self._get_receipt_token(context)
        exit_eth = from_wei(sum(max_exitable_eth.values()))
        out_event, ticket_events = None, []
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == receipt_token and
                    event.address == ZERO_ADDRESS and
                    event.location_label == staker
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Request exit of {event.amount} {receipt_token.symbol} worth {exit_eth} ETH from Kiln'  # noqa: E501
                event.counterparty = CPT_KILN
                event.extra_data = {'tickets': [
                    {'exit_queue': exit_queue, 'ticket_id': str(ticket_id)}
                    for exit_queue, ticket_id in tickets
                ]}
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    event.location_label == staker
            ):
                for exit_queue, ticket_id in tickets:
                    if self._is_ticket_of(event=event, exit_queue=exit_queue):
                        event.notes = f'Receive Kiln exit ticket {ticket_id} for up to {from_wei(max_exitable_eth[ticket_id])} ETH'  # noqa: E501
                        event.counterparty = CPT_KILN
                        ticket_events.append(event)
                        break

        if out_event is None:
            log.error('Failed to find the receipt token burn event for Kiln exit request', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, *ticket_events],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KILN)

    def _decode_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode claiming exit tickets, which pays the ETH to the ticket owner.

        Anyone can claim tickets on behalf of their owner, either directly in the exit
        queue or via the claim helper. All tickets of an owner claimed in the same call
        are paid with a single Payment log after all their FilledTicket logs.
        """
        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        exit_queue = context.tx_log.address
        eth_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        claim_event, ticket_events = None, []
        for event in context.decoded_events:
            if event.location_label != recipient or event.event_subtype != HistoryEventSubType.NONE:  # noqa: E501
                continue

            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == A_ETH and
                    event.amount == eth_amount and
                    event.address == exit_queue
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Claim {eth_amount} ETH from Kiln exit queue'
                event.counterparty = CPT_KILN
                claim_event = event
            elif (
                    event.address == ZERO_ADDRESS and
                    event.counterparty is None and
                    self._is_ticket_of(event=event, exit_queue=exit_queue)
            ):
                ticket_id = event.asset.identifier.rsplit('/', maxsplit=1)[-1]
                if event.event_type == HistoryEventType.SPEND:
                    event.notes = f'Return Kiln exit ticket {ticket_id}'
                else:  # tickets minted in a claim are the re-issued partially claimed ones
                    event.notes = f'Receive Kiln exit ticket {ticket_id} for the unclaimed remainder of a partially claimed ticket'  # noqa: E501

                event.counterparty = CPT_KILN
                ticket_events.append(event)

        if claim_event is None:
            log.error('Failed to find the ETH receive event for Kiln exit ticket claim', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[*ticket_events, claim_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KILN)

    def _decode_integration_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == STAKE_TOPIC:
            return self._decode_stake(context)
        if context.tx_log.topics[0] == EXIT_TOPIC:
            return self._decode_exit_request(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_exit_queue_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == PAYMENT_TOPIC:
            return self._decode_claim(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_unlisted_kiln_contract(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
            strict: bool = False,  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        """Decode the events of Kiln integration contracts and exit queues that are not
        hardcoded. The topic checks come first so that the on chain verification only
        happens for logs that look like Kiln ones and only once per contract."""
        if (topic := tx_log.topics[0]) in (STAKE_TOPIC, EXIT_TOPIC):
            if tx_log.address in KILN_INTEGRATION_CONTRACTS or not self._is_kiln_integration(tx_log.address):  # noqa: E501
                return DEFAULT_EVM_DECODING_OUTPUT

            decode_fn: Callable[[DecoderContext], EvmDecodingOutput] = self._decode_integration_event  # noqa: E501
        elif topic == PAYMENT_TOPIC:  # a common event so first require a Kiln FilledTicket log from the same contract  # noqa: E501
            if (
                    tx_log.address in KILN_EXIT_QUEUES or
                    not any(
                        x.topics[0] == FILLED_TICKET_TOPIC and x.address == tx_log.address
                        for x in all_logs
                    ) or
                    not self._is_kiln_exit_queue(tx_log.address)
            ):
                return DEFAULT_EVM_DECODING_OUTPUT

            decode_fn = self._decode_exit_queue_event
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        return decode_fn(DecoderContext(
            tx_log=tx_log,
            transaction=transaction,
            decoded_events=decoded_events,
            action_items=action_items,
            all_logs=all_logs,
        ))

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(
            KILN_INTEGRATION_CONTRACTS,
            (self._decode_integration_event,),
        ) | dict.fromkeys(
            KILN_EXIT_QUEUES,
            (self._decode_exit_queue_event,),
        )

    def decoding_rules(self) -> list[Callable]:
        return [self._decode_unlisted_kiln_contract]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (KILN_CPT_DETAILS,)
