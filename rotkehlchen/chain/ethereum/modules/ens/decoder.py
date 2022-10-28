import logging
from multiprocessing.managers import RemoteError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from eth_utils import to_checksum_address
from rotkehlchen.accounting.structures.balance import Balance

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.names import find_ens_mappings
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import ENS_PUBLIC_RESOLVER_2, ENS_REVERSE_RESOLVER
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, Location
from rotkehlchen.utils.misc import from_wei, ts_sec_to_ms
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import CPT_ENS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ENS_REGISTRAR_CONTROLLER = string_to_evm_address('0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5')
ENS_REGISTRY_WITH_FALLBACK = string_to_evm_address('0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e')
ENS_PUBLIC_RESOLVER_2_ADDRESS = string_to_evm_address('0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41')

NAME_REGISTERED = b'\xcaj\xbb\xe9\xd7\xf1\x14"\xcbl\xa7b\x9f\xbfo\xe9\xef\xb1\xc6!\xf7\x1c\xe8\xf0+\x9f*#\x00\x97@O'  # noqa: E501
NAME_REGISTERED_ABI = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"uint256","name":"cost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRegistered","type":"event"}'  # noqa: E501
NAME_RENEWED = b'=\xa2L\x02E\x82\x93\x1c\xfa\xf8&}\x8e\xd2M\x13\xa8*\x80h\xd5\xbd3}0\xecE\xce\xa4\xe5\x06\xae'  # noqa: E501
NAME_RENEWED_ABI = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"cost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRenewed","type":"event"}'  # noqa: E501
NEW_RESOLVER = b'3W!\xb0\x18f\xdc#\xfb\xee\x8bk,{\x1e\x14\xd6\xf0\\(\xcd5\xa2\xc94#\x9f\x94\tV\x02\xa0'  # noqa: E501
TEXT_CHANGED = b'\xd8\xc93K\x1a\x9c/\x9d\xa3B\xa0\xa2\xb3&)\xc1\xa2)\xb6D]\xadx\x94\x7fgKDDJuP'
TEXT_CHANGED_ABI = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"node","type":"bytes32"},{"indexed":true,"internalType":"string","name":"indexedKey","type":"string"},{"indexed":false,"internalType":"string","name":"key","type":"string"}],"name":"TextChanged","type":"event"}'  # noqa: E501


