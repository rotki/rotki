import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.optimism.modules.walletconnect.constants import WALLETCONECT_STAKE_WEIGHT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import bytes_to_address
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import (
    CPT_WALLETCONNECT,
    WALLETCONECT_AIRDROP_CLAIM,
    WALLETCONNECT_CPT_DETAILS,
    WCT_TOKEN_ID,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKENS_CLAIMED: Final = b'\x89n\x03If\xea\xaf\x1a\xdcT\xac\xc0\xf2W\x05o\xeb\xbd0\x0c\x9eG\x18,\xf7a\x98,\xf1\xf5\xe40'  # noqa: E501
STAKING_DEPOSIT: Final = b'\xf9C\xcf\x10\xefM\x1e29\xf4qm\xde\xcd\xf5F\xe8\xba\x8a\xb0\xe4\x1d\xea\xfd\x9aq\xa9\x996\x82~E'  # noqa: E501
STAKING_WITHDRAW: Final = b"\x02\xf2Rp\xa4\xd8{\xeau\xdbT\x1c\xdf\xe5Y3J'[J#5 \xedl\n$)f|\xca\x94"


class WalletconnectDecoder(DecoderInterface, CustomizableDateMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        CustomizableDateMixin.__init__(self, base_tools.database)

    def _decode_airdop_claim(self, context: 'DecoderContext') -> DecodingOutput:
        """Decodes wallet connect airdrop claim event."""
        if context.tx_log.topics[0] != TOKENS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if match_airdrop_claim(
                    event=event,
                    user_address=user_address,
                    amount=amount,
                    asset=Asset(WCT_TOKEN_ID),
                    counterparty=CPT_WALLETCONNECT,
                    airdrop_identifier='walletconnect',
            ):
                break
        else:
            log.error(f'Failed to find walletconnect airdrop claim event for {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_staking_deposit(self, context: 'DecoderContext') -> DecodingOutput:
        user_address = bytes_to_address(context.tx_log.topics[1])
        locktime = Timestamp(int.from_bytes(context.tx_log.data[32:64]))
        transferred_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[96:128]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        # according to the contract `transferred_amount` is either equal to amount
        # or zero. If zero then no transfer has occurred, but just lock time has changed
        if transferred_amount == ZERO:
            return DecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=Asset(WCT_TOKEN_ID),
                amount=ZERO,
                location_label=user_address,
                notes=f'Increase WCT staking expiration until {self.timestamp_to_date(locktime)}',
                address=context.tx_log.address,
                counterparty=CPT_WALLETCONNECT,
                extra_data={'until': locktime},
        )])

        for event in context.decoded_events:
            if (
                    event.location_label == user_address and
                    event.address == WALLETCONECT_STAKE_WEIGHT and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == WCT_TOKEN_ID and
                    event.amount == transferred_amount
            ):
                event.counterparty = CPT_WALLETCONNECT
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Stake {transferred_amount} WCT until {self.timestamp_to_date(locktime)}'  # noqa: E501
                event.extra_data = {'until': locktime}
                break

        else:  # not found
            log.error(f'WCT staking deposit transfer was not found for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _decode_staking_withdraw(self, context: 'DecoderContext') -> DecodingOutput:
        user_address = bytes_to_address(context.tx_log.topics[1])
        transferred_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.location_label == user_address and
                    event.address == WALLETCONECT_STAKE_WEIGHT and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == WCT_TOKEN_ID and
                    event.amount == transferred_amount
            ):
                event.counterparty = CPT_WALLETCONNECT
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Unstake {transferred_amount} WCT'
                break

        else:  # not found
            log.error(f'WCT staking withdrawal transfer was not found for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _decode_staking(self, context: 'DecoderContext') -> DecodingOutput:
        """Decodes WalletConnect staking related activity"""
        if context.tx_log.topics[0] == STAKING_DEPOSIT:
            return self._decode_staking_deposit(context)
        elif context.tx_log.topics[0] == STAKING_WITHDRAW:
            return self._decode_staking_withdraw(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            WALLETCONECT_AIRDROP_CLAIM: (self._decode_airdop_claim,),
            WALLETCONECT_STAKE_WEIGHT: (self._decode_staking,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (WALLETCONNECT_CPT_DETAILS,)
