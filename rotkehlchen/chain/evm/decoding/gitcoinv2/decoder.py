import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.gitcoinv2.constants import (
    ALLOCATED,
    DIRECT_ALLOCATED,
    FUNDS_DISTRIBUTED,
    GET_RECIPIENT_ABI,
    METADATA_UPDATED,
    NEW_PROJECT_APPLICATION_2ARGS,
    NEW_PROJECT_APPLICATION_3ARGS,
    PROFILE_CREATED,
    PROFILE_CREATED_ABI,
    PROFILE_METADATA_UPDATED,
    PROFILE_REGISTRY,
    PROJECT_CREATED,
    REGISTERED,
    REGISTERED_ABI,
    VOTED,
    VOTED_WITH_ORIGIN,
    VOTED_WITHOUT_APPLICATION_IDX,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import get_donation_event_params
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.misc import bytes_to_address, bytes_to_hexstr

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinV2CommonDecoder(EvmDecoderInterface, ABC):
    """This is the gitcoin v2 (allo protocol) common decoder

    Not the same as gitcoin v1, or v1.5 (they have changed contracts many times).

    Each round seems to have their own contract address and we need to be
    adding them as part of the constructor here to create the proper mappings.

    Also the payout strategy address should match the number of round implementations.
    Each payout address is found from the round implementation by querying the
    public variable payoutStrategy()

    voting_merkle_distributor_addresses are
    DonationVotingMerkleDistributionDirectTransferStrategy contracts

    TODO: Figure out if this can scale better as finding all contract addresses is error prone
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            project_registry: Optional['ChecksumEvmAddress'],
            voting_impl_addresses: list['ChecksumEvmAddress'],
            round_impl_addresses: list['ChecksumEvmAddress'],
            payout_strategy_addresses: list['ChecksumEvmAddress'],
            voting_merkle_distributor_addresses: list['ChecksumEvmAddress'] | None = None,
            retro_funding_strategy_addresses: list['ChecksumEvmAddress'] | None = None,
            direct_allocation_strategy_addresses: list['ChecksumEvmAddress'] | None = None,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.project_registry = project_registry
        self.round_impl_addresses = round_impl_addresses
        self.payout_strategy_addresses = payout_strategy_addresses
        assert len(self.payout_strategy_addresses) == len(self.round_impl_addresses), 'payout should match round number'  # noqa: E501
        self.voting_impl_addresses = voting_impl_addresses
        self.voting_merkle_distributor_addresses = voting_merkle_distributor_addresses
        self.retro_funding_strategy_addresses = retro_funding_strategy_addresses
        self.direct_allocation_strategy_addresses = direct_allocation_strategy_addresses
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.recipient_id_to_addr: LRUCacheWithRemove[ChecksumEvmAddress, ChecksumEvmAddress] = LRUCacheWithRemove(maxsize=512)  # noqa: E501

    def _get_recipient_address_from_id(
            self,
            recipient_id: 'ChecksumEvmAddress',
            contract_address: 'ChecksumEvmAddress',
    ) -> 'ChecksumEvmAddress | None':
        """Query the relevant contract to get the recipient id to address mapping.

        Also use a cache to save on contract calls"""
        if (recipient_address := self.recipient_id_to_addr.get(recipient_id)) is not None:
            return recipient_address

        result = self.node_inquirer.call_contract(
            contract_address=contract_address,
            abi=GET_RECIPIENT_ABI,
            method_name='getRecipient',
            arguments=[recipient_id],
        )
        if result is None or len(result) != 3:
            return None

        try:
            self.recipient_id_to_addr.add(
                key=recipient_id,
                value=(recipient_address := deserialize_evm_address(result[1])),
            )
        except DeserializationError:
            log.error(f'Got invalid evm address {result[1]} from getRecipient({recipient_id})')
            return None

        return recipient_address

    def _common_donator_logic(
            self,
            context: DecoderContext,
            sender_address: 'ChecksumEvmAddress',
            recipient_address: 'ChecksumEvmAddress',
            recipient_tracked: bool,
            asset: 'CryptoAsset',
            amount: FVal,
            payer_address: 'ChecksumEvmAddress',
    ) -> EvmDecodingOutput:
        """Common logic across Allocated and Voted events for the donator side

        sender_address: The original sender address
        recipient_address: The final address of the recipient
        payer_address: The in-between contract that splits the payment
        """
        new_type, expected_type, expected_address, expected_location_label, notes = get_donation_event_params(  # noqa: E501
            context=context,
            sender_address=sender_address,
            recipient_address=recipient_address,
            sender_tracked=True,  # _common_donator_logic is only called when sender is tracked
            recipient_tracked=recipient_tracked,
            asset=asset,
            amount=amount,
            payer_address=payer_address,
            counterparty=CPT_GITCOIN,
        )
        for event in context.decoded_events:
            if event.event_type == expected_type and event.event_subtype == HistoryEventSubType.NONE and event.asset == asset and event.location_label == expected_location_label and event.address == expected_address:  # noqa: E501
                # this is either the internal transfer to the contract that
                # should later break up into the transfers, or the internal
                # transfer to the grant if both are tracked. Replace it
                event.event_type = new_type
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = notes
                event.address = recipient_address
                event.amount = amount
                event.location_label = sender_address
                break
        else:  # no event found, so create a new one
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=new_type,
                event_subtype=HistoryEventSubType.DONATE,
                asset=asset,
                amount=amount,
                location_label=sender_address,
                notes=notes,
                counterparty=CPT_GITCOIN,
                address=recipient_address,
            )
            return EvmDecodingOutput(events=[event])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_retro_funding_strategy(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == REGISTERED:
            return self._decode_registered(context)
        elif context.tx_log.topics[0] == FUNDS_DISTRIBUTED:
            return self._decode_funds_distributed(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_voting_merkle_distributor(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == ALLOCATED:
            return self._decode_allocated(context)
        elif context.tx_log.topics[0] == REGISTERED:
            return self._decode_registered(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_registered(self, context: DecoderContext) -> EvmDecodingOutput:
        try:
            topic_data, decoded_data = decode_event_data_abi(context.tx_log, REGISTERED_ABI)
        except DeserializationError as e:
            log.error(
                f'Failed to deserialize gitcoin registered event at '
                f'{context.transaction.tx_hash.hex()} due to {e}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(sender := decoded_data[1]):
            return DEFAULT_EVM_DECODING_OUTPUT

        self.recipient_id_to_addr.add(  # store the recipient id to address mapping in the cache
            key=(recipient_id := topic_data[0]),
            value=sender,
        )  # and now create the informational registered event
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPLY,
            asset=A_ETH,
            amount=ZERO,
            location_label=sender,
            notes=f'Register for a gitcoin round with recipient id {recipient_id}',
            counterparty=CPT_GITCOIN,
            extra_data={'recipient_id': recipient_id},
        )
        return EvmDecodingOutput(events=[event])

    def _decode_allocated(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the allocated events

        The problem with those is that the recipient address is not known and needs a contract
        call to turn recipient id to address. This is bad since the allocated event
        comes before the token transfer. Which means we have no way to identify
        which of the allocated events concern the tracked addresses. And in some transactions
        there are hundreds such events.

        Example: https://arbiscan.io/tx/0x0388c141d93924d4737c4c52956469ecdb2c0a8dd9b3802317994c027d0a38af#eventlog
        """
        origin = bytes_to_address(context.tx_log.data[96:128])
        if (recipient_address := self._get_recipient_address_from_id(
            recipient_id=(recipient_id := bytes_to_address(context.tx_log.topics[1])),
            contract_address=context.tx_log.address,
        )) is None:
            log.error(f'Could not get recipient_address for recipient_id: {recipient_id}')
            return DEFAULT_EVM_DECODING_OUTPUT

        recipient_tracked = self.base.is_tracked(recipient_address)
        if not (origin_tracked := self.base.is_tracked(origin)) and not recipient_tracked:
            return DEFAULT_EVM_DECODING_OUTPUT

        token_address = bytes_to_address(context.tx_log.data[32:64])
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        if token_address == ETH_SPECIAL_ADDRESS:
            asset = self.node_inquirer.native_token
        else:
            asset = self.base.get_or_create_evm_token(token_address)

        amount = asset_normalized_value(amount_raw, asset)

        if origin_tracked:
            return self._common_donator_logic(
                context=context,
                sender_address=origin,
                recipient_address=recipient_address,
                recipient_tracked=recipient_tracked,
                asset=asset,
                amount=amount,
                payer_address=bytes_to_address(context.tx_log.data[64:96]),  # called sender in log
            )

        # else only recipient tracked
        new_type = HistoryEventType.RECEIVE
        expected_type = HistoryEventType.RECEIVE
        notes = f'Receive a gitcoin donation of {amount} {asset.symbol} from {origin}'
        for event in context.decoded_events:
            if event.event_type == expected_type and event.event_subtype == HistoryEventSubType.NONE and event.asset == asset and event.amount == amount and event.asset == asset:  # noqa: E501
                event.event_type = new_type
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = notes
                event.address = origin
                break

        else:  # no event found. Comes afterwards. Find it with ActionItem
            action_item = ActionItem(
                action='transform',
                from_event_type=expected_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                to_event_type=new_type,
                to_event_subtype=HistoryEventSubType.DONATE,
                to_notes=notes,
                to_address=origin,
                to_counterparty=CPT_GITCOIN,
            )
            return EvmDecodingOutput(action_items=[action_item])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vote_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == VOTED_WITH_ORIGIN:
            donator = bytes_to_address(context.tx_log.data[64:96])
            return self._decode_voted(
                context=context,
                donator=donator,
                receiver_start_idx=96,
                paying_contract_idx=1,
            )
        elif context.tx_log.topics[0] in (VOTED, VOTED_WITHOUT_APPLICATION_IDX):
            donator = bytes_to_address(context.tx_log.topics[1])
            return self._decode_voted(
                context=context,
                donator=donator,
                receiver_start_idx=64,
                paying_contract_idx=3,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_voted(
            self,
            context: DecoderContext,
            donator: 'ChecksumEvmAddress',
            receiver_start_idx: int,
            paying_contract_idx: int,
    ) -> EvmDecodingOutput:
        receiver = bytes_to_address(context.tx_log.data[receiver_start_idx:receiver_start_idx + 32])  # noqa: E501
        donator_tracked = self.base.is_tracked(donator)
        receiver_tracked = self.base.is_tracked(receiver)
        if donator_tracked is False and receiver_tracked is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        # there is a discrepancy here between the 2 different Voted events
        paying_contract_address = bytes_to_address(context.tx_log.topics[paying_contract_idx])
        token_address = bytes_to_address(context.tx_log.data[:32])
        if token_address == ZERO_ADDRESS:
            asset = self.node_inquirer.native_token
        else:
            asset = self.base.get_or_create_evm_token(token_address)
        amount_raw = int.from_bytes(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount_raw, asset)

        if donator_tracked:
            return self._common_donator_logic(
                context=context,
                sender_address=donator,
                recipient_address=receiver,
                recipient_tracked=receiver_tracked,
                asset=asset,
                amount=amount,
                payer_address=paying_contract_address,
            )

        # else only receiver tracked
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == asset and event.amount == amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Receive a gitcoin donation of {amount} {asset.symbol} from {donator}'  # noqa: E501
                event.address = donator
                break
        else:
            log.error(
                f'Could not find a corresponding event for donation to {receiver}'
                f' in {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}',  # noqa: E501
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_project_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == PROJECT_CREATED:
            project_id = int.from_bytes(context.tx_log.topics[1])
            owner = bytes_to_address(context.tx_log.topics[2])
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.CREATE,
                asset=A_ETH,
                amount=ZERO,
                location_label=context.transaction.from_address,
                notes=f'Create gitcoin project with id {project_id} and owner {owner}',
                counterparty=CPT_GITCOIN,
                address=context.tx_log.address,
            )
            return EvmDecodingOutput(events=[event])
        elif context.tx_log.topics[0] == METADATA_UPDATED:
            project_id = int.from_bytes(context.tx_log.topics[1])
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.UPDATE,
                asset=A_ETH,
                amount=ZERO,
                location_label=context.transaction.from_address,
                notes=f'Update gitcoin project with id {project_id}',
                counterparty=CPT_GITCOIN,
                address=context.tx_log.address,
            )
            return EvmDecodingOutput(events=[event])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_profile_created(self, context: DecoderContext) -> EvmDecodingOutput:
        try:
            topic_data, decoded_data = decode_event_data_abi(context.tx_log, PROFILE_CREATED_ABI)
            profile_id = bytes_to_hexstr(topic_data[0])
        except DeserializationError as e:
            log.error(
                f'Failed to deserialize gitcoin profile created event at '
                f'{context.transaction.tx_hash.hex()} due to {e}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        name = decoded_data[1]
        owner = decoded_data[3]
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Create gitcoin profile for {name} with id {profile_id} and owner {owner}',
            counterparty=CPT_GITCOIN,
            address=context.tx_log.address,
            extra_data={
                'name': name,
                'profile_id': profile_id,
                'owner': owner,
                'anchor': decoded_data[4],
            },
        )
        return EvmDecodingOutput(events=[event])

    def _decode_profile_metadata_updated(self, context: DecoderContext) -> EvmDecodingOutput:
        profile_id = bytes_to_hexstr(context.tx_log.topics[1])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Update gitcoin profile {profile_id} metadata',
            counterparty=CPT_GITCOIN,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_profile_registry(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == PROFILE_CREATED:
            return self._decode_profile_created(context)
        elif context.tx_log.topics[0] == PROFILE_METADATA_UPDATED:
            return self._decode_profile_metadata_updated(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_round_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (NEW_PROJECT_APPLICATION_2ARGS, NEW_PROJECT_APPLICATION_3ARGS):  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        application_id = context.tx_log.topics[1].hex()
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPLY,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Apply to gitcoin round with project application id 0x{application_id}',
            counterparty=CPT_GITCOIN,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_funds_distributed(self, context: DecoderContext) -> EvmDecodingOutput:
        grantee = bytes_to_address(context.tx_log.data[32:64])
        if self.base.is_tracked(grantee) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        token_address = bytes_to_address(context.tx_log.topics[1])
        token = self.base.get_or_create_evm_token(token_address)
        amount = asset_normalized_value(raw_amount, token)

        for event in reversed(context.decoded_events):  # transfer event should be right before
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == token and event.amount == amount and event.location_label == grantee:  # noqa: E501
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Receive matching payout of {amount} {token.symbol} for a gitcoin round'  # noqa: E501
                break
        else:
            log.error(
                f'Could not find a corresponding event for round payout to {grantee}'
                f' in {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}',  # noqa: E501
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_payout_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != FUNDS_DISTRIBUTED:
            return DEFAULT_EVM_DECODING_OUTPUT

        return self._decode_funds_distributed(context)

    def _decode_direct_allocated(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode direct allocation strategy donations from gitcoin v2."""
        if context.tx_log.topics[0] != DIRECT_ALLOCATED:
            return DEFAULT_EVM_DECODING_OUTPUT

        recipient = bytes_to_address(context.tx_log.data[:32])
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=(token := self.base.get_token_or_native(bytes_to_address(context.tx_log.data[64:96]))),  # noqa: E501
        )
        new_type, expected_type, _, expected_location_label, notes = get_donation_event_params(
            context=context,
            sender_address=(sender := bytes_to_address(context.tx_log.data[96:128])),
            recipient_address=recipient,
            sender_tracked=self.base.is_tracked(sender),
            recipient_tracked=self.base.is_tracked(recipient),
            asset=token,
            amount=amount,
            payer_address=sender,
            counterparty=CPT_GITCOIN,
        )

        # first, try to find existing event (for ERC20 tokens)
        for event in context.decoded_events:
            if (
                event.event_type == expected_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == token and
                event.amount == amount and
                event.location_label == expected_location_label
            ):
                event.notes = notes
                event.event_type = new_type
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                return DEFAULT_EVM_DECODING_OUTPUT

        # if no event found, create action item (for native tokens sent as internal transactions)
        action_item = ActionItem(
            action='transform',
            from_event_type=expected_type,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=token,
            amount=amount,
            to_event_type=new_type,
            to_event_subtype=HistoryEventSubType.DONATE,
            to_notes=notes,
            to_counterparty=CPT_GITCOIN,
        )
        return EvmDecodingOutput(action_items=[action_item])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        mappings: dict[ChecksumEvmAddress, tuple[Any, ...]] = {PROFILE_REGISTRY: (self._decode_profile_registry,)}  # noqa: E501
        mappings |= dict.fromkeys(self.voting_impl_addresses, (self._decode_vote_action,))
        mappings |= dict.fromkeys(self.round_impl_addresses, (self._decode_round_action,))
        mappings |= dict.fromkeys(self.payout_strategy_addresses, (self._decode_payout_action,))
        if self.voting_merkle_distributor_addresses:
            mappings |= dict.fromkeys(self.voting_merkle_distributor_addresses, (self._decode_voting_merkle_distributor,))  # noqa: E501
        if self.retro_funding_strategy_addresses:
            mappings |= dict.fromkeys(self.retro_funding_strategy_addresses, (self._decode_retro_funding_strategy,))  # noqa: E501
        if self.project_registry:
            mappings[self.project_registry] = (self._decode_project_action,)
        if self.direct_allocation_strategy_addresses:
            mappings |= dict.fromkeys(self.direct_allocation_strategy_addresses, (self._decode_direct_allocated,))  # noqa: E501

        return mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
