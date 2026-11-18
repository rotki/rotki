from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, STAKED_TOPIC_V2
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_LINK
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    COMMUNITY_POOL,
    CPT_CHAINLINK,
    MIGRATED_V01,
    REWARD_CLAIMED,
    REWARD_VAULT,
    STAKED_V02,
    STAKING_V01,
    STAKING_V02_POOLS,
    UNBONDING_PERIOD_STARTED,
    UNSTAKED,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


def _link_amount(raw_amount: bytes) -> FVal:
    return token_normalized_value_decimals(
        token_amount=int.from_bytes(raw_amount),
        token_decimals=DEFAULT_TOKEN_DECIMALS,
    )


class ChainlinkDecoder(EvmDecoderInterface):
    """Decoder for Chainlink staking.

    LINK is staked with transferAndCall to the staking pool, so the LINK transfer is decoded
    before the pool's Staked event. v0.2 has a community and an operator pool, which share
    their contract code, and a reward vault from which the rewards of both are claimed.
    v0.1 is concluded and only lets stakers unstake or migrate their stake and their rewards
    to the v0.2 community pool, both of which emit their event before the LINK transfer.
    """

    @staticmethod
    def _find_link_transfer(
            context: DecoderContext,
            event_type: HistoryEventType,
            staker: ChecksumEvmAddress,
            amount: FVal,
    ) -> EvmEvent | None:
        """Find the decoded LINK transfer between the staker and the contract of the log"""
        for event in context.decoded_events:
            if (
                event.event_type == event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_LINK and
                event.location_label == staker and
                event.address == context.tx_log.address and
                event.amount == amount
            ):
                return event

        return None

    def _decode_staking_v01(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (STAKED_TOPIC_V2, UNSTAKED, MIGRATED_V01):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.data[:32])):
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == STAKED_TOPIC_V2:
            if (event := self._find_link_transfer(
                context=context,
                event_type=HistoryEventType.SPEND,
                staker=staker,
                amount=(amount := _link_amount(context.tx_log.data[32:64])),
            )) is not None:
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CHAINLINK
                event.notes = f'Stake {amount} LINK in Chainlink staking v0.1'

            return DEFAULT_EVM_DECODING_OUTPUT

        principal = _link_amount(context.tx_log.data[32:64])
        rewards = _link_amount(context.tx_log.data[64:96]) + _link_amount(context.tx_log.data[96:128])  # noqa: E501
        if context.tx_log.topics[0] == UNSTAKED:
            return self._decode_unstake_v01(
                context=context,
                staker=staker,
                principal=principal,
                rewards=rewards,
            )

        return self._decode_migration_v01(
            context=context,
            staker=staker,
            principal=principal,
            rewards=rewards,
        )

    def _decode_unstake_v01(
            self,
            context: DecoderContext,
            staker: ChecksumEvmAddress,
            principal: FVal,
            rewards: FVal,
    ) -> EvmDecodingOutput:
        """Decode Unstaked(staker, principal, baseReward, delegationReward) of v0.1.

        The principal and the rewards come in one LINK transfer after this event, so that
        transfer is skipped and replaced by an unstake event and a reward event.
        """
        events = [self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LINK,
            amount=principal,
            location_label=staker,
            notes=f'Unstake {principal} LINK from Chainlink staking v0.1',
            counterparty=CPT_CHAINLINK,
            address=STAKING_V01,
        )]
        if rewards != ZERO:
            events.append(self.base.make_event_next_index(
                tx_ref=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=A_LINK,
                amount=rewards,
                location_label=staker,
                notes=f'Receive {rewards} LINK as Chainlink staking v0.1 rewards',
                counterparty=CPT_CHAINLINK,
                address=STAKING_V01,
            ))

        return EvmDecodingOutput(events=events, action_items=[ActionItem(
            action='skip',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_LINK,
            amount=principal + rewards,
            location_label=staker,
        )])

    def _decode_migration_v01(
            self,
            context: DecoderContext,
            staker: ChecksumEvmAddress,
            principal: FVal,
            rewards: FVal,
    ) -> EvmDecodingOutput:
        """Decode Migrated(staker, principal, baseReward, delegationReward, data) of v0.1.

        The principal and the rewards are transferred to the v0.2 community pool and staked
        there for the staker, without passing through the staker's wallet. The principal
        stays staked, while the rewards are earned and staked in the same transaction.
        """
        events = [self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_LINK,
            amount=ZERO,
            location_label=staker,
            notes=f'Migrate {principal} LINK staked in Chainlink staking v0.1 to the Chainlink community staking pool',  # noqa: E501
            counterparty=CPT_CHAINLINK,
            address=STAKING_V01,
        )]
        if rewards != ZERO:
            for event_type, event_subtype, notes, address in (
                (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, f'Receive {rewards} LINK as Chainlink staking v0.1 rewards', STAKING_V01),  # noqa: E501
                (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET, f'Stake {rewards} LINK of Chainlink staking v0.1 rewards in the Chainlink community staking pool', COMMUNITY_POOL),  # noqa: E501
            ):
                events.append(self.base.make_event_next_index(
                    tx_ref=context.transaction.tx_hash,
                    timestamp=context.transaction.timestamp,
                    event_type=event_type,
                    event_subtype=event_subtype,
                    asset=A_LINK,
                    amount=rewards,
                    location_label=staker,
                    notes=notes,
                    counterparty=CPT_CHAINLINK,
                    address=address,
                ))

        return EvmDecodingOutput(events=events)

    def _decode_staking_pool(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the events of a v0.2 staking pool"""
        if context.tx_log.topics[0] not in (STAKED_V02, UNSTAKED, UNBONDING_PERIOD_STARTED):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        pool = f'Chainlink {STAKING_V02_POOLS[context.tx_log.address]} staking pool'
        if context.tx_log.topics[0] == UNBONDING_PERIOD_STARTED:
            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_LINK,
                amount=ZERO,
                location_label=staker,
                notes=f'Start the unbonding period to unstake LINK from the {pool}',
                counterparty=CPT_CHAINLINK,
                address=context.tx_log.address,
            )])

        amount = _link_amount(context.tx_log.data[:32])
        if context.tx_log.topics[0] == STAKED_V02:
            # a stake migrated from v0.1 has no LINK transfer from the staker and is
            # decoded from the Migrated event of v0.1
            event_type = HistoryEventType.SPEND
            new_subtype = HistoryEventSubType.DEPOSIT_ASSET
            notes = f'Stake {amount} LINK in the {pool}'
        else:
            event_type = HistoryEventType.RECEIVE
            new_subtype = HistoryEventSubType.REMOVE_ASSET
            notes = f'Unstake {amount} LINK from the {pool}'

        if (event := self._find_link_transfer(
            context=context,
            event_type=event_type,
            staker=staker,
            amount=amount,
        )) is not None:
            event.event_type = HistoryEventType.STAKING
            event.event_subtype = new_subtype
            event.counterparty = CPT_CHAINLINK
            event.notes = notes

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_reward_vault(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode RewardClaimed(staker, claimedRewards) of the v0.2 reward vault"""
        if context.tx_log.topics[0] != REWARD_CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (event := self._find_link_transfer(
            context=context,
            event_type=HistoryEventType.RECEIVE,
            staker=bytes_to_address(context.tx_log.topics[1]),
            amount=(amount := _link_amount(context.tx_log.data[:32])),
        )) is not None:
            event.event_subtype = HistoryEventSubType.REWARD
            event.counterparty = CPT_CHAINLINK
            event.notes = f'Claim {amount} LINK of Chainlink staking rewards'

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            STAKING_V01: (self._decode_staking_v01,),
            REWARD_VAULT: (self._decode_reward_vault,),
        } | dict.fromkeys(STAKING_V02_POOLS, (self._decode_staking_pool,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_CHAINLINK,
            label='Chainlink',
            image='chainlink.svg',
        ),)
