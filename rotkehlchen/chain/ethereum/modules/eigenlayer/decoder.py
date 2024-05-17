import logging
from typing import Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    CPT_EIGENLAYER,
    DELAYED_WITHDRAWAL_CREATED,
    DEPOSIT_TOPIC,
    EIGEN_TOKEN_ID,
    EIGENLAYER_AIRDROP_DISTRIBUTOR,
    EIGENLAYER_CPT_DETAILS,
    EIGENLAYER_STRATEGY_MANAGER,
    EIGENPOD_DELAYED_WITHDRAWAL_ROUTER,
    EIGENPOD_MANAGER,
    FULL_WITHDRAWAL_REDEEMED,
    PARTIAL_WITHDRAWAL_REDEEMED,
    POD_DEPLOYED,
    WITHDRAWAL_COMPLETE_TOPIC,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.clique.decoder import CliqueAirdropDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

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

    def decode_eigenpod_creation(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != POD_DEPLOYED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(owner := hex_or_bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_DECODING_OUTPUT

        eigenpod_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        suffix = f' with owner {owner}' if context.transaction.from_address != owner else ''
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Deploy eigenpod {eigenpod_address}{suffix}',
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
            extra_data={'eigenpod_owner': owner, 'eigenpod_address': eigenpod_address},
        )
        return DecodingOutput(event=event)

    def decode_delayed_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DELAYED_WITHDRAWAL_CREATED:
            return DEFAULT_DECODING_OUTPUT

        pod_owner = hex_or_bytes_to_address(context.tx_log.data[0:32])
        recipient = hex_or_bytes_to_address(context.tx_log.data[32:64])
        if not self.base.any_tracked([pod_owner, recipient]):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(token_amount=hex_or_bytes_to_int(context.tx_log.data[64:96]), token_decimals=18)  # noqa: E501
        partial_withdrawals_redeemed, full_withdrawals_redeemed = 0, 0
        for log_entry in context.all_logs:
            if log_entry.topics[0] == PARTIAL_WITHDRAWAL_REDEEMED:
                partial_withdrawals_redeemed += 1
            elif log_entry.topics[0] == FULL_WITHDRAWAL_REDEEMED:
                full_withdrawals_redeemed += 1

        notes = f'Start a delayed withdrawal of {amount} ETH from Eigenlayer'
        if partial_withdrawals_redeemed != 0 or full_withdrawals_redeemed != 0:
            notes += f' by processing {partial_withdrawals_redeemed} partial and {full_withdrawals_redeemed} full beaconchain withdrawals'  # noqa: E501
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            EIGENLAYER_STRATEGY_MANAGER: (self.decode_event,),
            EIGENLAYER_AIRDROP_DISTRIBUTOR: (self.decode_airdrop,),
            EIGENPOD_MANAGER: (self.decode_eigenpod_creation,),
            EIGENPOD_DELAYED_WITHDRAWAL_ROUTER: (self.decode_delayed_withdrawal,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (EIGENLAYER_CPT_DETAILS,)

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {CPT_EIGENLAYER: [EvmProduct.STAKING]}
