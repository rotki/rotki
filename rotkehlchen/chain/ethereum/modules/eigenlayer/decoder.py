import logging
from typing import Any

from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    CPT_EIGENLAYER,
    DEPOSIT_TOPIC,
    EIGEN_TOKEN_ID,
    EIGENLAYER_AIRDROP_DISTRIBUTOR,
    EIGENLAYER_CPT_DETAILS,
    EIGENLAYER_STRATEGY_MANAGER,
    WITHDRAWAL_COMPLETE_TOPIC,
)
from rotkehlchen.chain.evm.decoding.clique.decoder import CliqueAirdropDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EigenlayerDecoder(CliqueAirdropDecoderInterface):

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        depositor = hex_or_bytes_to_address(context.tx_log.data[0:32])
        token_addr = hex_or_bytes_to_address(context.tx_log.data[32:64])
        token_identifier = ethaddress_to_identifier(address=token_addr)
        strategy = hex_or_bytes_to_address(context.tx_log.data[64:96])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.asset == token_identifier and
                event.location_label == depositor
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                asset = event.asset.resolve_to_crypto_asset()
                event.notes = f'Deposit {event.balance.amount} {asset.symbol} in EigenLayer'
                event.extra_data = {'strategy': strategy}
                event.product = EvmProduct.STAKING
                event.counterparty = CPT_EIGENLAYER

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """
        Decode withdrawal from eigenlayer. The transaction only contains a transfer event
        and the unstake event but the unstake event doesn't have information about the asset
        or the amount unstaked.
        """
        depositor = hex_or_bytes_to_address(context.tx_log.topics[1])
        withdrawer = hex_or_bytes_to_address(context.tx_log.topics[2])
        depositor_is_tracked = self.base.is_tracked(depositor)
        withdrawer_is_tracked = self.base.is_tracked(withdrawer)

        if depositor_is_tracked is True and withdrawer_is_tracked is True:
            event_type, event_subtype = HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET
            notes = 'Unstake {amount} {symbol} from EigenLayer'
        elif depositor_is_tracked is False and withdrawer_is_tracked is True:  # it is unstake + transfer  # noqa: E501
            event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.NONE
            notes = 'Receive {amount} {symbol} from EigenLayer depositor {depositor} unstaking'
        elif depositor_is_tracked is True and withdrawer_is_tracked is False:  # we withdraw to a different address not tracked  # noqa: E501
            notes = 'Send {amount} {symbol} from EigenLayer to {withdrawer} via unstaking'
            event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.NONE
        else:
            log.error(f'Unexpected eigenlayer withdrawal in {context.transaction.tx_hash.hex()}. Skipping')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE:
                event.event_type = event_type
                event.event_subtype = event_subtype
                event.counterparty = CPT_EIGENLAYER
                event.product = EvmProduct.STAKING
                event.notes = notes.format(amount=event.balance.amount, symbol=event.asset.resolve_to_crypto_asset().symbol)  # noqa: E501
                break
        else:
            log.error(f'Could not match eigenlayer withdrawal event in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def decode_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            return self._decode_deposit(context)
        elif context.tx_log.topics[0] == WITHDRAWAL_COMPLETE_TOPIC:
            return self._decode_withdrawal(context)

        return DEFAULT_DECODING_OUTPUT

    def decode_airdrop(self, context: DecoderContext) -> DecodingOutput:
        if not (decode_result := self._decode_claim(context)):
            return DEFAULT_DECODING_OUTPUT

        claiming_address, claimed_amount = decode_result
        notes = f'Claim {claimed_amount} EIGEN from the Eigenlayer airdrop'
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset.identifier == EIGEN_TOKEN_ID and
                event.balance.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_EIGENLAYER
                event.notes = notes
                break
        else:
            log.error(f'Could not match eigenlayer airdrop receive event in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            EIGENLAYER_STRATEGY_MANAGER: (self.decode_event,),
            EIGENLAYER_AIRDROP_DISTRIBUTOR: (self.decode_airdrop,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (EIGENLAYER_CPT_DETAILS,)

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {CPT_EIGENLAYER: [EvmProduct.STAKING]}
