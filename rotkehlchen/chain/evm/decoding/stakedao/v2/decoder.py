import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import TokenEncounterInfo, token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, REWARDS_CLAIMED_TOPIC, WITHDRAW_TOPIC_V3
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.evm.decoding.stakedao.v2.utils import query_stakedao_v2_vaults
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import get_protocol_token_addresses
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress

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
            accountant_address: ChecksumEvmAddress,
            reward_token_address: ChecksumEvmAddress,
    ):
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.vaults: set[ChecksumEvmAddress] = set()
        self.accountant_address = accountant_address
        self.reward_token_address = reward_token_address

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Refresh the vaults cache."""
        if should_update_protocol_cache(
            userdb=self.base.database,
            cache_key=CacheType.STAKEDAO_V2_VAULTS,
            args=(str(self.node_inquirer.chain_id),),
        ):
            query_stakedao_v2_vaults(self.node_inquirer)

        self.vaults = get_protocol_token_addresses(
            protocol=CPT_STAKEDAO_V2,
            chain_id=self.node_inquirer.chain_id,
            existing_tokens=self.vaults,
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
        if (
            (vault_token := self.base.get_evm_token(address=context.tx_log.address)) is None or
            len(vault_token.underlying_tokens) != 1 or
            (underlying_token := self.base.get_evm_token(address=vault_token.underlying_tokens[0].address)) is None  # noqa: E501
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
        if context.tx_log.topics[0] != REWARDS_CLAIMED_TOPIC:
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

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.vaults, (self._decode_vault_events,)) | {
            self.accountant_address: (self._decode_accountant_claim_reward,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_STAKEDAO_V2,
            label='Stakedao V2',
            image='stakedao.png',
        ),)
