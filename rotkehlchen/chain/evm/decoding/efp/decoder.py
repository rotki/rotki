import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Final

from eth_utils import to_checksum_address

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_EFP

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

LIST_OP_TOPIC: Final = b"\xb0gc\x0e9\x08\xf1f\x06\x9cwvbP\xc5SAN'E\xe7B\xa5b\xd53\xf2\x97D\xa9\x1as"  # noqa: E501


class EfpCommonDecoder(EvmDecoderInterface, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            list_records_contract: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.list_records_contract = list_records_contract

    def _get_address_for_slot(self, slot: int) -> 'ChecksumEvmAddress | None':
        """Get address associated with the specified slot.
        Returns an address or None if unable to match an address to this slot."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (address := globaldb_get_unique_cache_value(
                    cursor=cursor,
                    key_parts=(CacheType.EFP_SLOT_ADDRESS, (chain := str(self.node_inquirer.chain_id)), str(slot)),  # noqa: E501
            )) is not None:
                return string_to_evm_address(address)

        try:
            if (address := to_checksum_address(self.node_inquirer.contracts.contract(self.list_records_contract).call(  # noqa: E501
                node_inquirer=self.node_inquirer,
                method_name='getListUser',
                arguments=[slot],
            ))) == ZERO_ADDRESS:
                log.error(f'Failed to retrieve address for EFP slot {slot} on {chain}')
                return None
        except RemoteError as e:
            log.error(f'Failed to retrieve address for EFP slot {slot} on {chain} due to {e!s}')
            return None

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.EFP_SLOT_ADDRESS, chain, str(slot)),
                value=address,
            )
        return address

    def _decode_list_op_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode EFP list operation events."""
        if context.tx_log.topics[0] != LIST_OP_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (address := self._get_address_for_slot(
                slot=int.from_bytes(context.tx_log.topics[1]),
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(address):
            log.debug(
                f'Skipping EFP list op event for untracked address {address} '
                f'in transaction {context.transaction}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        # Decode list operation data. See https://docs.ethfollow.xyz/design/list-ops/
        data = context.tx_log.data[64:]
        op_version = int.from_bytes(data[0:1])
        op_code = int.from_bytes(data[1:2])
        record_version = int.from_bytes(data[2:3])
        record_type = int.from_bytes(data[3:4])
        if op_version != 1 or op_code not in [1, 2, 3, 4] or record_version != 1 or record_type != 1:  # noqa: E501
            log.error(
                f'Found unsupported EFP list operation in transaction {context.transaction}. '
                f'OpVersion: {op_version}, OpCode: {op_code}, '
                f'RecordVersion: {record_version}, RecordType: {record_type}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        followed_address = bytes_to_address(b'\x00' * 12 + data[4:24])
        if op_code == 1:  # Follow
            notes = f'Follow {followed_address} on EFP'
        elif op_code == 2:  # Unfollow
            notes = f'Unfollow {followed_address} on EFP'
        elif op_code == 3:  # Tag
            tag = data[24:].rstrip(b'\x00').decode()
            notes = f'Add {tag} tag to {followed_address} on EFP'
        else:  # op_code == 4  # Untag
            tag = data[24:].rstrip(b'\x00').decode()
            notes = f'Remove {tag} tag from {followed_address} on EFP'

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=address,
            notes=notes,
            counterparty=CPT_EFP,
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.list_records_contract: (self._decode_list_op_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_EFP,
            label='EFP',
            image='efp.svg',
        ),)
