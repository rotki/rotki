import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.evm_event import LIQUITY_STAKING_DETAILS
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_LIQUITY

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

BALANCE_UPDATE = b'\xca#+Z\xbb\x98\x8cT\x0b\x95\x9f\xf6\xc3\xbf\xae>\x97\xff\xf9d\xfd\t\x8cP\x8f\x96\x13\xc0\xa6\xbf\x1a\x80'  # noqa: E501
ACTIVE_POOL = string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F')
STABILITY_POOL = string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb')
LIQUITY_STAKING = string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d')

STABILITY_POOL_GAIN_WITHDRAW = b'QEr"\xeb\xca\x92\xc35\xc9\xc8n+\xaa\x1c\xc0\xe4\x0f\xfa\xa9\x08JQE)\x80\xd5\xba\x8d\xec/c'  # noqa: E501
STABILITY_POOL_LQTY_PAID = b'&\x08\xb9\x86\xa6\xac\x0flb\x9c\xa3p\x18\xe8\n\xf5V\x1e6bR\xae\x93`*\x96\xd3\xab.s\xe4-'  # noqa: E501
STABILITY_POOL_EVENTS = {STABILITY_POOL_GAIN_WITHDRAW, STABILITY_POOL_LQTY_PAID}
STAKING_LQTY_CHANGE = b'9\xdf\x0eR\x86\xa3\xef/B\xa0\xbfR\xf3,\xfe,X\xe5\xb0@_G\xfeQ/,$9\xe4\xcf\xe2\x04'  # noqa: E501
STAKING_GAINS = b'\xf7D\xd3L\xa1\xcb%\xac\xfaA\x80\xdf_\t\xa6s\x06\x10q\x10\xa9\xf4\xb6\xed\x99\xbb;\xe2Ys\x82\x15'  # noqa: E501
STAKING_ETH_SENT = b'a\t\xe2U\x9d\xfavj\xae\xc7\x11\x83Q\xd4\x8aR?\nAW\xf4\x9c\x8dht\x9c\x8a\xc4\x13\x18\xad\x12'  # noqa: E501
STAKING_LQTY_EVENTS = {STAKING_LQTY_CHANGE, STAKING_ETH_SENT}
STAKING_REWARDS_ASSETS = {A_ETH, A_LUSD}

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LiquityDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.lusd = A_LUSD.resolve_to_crypto_asset()
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.lqty = A_LQTY.resolve_to_evm_token()

    def _decode_trove_operations(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != BALANCE_UPDATE:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_LIQUITY)
                continue
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_LUSD:
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Generate {event.balance.amount} {self.lusd.symbol} from liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Return {event.balance.amount} {self.lusd.symbol} to liquity'
            elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} as collateral for liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} collateral from liquity'  # noqa: E501
        return DEFAULT_DECODING_OUTPUT

    def _decode_stability_pool_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in STABILITY_POOL_EVENTS:
            return DEFAULT_DECODING_OUTPUT

        collected_eth, collected_lqty = ZERO, ZERO
        if context.tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW:
            collected_eth = asset_normalized_value(
                amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
                asset=self.eth,
            )
        elif context.tx_log.topics[0] == STABILITY_POOL_LQTY_PAID:
            collected_lqty = asset_normalized_value(
                amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
                asset=self.lqty,
            )

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f"Deposit {event.balance.amount} {self.lusd.symbol} in liquity's stability pool"  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE:
                if (
                    (
                        event.asset == self.eth and
                        event.balance.amount == collected_eth and
                        context.tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW
                    ) or (
                        event.asset == self.lqty and
                        event.balance.amount == collected_lqty and
                        context.tx_log.topics[0] == STABILITY_POOL_LQTY_PAID
                    )
                ):
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_LIQUITY
                    resolved_asset = event.asset.resolve_to_asset_with_symbol()
                    event.notes = f"Collect {event.balance.amount} {resolved_asset.symbol} from liquity's stability pool"  # noqa: E501
                elif event.asset == self.lusd:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f"Withdraw {event.balance.amount} {self.lusd.symbol} from liquity's stability pool"  # noqa: E501
        return DEFAULT_DECODING_OUTPUT

    def _decode_lqty_staking_deposits(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in STAKING_LQTY_EVENTS:
            return DEFAULT_DECODING_OUTPUT

        user, lqty_amount = None, ZERO
        if context.tx_log.topics[0] == STAKING_LQTY_CHANGE:
            user = hex_or_bytes_to_address(context.tx_log.topics[1])
            lqty_amount = asset_normalized_value(
                amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
                asset=self.lqty,
            )

        informational_event = None
        for event in context.decoded_events:
            if (
                context.tx_log.topics[0] == STAKING_LQTY_CHANGE and
                event.asset == A_LQTY
            ):
                extra_data = {
                    LIQUITY_STAKING_DETAILS: {
                        'staked_amount': str(lqty_amount),
                        'asset': self.lqty.identifier,
                    },
                }
                if event.location_label == user and event.event_type == HistoryEventType.SPEND:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f'Stake {event.balance.amount} {self.lqty.symbol} in the Liquity protocol'  # noqa: E501
                    event.extra_data = extra_data
                elif event.location_label == user and event.event_type == HistoryEventType.RECEIVE:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_LIQUITY
                    event.notes = f'Unstake {event.balance.amount} {self.lqty.symbol} from the Liquity protocol'  # noqa: E501
                    event.extra_data = extra_data
            elif (
                context.tx_log.topics[0] == STAKING_ETH_SENT and
                event.asset in STAKING_REWARDS_ASSETS and
                event.event_type == HistoryEventType.RECEIVE
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_LIQUITY
                event.notes = f"Receive reward of {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} from Liquity's staking"  # noqa: E501

        return DecodingOutput(event=informational_event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ACTIVE_POOL: (self._decode_trove_operations,),
            STABILITY_POOL: (self._decode_stability_pool_event,),
            LIQUITY_STAKING: (self._decode_lqty_staking_deposits,),
        }

    def counterparties(self) -> list[str]:
        return [CPT_LIQUITY]
