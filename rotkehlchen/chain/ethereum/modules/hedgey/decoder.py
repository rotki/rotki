import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.constants import DELEGATE_CHANGED
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_HEDGEY, VOTING_TOKEN_LOCKUPS, VOTING_TOKEN_LOCKUPS_ABI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MIGRATED = b'\x92\x8f\xd5S\x13$\xee\x87\xd7l\xc50}\xc3u\x80\x17M\xa7k\x85\xcdTm\xa61\xb2g\x0b\xc2f\xb5'  # noqa: E501


class HedgeyDecoder(DecoderInterface):

    def _decode_delegate_changed(
            self,
            tx_log: 'EvmTxReceiptLog',
            transaction: 'EvmTransaction',
            owner_address: 'ChecksumEvmAddress',
            plan_name: str,
    ) -> DecodingOutput:
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
        return DecodingOutput(events=[event])

    def _decode_vault_creation(self, context: DecoderContext) -> DecodingOutput:
        vault_address = bytes_to_address(context.tx_log.data[:32])
        plan_id = int.from_bytes(context.tx_log.topics[1])
        owner_address = deserialize_evm_address(self.evm_inquirer.call_contract(
            contract_address=VOTING_TOKEN_LOCKUPS,
            abi=VOTING_TOKEN_LOCKUPS_ABI,
            method_name='ownerOf',
            arguments=[plan_id],
        ))
        if not self.base.is_tracked(owner_address):
            return DEFAULT_DECODING_OUTPUT

        # now find the log of the token delegation
        for tx_log in context.all_logs:
            if tx_log.topics[0] == DELEGATE_CHANGED and bytes_to_address(tx_log.topics[1]) == vault_address:  # noqa: E501
                return self._decode_delegate_changed(
                    tx_log=tx_log,
                    transaction=context.transaction,
                    owner_address=owner_address,
                    plan_name=f'Hedgey token lockup {plan_id}',
                )

        log.error(f'Did not find a delegation event in {context.transaction} logs')
        return DEFAULT_DECODING_OUTPUT

    def _decode_delegate_plans(self, context: DecoderContext) -> DecodingOutput:
        """Decode direct delegate change after voting token lockup creation.
        Will only work if called by an EoA"""
        if not self.base.is_tracked(owner_address := context.transaction.from_address):
            return DEFAULT_DECODING_OUTPUT

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

    def _decode_plan_redeemed(self, context: DecoderContext) -> DecodingOutput:
        plan_id = int.from_bytes(context.tx_log.topics[1])
        contract = EvmContract(address=VOTING_TOKEN_LOCKUPS, abi=VOTING_TOKEN_LOCKUPS_ABI)
        calls = [
            (contract.address, contract.encode(method_name='plans', arguments=[plan_id])),
            (contract.address, contract.encode(method_name='ownerOf', arguments=[plan_id])),
        ]
        output = self.evm_inquirer.multicall(calls=calls)
        token_address = deserialize_evm_address(
            contract.decode(result=output[0], method_name='plans', arguments=[plan_id])[0],
        )
        owner_address = deserialize_evm_address(
            contract.decode(result=output[1], method_name='ownerOf', arguments=[plan_id])[0],
        )
        if not self.base.is_tracked(owner_address):
            return DEFAULT_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(address=token_address)
        amount_redeemed = token_normalized_value(token_amount=int.from_bytes(context.tx_log.data[:32]), token=token)  # noqa: E501
        # now find the transfer of the token
        for event in context.decoded_events:
            if event.asset == token and event.amount == amount_redeemed and event.location_label == owner_address and event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Redeem {amount_redeemed} {token.symbol} from Hedgey token lockup {plan_id}'  # noqa: E501
                event.counterparty = CPT_HEDGEY
                event.address = VOTING_TOKEN_LOCKUPS
                break
        else:
            log.error(f'Could not find token transfer event for hedgey plan redemption in {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_lockup_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == b'\xa9d\x9a`\xc9\xbf\x95\x06R\x94\x9a}n=\xca\x99+0\xcc\xa6\x10\xef\xc7\xdfDi\xb1Z\x8fw\x8d\xdd':  # Voting Vault Created  # noqa: E501
            return self._decode_vault_creation(context)
        elif context.tx_log.topics[0] == b'\xa6\xfa\xee"FGE\x97\xb6\xde|v\xbf\x9aE\xd2VsuC\xcb\x08\x06\xe6\xe8\x05\xb5[8\xc7f?':  # PlanRedeemed  # noqa: E501
            return self._decode_plan_redeemed(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {VOTING_TOKEN_LOCKUPS: (self._decode_lockup_events,)}

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
                image='hedgey_dark.svg',
                darkmode_image='hedgey_light.svg',
            ),
        )
