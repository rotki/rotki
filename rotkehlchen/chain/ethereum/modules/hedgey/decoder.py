import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.constants import DELEGATE_CHANGED, ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_HEDGEY,
    HEDGEY_PLAN_CONTRACTS,
    VOTING_TOKEN_LOCKUPS,
    VOTING_TOKEN_LOCKUPS_ABI,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HedgeyDecoder(EvmDecoderInterface):

    def _decode_delegate_changed(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            owner_address: ChecksumEvmAddress,
            plan_name: str,
    ) -> EvmDecodingOutput:
        token = self.base.get_or_create_evm_token(tx_log.address)
        from_delegate = bytes_to_address(tx_log.topics[2])
        to_delegate = bytes_to_address(tx_log.topics[3])
        notes = f'Change {token.symbol} delegate for {owner_address} {plan_name}'
        if from_delegate != ZERO_ADDRESS:
            notes += f' from {from_delegate}'
        notes += f' to {to_delegate}'
        event = self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=token,
            amount=ZERO,
            location_label=owner_address,
            notes=notes,
            counterparty=CPT_HEDGEY,
            address=tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_vault_creation(
            self,
            context: DecoderContext,
            plan_type: str,
    ) -> EvmDecodingOutput:
        vault_address = bytes_to_address(context.tx_log.data[:32])
        plan_id = int.from_bytes(context.tx_log.topics[1])
        owner_address = self.node_inquirer.call_contract(
            contract_address=context.tx_log.address,
            abi=VOTING_TOKEN_LOCKUPS_ABI,
            method_name='ownerOf',
            arguments=[plan_id],
        )
        if not self.base.is_tracked(owner_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        # now find the log of the token delegation
        for tx_log in context.all_logs:
            if tx_log.topics[0] == DELEGATE_CHANGED and bytes_to_address(tx_log.topics[1]) == vault_address:  # noqa: E501
                return self._decode_delegate_changed(
                    tx_log=tx_log,
                    transaction=context.transaction,
                    owner_address=owner_address,
                    plan_name=f'Hedgey {plan_type} {plan_id}',
                )

        log.error(f'Did not find a delegation event in {context.transaction} logs')
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_delegate_plans(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode direct delegate change after voting token lockup creation.
        Will only work if called by an EoA"""
        if not self.base.is_tracked(owner_address := context.transaction.from_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        contract = EvmContract(address=VOTING_TOKEN_LOCKUPS, abi=VOTING_TOKEN_LOCKUPS_ABI)
        _, args = contract.decode_input_data(context.transaction.input_data)
        if len(planids := args['planIds']) == 1:
            plan_name = f'Hedgey token lockup {planids[0]}'
        else:
            plan_name = f'Hedgey token lockups ({",".join(str(x) for x in planids)})'

        return self._decode_delegate_changed(
            transaction=context.transaction,
            tx_log=context.tx_log,
            owner_address=owner_address,
            plan_name=plan_name,
        )

    def _decode_plan_redeemed(self, context: DecoderContext) -> EvmDecodingOutput:
        plan_id = int.from_bytes(context.tx_log.topics[1])
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        owner_address = None
        burn_sequence_index = None
        if int.from_bytes(context.tx_log.data[32:64]) == 0:  # fully redeemed plans are burned
            for tx_log in context.all_logs:
                if (
                        tx_log.address == context.tx_log.address and
                        len(tx_log.topics) == 4 and
                        tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                        int.from_bytes(tx_log.topics[3]) == plan_id and
                        bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS
                ):
                    owner_address = bytes_to_address(tx_log.topics[1])
                    burn_sequence_index = self.base.get_sequence_index(tx_log)
                    break

        # Each redemption transfers the claimed tokens immediately before PlanRedeemed is emitted.
        # Reading the transfer also works after a full redemption has deleted the plan's storage.
        for tx_log in reversed(context.all_logs):
            if (
                    tx_log.log_index >= context.tx_log.log_index or
                    len(tx_log.topics) != 3 or
                    tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
                    int.from_bytes(tx_log.data) != amount_raw
            ):
                continue

            recipient = bytes_to_address(tx_log.topics[2])
            if (
                    (owner_address is not None and recipient != owner_address) or
                    (owner_address is None and not self.base.is_tracked(recipient))
            ):
                continue

            owner_address = recipient
            token = self.base.get_or_create_evm_token(address=tx_log.address)
            break
        else:
            log.error(
                'Could not find token transfer for Hedgey plan %s in %s',
                plan_id,
                context.transaction,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(owner_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_redeemed = token_normalized_value(token_amount=amount_raw, token=token)
        if burn_sequence_index is not None:
            for event in context.decoded_events:
                if event.sequence_index == burn_sequence_index:
                    event.event_type = HistoryEventType.BURN
                    event.event_subtype = HistoryEventSubType.NFT
                    event.notes = f'Burn Hedgey {HEDGEY_PLAN_CONTRACTS[context.tx_log.address]} NFT {plan_id} after full redemption'  # noqa: E501
                    event.counterparty = CPT_HEDGEY
                    break

        # now find the transfer of the token
        for event in context.decoded_events:
            if event.asset == token and event.amount == amount_redeemed and event.location_label == owner_address and event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Redeem {amount_redeemed} {token.symbol} from Hedgey {HEDGEY_PLAN_CONTRACTS[context.tx_log.address]} {plan_id}'  # noqa: E501
                event.counterparty = CPT_HEDGEY
                event.address = context.tx_log.address
                break
        else:
            log.error(f'Could not find token transfer event for hedgey plan redemption in {context.transaction}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_plan_events(self, context: DecoderContext, plan_type: str) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == b'\xa9d\x9a`\xc9\xbf\x95\x06R\x94\x9a}n=\xca\x99+0\xcc\xa6\x10\xef\xc7\xdfDi\xb1Z\x8fw\x8d\xdd':  # Voting Vault Created  # noqa: E501
            return self._decode_vault_creation(context=context, plan_type=plan_type)
        elif context.tx_log.topics[0] == b'\xa6\xfa\xee"FGE\x97\xb6\xde|v\xbf\x9aE\xd2VsuC\xcb\x08\x06\xe6\xe8\x05\xb5[8\xc7f?':  # PlanRedeemed  # noqa: E501
            return self._decode_plan_redeemed(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            address: (self._decode_plan_events, plan_type)
            for address, plan_type in HEDGEY_PLAN_CONTRACTS.items()
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            b'\xa8\x97>+': {
                DELEGATE_CHANGED: self._decode_delegate_plans,
            },
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_HEDGEY,
                label='Hedgey',
                image='hedgey_light.svg',
                darkmode_image='hedgey_dark.svg',
            ),
        )
