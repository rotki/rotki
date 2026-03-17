import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi

from rotkehlchen.assets.utils import TokenEncounterInfo, token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, REWARDS_CLAIMED_TOPIC, WITHDRAW_TOPIC_V3
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import (
    CPT_STAKEDAO_V2,
    LAPOSTE_ADDRESS,
    LAPOSTE_BUNDLER_ADDRESS,
    LAPOSTE_MESSAGE_RECEIVED_TOPIC,
    LAPOSTE_MESSAGE_SENT_TOPIC,
    LAPOSTE_TOKEN_FACTORY_ADDRESS,
    VOTEMARKET_CLAIM_TOPIC,
    VOTEMARKET_PLATFORM_ADDRESSES,
)
from rotkehlchen.chain.evm.decoding.stakedao.v2.utils import (
    ensure_stakedao_v2_vault_token_exists,
    query_stakedao_v2_vaults,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import get_address_to_address_dict_from_cache
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Stakedaov2CommonDecoder(EvmDecoderInterface, ReloadableDecoderMixin):
    """Base decoder for Stake DAO v2 protocol."""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            accountant_address: ChecksumEvmAddress | None,
            reward_token_address: ChecksumEvmAddress | None,
    ):
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.vaults: dict[ChecksumEvmAddress, ChecksumEvmAddress] = {}
        self.accountant_address = accountant_address
        self.reward_token_address = reward_token_address

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Refresh the vaults cache."""
        if should_update_protocol_cache(
            userdb=self.base.database,
            cache_key=CacheType.STAKEDAO_V2_VAULTS,
            args=(str(self.node_inquirer.chain_id.serialize()),),
        ):
            query_stakedao_v2_vaults(
                chain_id=self.node_inquirer.chain_id,
                msg_aggregator=self.msg_aggregator,
            )
        elif len(self.vaults) != 0:
            return None  # didn't update cache and we already have the vault info

        self.vaults = get_address_to_address_dict_from_cache(
            cache_type=CacheType.STAKEDAO_V2_VAULTS,
            chain_id=self.node_inquirer.chain_id,
            description='StakeDAO V2 vault',
        )
        return self.addresses_to_decoders()

    def _decode_deposit_withdraw(
            self,
            context: DecoderContext,
            assets_expected_event_type: HistoryEventType,
            assets_event_type: HistoryEventType,
            assets_event_subtype: HistoryEventSubType,
            assets_notes: str,
            shares_expected_event_type: HistoryEventType,
            shares_event_type: HistoryEventType,
            shares_event_subtype: HistoryEventSubType,
            shares_notes: str,
            is_deposit: bool,
    ) -> EvmDecodingOutput:
        """Decode deposit/withdraw events for StakeDAO vaults.

        Etherscan shows the deposit/withdraw events with incorrect labels.
        See the following source for what is actually emitted:
        Deposit: https://github.com/stake-dao/contracts-monorepo/blob/main/packages/strategies/src/RewardVault.sol#L300
        Withdraw: https://github.com/stake-dao/contracts-monorepo/blob/main/packages/strategies/src/RewardVault.sol#L395
        """
        if (vault_token := self.base.get_evm_token(address=context.tx_log.address)) is None:
            log.error(
                f'StakeDAO v2 vault token for transaction {context.transaction} '
                f'is missing or has invalid underlying tokens.',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        underlying_tokens = vault_token.underlying_tokens
        if (
            underlying_tokens is None or
            len(underlying_tokens) != 1 or
            (underlying_token := self.base.get_evm_token(address=underlying_tokens[0].address)) is None  # noqa: E501
        ):
            log.error(
                f'StakeDAO v2 vault token for transaction {context.transaction} '
                f'is missing or has invalid underlying tokens.',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        assets_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token=underlying_token,
        )
        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=vault_token,
        )
        asset_event = shares_event = None
        for event in context.decoded_events:
            if (
                event.event_type == assets_expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == underlying_token and
                event.amount == assets_amount
            ):
                event.event_type = assets_event_type
                event.event_subtype = assets_event_subtype
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = assets_notes.format(amount=event.amount, asset=underlying_token.symbol)  # noqa: E501
                asset_event = event
            elif (
                    event.event_type == shares_expected_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == vault_token and
                    event.amount == shares_amount
            ):
                event.event_type = shares_event_type
                event.event_subtype = shares_event_subtype
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = shares_notes.format(amount=event.amount, asset=vault_token.symbol)
                shares_event = event

        if asset_event is None or shares_event is None:
            log.error(f'Failed to find both StakeDAO out/in events for transaction {context.transaction}')  # noqa: E501
        else:
            maybe_reshuffle_events(
                ordered_events=[asset_event, shares_event] if is_deposit else [shares_event, asset_event],  # noqa: E501
                events_list=context.decoded_events,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
        ensure_stakedao_v2_vault_token_exists(
            evm_inquirer=self.node_inquirer,
            vault=context.tx_log.address,
            underlying=self.vaults[context.tx_log.address],
        )

        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            return self._decode_deposit_withdraw(
                context=context,
                assets_expected_event_type=HistoryEventType.SPEND,
                assets_event_type=HistoryEventType.DEPOSIT,
                assets_event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                assets_notes='Deposit {amount} {asset} in StakeDAO',
                shares_expected_event_type=HistoryEventType.RECEIVE,
                shares_event_type=HistoryEventType.RECEIVE,
                shares_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                shares_notes='Receive {amount} {asset} after deposit in StakeDAO',
                is_deposit=True,
            )
        if context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            return self._decode_deposit_withdraw(
                context=context,
                assets_expected_event_type=HistoryEventType.RECEIVE,
                assets_event_type=HistoryEventType.WITHDRAWAL,
                assets_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                assets_notes='Withdraw {amount} {asset} from StakeDAO',
                shares_expected_event_type=HistoryEventType.SPEND,
                shares_event_type=HistoryEventType.SPEND,
                shares_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                shares_notes='Return {amount} {asset} to StakeDAO',
                is_deposit=False,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_accountant_claim_reward(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != REWARDS_CLAIMED_TOPIC or
            self.reward_token_address is None
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(
            action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=(reward_token := self.base.get_or_create_evm_token(
                    address=self.reward_token_address,
                    encounter=TokenEncounterInfo(should_notify=False),
                )),
                amount=(amount := token_normalized_value(
                    token_amount=int.from_bytes(context.tx_log.data[32:64]),
                    token=reward_token,
                )),
                to_event_subtype=HistoryEventSubType.REWARD,
                to_notes=f'Claim {amount} {reward_token.symbol} from StakeDAO',
                to_counterparty=CPT_STAKEDAO_V2,
            )],
        )

    def _decode_votemarket_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VOTEMARKET_CLAIM_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.is_tracked(claimant := bytes_to_address(context.tx_log.topics[2])) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        claim_amount_raw = int.from_bytes(context.tx_log.data[:32])
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == claimant and
                event.amount == token_normalized_value(
                    claim_amount_raw,
                    event.asset.resolve_to_evm_token(),
                )
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = (
                    f'Claim {event.amount} {event.asset.symbol_or_name()} '
                    f'from StakeDAO votemarket'
                )
                break
        else:
            log.error(
                f'Failed to match StakeDAO votemarket claim for transaction {context.transaction}',
            )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == claimant and
                event.asset == self.node_inquirer.native_token and
                event.address == LAPOSTE_BUNDLER_ADDRESS
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = (
                    f'Spend {event.amount} {self.node_inquirer.native_token.symbol} '
                    f'as StakeDAO votemarket fee'
                )
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_laposte_bridge_out(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != LAPOSTE_MESSAGE_SENT_TOPIC or
            bytes_to_address(context.tx_log.topics[3]) != LAPOSTE_BUNDLER_ADDRESS or
            int.from_bytes(context.tx_log.topics[1]) != ChainID.ETHEREUM.serialize()
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        receiver = bytes_to_address(context.tx_log.data[:32])
        source_chain = self.node_inquirer.chain_id.label()
        bridge_sender = None
        bridged_events = []
        for event in context.decoded_events:
            if not (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label is not None and
                event.asset != self.node_inquirer.native_token and
                event.address == LAPOSTE_BUNDLER_ADDRESS
            ):
                continue

            if bridge_sender is None:
                if self.base.is_tracked(
                    sender := deserialize_evm_address(event.location_label),
                ) is False:
                    return DEFAULT_EVM_DECODING_OUTPUT
                bridge_sender = sender
            elif event.location_label != bridge_sender:
                continue

            bridge_token = event.asset.resolve_to_evm_token()

            # Only classify as a bridge deposit when destination is tracked.
            # For untracked receivers we keep spend semantics, but still annotate
            # counterparty/notes to preserve protocol attribution and context.
            if self.base.is_tracked(receiver):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
            event.counterparty = CPT_STAKEDAO_V2
            event.notes = (
                f'Bridge {event.amount} {bridge_token.symbol} from {source_chain} '
                f'to Ethereum for {receiver} via StakeDAO votemarket'
            )
            bridged_events.append(event)

        bridge_fee_event = None
        refund_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == bridge_sender and
                event.asset == self.node_inquirer.native_token and
                event.address == LAPOSTE_BUNDLER_ADDRESS
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = f'Spend {event.amount} {self.node_inquirer.native_token.symbol} as StakeDAO votemarket bridge fee'  # noqa: E501
                bridge_fee_event = event
                break

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == bridge_sender and
                event.asset == self.node_inquirer.native_token and
                event.address == LAPOSTE_ADDRESS
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                event.counterparty = CPT_STAKEDAO_V2
                event.notes = (
                    f'Refund of {event.amount} '
                    f'{self.node_inquirer.native_token.symbol} from StakeDAO votemarket bridge'
                )
                refund_event = event
                break

        if bridge_fee_event is not None:
            bridged_events.append(bridge_fee_event)
        if refund_event is not None:
            bridged_events.append(refund_event)
        maybe_reshuffle_events(ordered_events=bridged_events, events_list=context.decoded_events)
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_laposte_bridge_in(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != LAPOSTE_MESSAGE_RECEIVED_TOPIC or
            bytes_to_address(context.tx_log.topics[3]) != LAPOSTE_BUNDLER_ADDRESS
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        receiver, message, _ = decode_abi(
            ['address', '(uint256,address,address,(address,uint256)[],(string,string,uint8)[],bytes,uint256)', 'bool'],  # noqa: E501
            context.tx_log.data,
        )

        if self.base.is_tracked(receiver := deserialize_evm_address(receiver)) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        target_chain = self.node_inquirer.chain_id.label()
        try:
            source_chain = ChainID.deserialize(int.from_bytes(context.tx_log.topics[1])).label()
        except DeserializationError:
            log.warning(f'Could not deserialize chain id {context.tx_log.topics[1]!r} during {context.transaction} decoding.')  # noqa: E501
            source_chain = 'Unknown Chain'

        bridged_token_amounts = {
            deserialize_evm_address(token_data[0]): token_data[1]
            for token_data in message[3]
        }
        bridged_events = []
        for event in context.decoded_events:
            if not (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == receiver and
                event.address == LAPOSTE_TOKEN_FACTORY_ADDRESS
            ):
                continue
            if (
                (bridge_token := event.asset.resolve_to_evm_token()).evm_address not in
                bridged_token_amounts
            ):
                continue
            if event.amount != token_normalized_value(
                bridged_token_amounts[bridge_token.evm_address],
                bridge_token,
            ):
                continue

            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.BRIDGE
            event.counterparty = CPT_STAKEDAO_V2
            event.notes = (
                f'Bridge {event.amount} {bridge_token.symbol} from {source_chain} to '
                f'{target_chain} for {receiver} via StakeDAO votemarket'
            )
            bridged_events.append(event)

        maybe_reshuffle_events(ordered_events=bridged_events, events_list=context.decoded_events)
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_laposte_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if self.node_inquirer.chain_id == ChainID.ETHEREUM:
            return self._decode_laposte_bridge_in(context)
        return self._decode_laposte_bridge_out(context)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mappings: dict[ChecksumEvmAddress, tuple[Any, ...]] = dict.fromkeys(
            self.vaults,
            (self._decode_vault_events,),
        )
        if self.accountant_address is not None and self.reward_token_address is not None:
            mappings[self.accountant_address] = (self._decode_accountant_claim_reward,)
        for address in VOTEMARKET_PLATFORM_ADDRESSES:
            mappings[address] = (self._decode_votemarket_claim,)
        mappings[LAPOSTE_ADDRESS] = (self._decode_laposte_events,)

        return mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_STAKEDAO_V2,
            label='Stakedao V2',
            image='stakedao.png',
        ),)