class EnsDecoder(DecoderInterface, CustomizableDateMixin):  # lgtm[py/missing-call-to-init]
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        self.base = base_tools
        self.ethereum_manager = ethereum_manager
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_ens_registrar_event(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] == NAME_REGISTERED:
            return self._decode_name_registered(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
            )

        if tx_log.topics[0] == NAME_RENEWED:
            return self._decode_name_renewed(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
            )

        return None, []

    def _decode_name_registered(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        try:
            _, decoded_data = decode_event_data_abi_str(tx_log, NAME_REGISTERED_ABI)
        except DeserializationError as e:
            log.debug(f'Failed to decode ENS name registered event due to {str(e)}')
            return None, []

        name = decoded_data[0]
        amount = from_wei(decoded_data[1])
        expires = decoded_data[2]

        refund_from_registrar = None
        to_remove_indices = []
        for event_idx, event in enumerate(decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_ETH and event.counterparty == ENS_REGISTRAR_CONTROLLER:  # noqa: E501
                # remove ETH refund event
                refund_from_registrar = event.balance.amount
                to_remove_indices.append(event_idx)

            # Find the ETH transfer event which should be before the registered event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.counterparty == tx_log.address:  # noqa: E501
                expected_amount = amount
                if refund_from_registrar:
                    expected_amount = amount + refund_from_registrar
                if event.balance.amount != expected_amount:
                    return None, []  # registration amount did not match

                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ENS
                event.notes = f'Register ENS name {name}.eth for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501

            # Find the ENS ERC721 receive event which should be before the registered event
            if event.event_type == HistoryEventType.RECEIVE and event.asset.identifier == 'eip155:1/erc721:0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85':  # noqa: E501
                assert event.extra_data is not None, 'All ERC721 events should have extra data'
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_ENS
                event.notes = f'Receive ENS name ERC721 token for {name}.eth with id {event.extra_data["token_id"]}'  # noqa: E501

        for index in to_remove_indices:
            del decoded_events[index]

        return None, []

    def _decode_name_renewed(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        try:
            _, decoded_data = decode_event_data_abi_str(tx_log, NAME_RENEWED_ABI)
        except DeserializationError as e:
            log.debug(f'Failed to decode ENS name renewed event due to {str(e)}')
            return None, []

        name = decoded_data[0]
        amount = from_wei(decoded_data[1])
        expires = decoded_data[2]

        for event in decoded_events:
            # Find the transfer event which should be before the name renewed event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.balance.amount == amount and event.counterparty == tx_log.address:  # noqa: E501
                event.event_type = HistoryEventType.RENEW
                event.event_subtype = HistoryEventSubType.NFT
                event.counterparty = CPT_ENS
                event.notes = f'Renew ENS name {name} for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501

        return None, []

    def _decode_ens_registry_with_fallback_event(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        """Decode event where address is set for an ENS name."""
        if tx_log.topics[0] == NEW_RESOLVER:
            node = tx_log.topics[1]
            try:
                ens_name = ENS_REVERSE_RESOLVER.call(
                    manager=self.ethereum_manager,
                    method_name='name',
                    arguments=[node],
                )
            except RemoteError as e:
                log.debug(f'Failed to decode ENS set-text event due to {str(e)}')
                return None, []

            if ens_name == '':
                # By checking the contract code, I don't think it can happen. But just in case.
                return None, []

            # Not able to give more info to the user such as address that was set since
            # we don't have historical info and event doesn't provide it
            notes = f'Set ENS address for {ens_name}'
            decoded_events.append(HistoryBaseEntry(
                event_identifier=transaction.tx_hash,
                sequence_index=self.base.get_sequence_index(tx_log),
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.BLOCKCHAIN,
                location_label=transaction.from_address,
                asset=A_ETH,
                balance=Balance(),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                counterparty=CPT_ENS,
            ))
        return None, []

    def _decode_ens_public_resolver_2_events(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        """Decode event where a text property (discord, telegram, etc.) is set for an ENS name."""
        if tx_log.topics[0] == TEXT_CHANGED:
            try:
                _, decoded_data = decode_event_data_abi_str(tx_log, TEXT_CHANGED_ABI)
                changed_key = decoded_data[0]
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'

                log.debug(f'Failed to decode ENS set-text event due to {msg}')
                return None, []

            node = tx_log.topics[1]
            try:
                address = ENS_PUBLIC_RESOLVER_2.call(
                    manager=self.ethereum_manager,
                    method_name='addr',
                    arguments=[node],
                )
                address = to_checksum_address(address)
                ens_mapping = find_ens_mappings(
                    ethereum_manager=self.ethereum_manager,
                    addresses=[address],
                    ignore_cache=False,
                )
            except RemoteError as e:
                log.debug(f'Failed to decode ENS set-text event due to {str(e)}')
                return None, []

            if address in ens_mapping:
                name_to_show = ens_mapping[address]
            else:
                name_to_show = address

            notes = f'Set ENS {changed_key} attribute for {name_to_show}'
            decoded_events.append(HistoryBaseEntry(
                event_identifier=transaction.tx_hash,
                sequence_index=self.base.get_sequence_index(tx_log),
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.BLOCKCHAIN,
                location_label=transaction.from_address,
                asset=A_ETH,
                balance=Balance(),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                counterparty=CPT_ENS,
            ))
        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            ENS_REGISTRAR_CONTROLLER: (self._decode_ens_registrar_event,),
            ENS_REGISTRY_WITH_FALLBACK: (self._decode_ens_registry_with_fallback_event,),
            ENS_PUBLIC_RESOLVER_2_ADDRESS: (self._decode_ens_public_resolver_2_events,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_ENS]
