from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.decoding.aave.common import Commonv2v3LikeDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from ..constants import CPT_AAVE_V2
from .constants import BORROW, DEPOSIT, REPAY

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev2CommonDecoder(Commonv2v3LikeDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_addresses: Sequence['ChecksumEvmAddress'],
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            incentives: 'ChecksumEvmAddress',
            incentives_reward_token: 'ChecksumEvmAddress',
            v3_migration_helper: 'ChecksumEvmAddress',
    ):
        Commonv2v3LikeDecoder.__init__(
            self,
            counterparty=CPT_AAVE_V2,
            label='AAVE v2',
            pool_addresses=pool_addresses,
            deposit_signature=DEPOSIT,
            borrow_signature=BORROW,
            repay_signature=REPAY,
            native_gateways=native_gateways,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.v3_migration_helper = v3_migration_helper
        self.incentives = incentives
        self.incentives_reward_token = incentives_reward_token

    def decode_liquidation(self, context: 'DecoderContext') -> None:
        """
        Decode AAVE v2 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if not self.base.is_tracked(bytes_to_address(context.tx_log.topics[3])):
            return

        for event in context.decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[32:64]),  # liquidated amount
                asset=asset,
            ) == event.amount and asset.protocol == CPT_AAVE_V2:
                # we are transferring the aTOKEN
                event.event_type = HistoryEventType.LOSS
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An {self.label} position got liquidated for {event.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = CPT_AAVE_V2
                event.address = context.tx_log.address
            elif asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[:32]),  # debt amount
                asset=asset,
            ) == event.amount:
                # we are transferring the debt token
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.amount} {asset.symbol} for an {self.label} position'
                event.counterparty = CPT_AAVE_V2
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differentiate paybacks happening in liquidations.  # noqa: E501

    def _decode_incentives(self, context: 'DecoderContext') -> DecodingOutput:
        if context.tx_log.topics[0] != b'V7\xd7\xf9b$\x8a\x7f\x05\xa7\xabi\xee\xc6Dn1\xf3\xd0\xa2\x99\xd9\x97\xf15\xa6\\b\x80nx\x91':  # RewardsClaimed  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return self._decode_incentives_common(
            context=context,
            to_idx=2,
            claimer_raw=context.tx_log.topics[3],
            reward_token_address=self.incentives_reward_token,
            amount_raw=context.tx_log.data[0:32],
        )

    def _decode_migration(self, context: 'DecoderContext') -> DecodingOutput:
        if context.tx_log.topics[0] != b'K\xec\xcb\x90\xf9\x94\xc3\x1a\xce\xd7\xa2;V\x11\x02\x07(\xa2=\x8e\xc5\xcd\xdd\x1a>\x9d\x97\xb9o\xda\x86f':  # TokenTransferred # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if self.v3_migration_helper and (bytes_to_address(context.tx_log.topics[2])) == self.v3_migration_helper and self.base.is_tracked(from_address := bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            token = self.base.get_evm_token(address=context.tx_log.address)
            assert token, 'token should be in the DB. Decoding rule reads it from the DB'
            amount = token_normalized_value(token_amount=int.from_bytes(context.tx_log.data[:32]), token=token)  # noqa: E501
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=amount,
                location_label=from_address,
                to_event_type=HistoryEventType.MIGRATE,
                to_event_subtype=HistoryEventSubType.SPEND,
                to_notes=f'Migrate {amount} {token.symbol} from AAVE v2',
                to_counterparty=CPT_AAVE_V2,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    # --- DecoderInterface methods
    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AAVE_V2,
            label=CPT_AAVE_V2.capitalize().replace('-v', ' V'),
            image='aave.svg',
        ),)

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return dict.fromkeys(GlobalDBHandler.get_addresses_by_protocol(
            chain_id=self.evm_inquirer.chain_id,
            protocol=CPT_AAVE_V2,
        ), CPT_AAVE_V2) | dict.fromkeys(self.pool_addresses, CPT_AAVE_V2)

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.incentives: (self._decode_incentives,),
        } | dict.fromkeys(GlobalDBHandler.get_addresses_by_protocol(
            chain_id=self.evm_inquirer.chain_id,
            protocol=CPT_AAVE_V2,
        ), (self._decode_migration,))
