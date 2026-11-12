from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC,
    WITHDRAW_TOPIC_V3,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_ETHENA, SILO_TO_VAULT, STAKING_VAULTS

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction


class EthenaDecoder(EvmDecoderInterface):
    """Decoder for the Ethena staking vaults (USDe -> sUSDe and ENA -> sENA).

    Both vaults are ERC4626 tokens with a cooldown. cooldownShares/cooldownAssets burn the
    staked tokens and emit a Withdraw event whose receiver is the vault's silo, which holds the
    underlying tokens until the user calls unstake once the cooldown has passed. The sUSDe
    unstake emits no event of its own, so for both vaults the claim is decoded from the silo's
    transfer to the receiver.
    """

    def _decode_staking_vault(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            self._decode_stake(context)
        elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            self._decode_cooldown(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stake(self, context: DecoderContext) -> None:
        """Decode Deposit(sender, owner, assets, shares) of a vault"""
        vault = STAKING_VAULTS[context.tx_log.address]
        sender = bytes_to_address(context.tx_log.topics[1])
        owner = bytes_to_address(context.tx_log.topics[2])
        assets = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        shares = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        deposit_event = receive_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.address == context.tx_log.address and
                event.asset.identifier == vault.underlying_token_id and
                event.amount == assets
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_ETHENA
                event.notes = f'Stake {assets} {vault.underlying_symbol} in Ethena'
                deposit_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == owner and
                event.asset.identifier == vault.token_id and
                event.amount == shares
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_ETHENA
                event.notes = f'Receive {shares} {vault.symbol} after staking in Ethena'
                receive_event = event

        maybe_reshuffle_events(
            ordered_events=[deposit_event, receive_event],
            events_list=context.decoded_events,
        )

    def _decode_cooldown(self, context: DecoderContext) -> None:
        """Decode Withdraw(sender, receiver, owner, assets, shares) of a vault to its silo.

        This is emitted by cooldownShares/cooldownAssets. Withdrawing to any other receiver is
        only possible while the cooldown duration is zero, which neither vault has used.
        """
        vault = STAKING_VAULTS[context.tx_log.address]
        if bytes_to_address(context.tx_log.topics[2]) != vault.silo:
            return

        owner = bytes_to_address(context.tx_log.topics[3])
        assets = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        shares = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == owner and
                event.asset.identifier == vault.token_id and
                event.amount == shares
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_ETHENA
                event.notes = f'Return {shares} {vault.symbol} to Ethena and start the cooldown to unstake {assets} {vault.underlying_symbol}'  # noqa: E501
                break

    def _decode_unstake(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        """Decode the tokens a silo sends to the receiver of an unstake after the cooldown"""
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address is not None and
                (vault := SILO_TO_VAULT.get(event.address)) is not None and
                event.asset.identifier == vault.underlying_token_id
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_ETHENA
                event.notes = f'Unstake {event.amount} {vault.underlying_symbol} from Ethena after the cooldown'  # noqa: E501

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(STAKING_VAULTS, (self._decode_staking_vault,))

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        """Map the vaults and their silos to Ethena so that the unstake rule runs.

        The silos are matched through the decoded transfer when unstake is called by another
        contract, such as a Safe, instead of directly on the vault.
        """
        return dict.fromkeys((*STAKING_VAULTS, *SILO_TO_VAULT), CPT_ETHENA)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ETHENA: [(0, self._decode_unstake)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_ETHENA, label='Ethena', image='ethena.png'),)
