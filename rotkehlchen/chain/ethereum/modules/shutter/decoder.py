import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.diva.decoder import DELEGATE_CHANGED
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_SHU
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_SHUTTER, REDEEMED_VESTING, SHUTTER_AIDROP_CONTRACT

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ShutterDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.shu = A_SHU.resolve_to_evm_token()

    def _decode_shutter_claim(self, context: DecoderContext) -> DecodingOutput:
        if not (
            context.tx_log.topics[0] == REDEEMED_VESTING and
            self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_DECODING_OUTPUT

        redeem_id = vesting_contract_address = None
        for tx_log in reversed(context.all_logs):
            if tx_log.topics[0] == REDEEMED_VESTING:
                redeem_id = tx_log.topics[1]
            elif (  # AddedVesting (id)
                tx_log.topics[0] == b'\xdc\x17\xa5b\x85\x03\x17a\xfbz\x86\xd9\n1"u1 ^\x1e\x9e\x8f\x85\xf4\xd0\xf0:T\xea_\xb9v' and  # noqa: E501
                tx_log.topics[1] == redeem_id
            ):
                vesting_contract_address = tx_log.address
            elif (
                tx_log.address == self.shu.evm_address and
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(tx_log.topics[1]) == SHUTTER_AIDROP_CONTRACT and
                bytes_to_address(tx_log.topics[2]) == vesting_contract_address
            ):
                amount = token_normalized_value(token_amount=int.from_bytes(tx_log.data), token=self.shu)  # noqa: E501
                break
        else:
            log.error(f'Could not find the SHU transfer in {context.transaction.tx_hash.hex()}')
            return DEFAULT_DECODING_OUTPUT

        return DecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.shu,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Claim {amount} SHU from shutter airdrop into the vesting contract: {vesting_contract_address}',  # noqa: E501
            counterparty=CPT_SHUTTER,
            address=context.transaction.to_address,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'shutter'},
        )])

    def _decode_delegation_change(self, context: DecoderContext) -> DecodingOutput:
        """This contract function (delegateTokens), can only be called by the owner,
        that is `context.transaction.from_address`. So not verifying the caller here."""
        if context.tx_log.topics[0] != DELEGATE_CHANGED:
            return DEFAULT_DECODING_OUTPUT

        delegator = bytes_to_address(context.tx_log.topics[1])
        delegator_note = ''
        if delegator != context.transaction.from_address:
            delegator_note = f' for {delegator}'
        return DecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.shu,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Change SHU Delegate{delegator_note} from {bytes_to_address(context.tx_log.topics[2])} to {bytes_to_address(context.tx_log.topics[3])}',  # noqa: E501
            counterparty=CPT_SHUTTER,
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            SHUTTER_AIDROP_CONTRACT: (self._decode_shutter_claim,),
            self.shu.evm_address: (self._decode_delegation_change,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_SHUTTER, label='Shutter', image='shutter.png'),)
