from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
    YEARN_ICON,
    YEARN_LABEL_V1,
    YEARN_LABEL_V2,
    YEARN_LABEL_V3,
    YEARN_PARTNER_TRACKER,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache, token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import (
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    YEARN_VAULTS_V3_PROTOCOL,
    CacheType,
    ChainID,
)
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

YEARN_DEPOSIT_AMOUNT_4_BYTES: Final = b'\xd0\xe3\r\xb0'
YEARN_DEPOSIT_4_BYTES: Final = b'\xb6\xb5_%'
YEARN_WITHDRAW_AMOUNT_4_BYTES: Final = b'.\x1a}M'
YEARN_WITHDRAW_4_BYTES: Final = b'<\xcf\xd6\x0b'
YEARN_V2_DEPOSIT_TOPIC: Final = b'\x90\x89\x08\t\xc6T\xf1\x1dnr\xa2\x8f\xa6\x01Iw\n\r\x11\xecl\x921\x9dl\xeb+\xb0\xa4\xea\x1a\x15'  # noqa: E501
YEARN_V3_DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
YEARN_V2_WITHDRAW_TOPIC: Final = b'\xf2y\xe6\xa1\xf5\xe3 \xcc\xa9\x115gm\x9c\xb6\xe4L\xa8\xa0\x8c\x0b\x884+\xcd\xb1\x14Oe\x11\xb5h'  # noqa: E501
YEARN_V3_WITHDRAW_TOPIC: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
TRANSFER_TOPIC: Final = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
YEARN_V2_INCREASE_DEPOSIT_TOPIC: Final = b"\xdb\x11\x01&'\xbc\xb8W\xec\x91^\x92\xe4\xc5\xa6\\\x80\t\x8e\xa7r\x90\xa7\xb3-Y\xa8\xef+>\xa4\x1b"  # noqa: E501
PROTOCOL_CPT_MAPPING: Final = {
    YEARN_VAULTS_V1_PROTOCOL: CPT_YEARN_V1,
    YEARN_VAULTS_V2_PROTOCOL: CPT_YEARN_V2,
    YEARN_VAULTS_V3_PROTOCOL: CPT_YEARN_V3,
}
YEARN_COUNTERPARTIES: TypeAlias = Literal['yearn-v1', 'yearn-v2', 'yearn-v3']


def _get_vault_token_name(vault_address: 'ChecksumEvmAddress') -> str:
    try:
        vault_token = EvmToken(ethaddress_to_identifier(vault_address))
        vault_token_name = vault_token.name
    except (UnknownAsset, WrongAssetType):
        vault_token_name = str(vault_address)

    return vault_token_name


class YearnDecoder(DecoderInterface, ReloadableDecoderMixin):
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
        self.vaults: dict[str, set[ChecksumEvmAddress]] = {
            CPT_YEARN_V1: set(),
            CPT_YEARN_V2: set(),
            CPT_YEARN_V3: set(),
        }

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db
        Returns a fresh addresses to decoders mapping.
        """
        if should_update_protocol_cache(CacheType.YEARN_VAULTS) is True:
            query_yearn_vaults(db=self.evm_inquirer.database)
        elif len(self.vaults[CPT_YEARN_V2]) != 0:
            return None  # we didn't update the globaldb cache and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = 'FROM evm_tokens WHERE protocol IN (?, ?, ?) AND chain=?'
            bindings = (
                YEARN_VAULTS_V1_PROTOCOL,
                YEARN_VAULTS_V2_PROTOCOL,
                YEARN_VAULTS_V3_PROTOCOL,
                ChainID.ETHEREUM.serialize_for_db(),
            )
            cursor.execute(f'SELECT COUNT(*) {query_body}', bindings)
            if cursor.fetchone()[0] == len(self.vaults[CPT_YEARN_V1]) + len(self.vaults[CPT_YEARN_V2]) + len(self.vaults[CPT_YEARN_V3]):  # noqa: E501
                return None  # up to date

            # we are missing new vaults. Populate the cache
            cursor.execute(f'SELECT protocol, address {query_body}', bindings)
            for row in cursor:
                self.vaults[PROTOCOL_CPT_MAPPING[row[0]]].add(string_to_evm_address(row[1]))

        return self.addresses_to_decoders()

    def _handle_withdraw_events(
            self,
            events: list['EvmEvent'],
            counterparty: YEARN_COUNTERPARTIES,
    ) -> tuple['EvmEvent | None', 'EvmEvent | None']:
        """Decode events associated with a withdrawal."""
        return_event, withdraw_event = None, None
        for event in events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = counterparty
                event.notes = f'Return {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to a {counterparty} vault'  # noqa: E501
                return_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.vaults[counterparty]
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = counterparty
                vault_token_name = _get_vault_token_name(event.address)
                event.notes = f'Withdraw {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {counterparty} vault {vault_token_name}'  # noqa: E501
                withdraw_event = event

        return return_event, withdraw_event

    def _handle_deposit_events(
            self,
            events: list['EvmEvent'],
            counterparty: YEARN_COUNTERPARTIES,
    ) -> tuple['EvmEvent | None', 'EvmEvent | None']:
        """Decode events associated with a deposit."""
        deposit_event, receive_event = None, None
        for event in events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                (event.address == YEARN_PARTNER_TRACKER or event.address in self.vaults[counterparty])  # noqa: E501
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = counterparty
                event.notes = f'Deposit {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {counterparty} vault'  # noqa: E501
                deposit_event = event
                if event.address != YEARN_PARTNER_TRACKER:
                    vault_token_name = _get_vault_token_name(event.address)
                    event.notes = f'{event.notes} {vault_token_name}'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = counterparty
                event.notes = f'Receive {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} after deposit in a {counterparty} vault'  # noqa: E501
                receive_event = event

        return deposit_event, receive_event

    def _decode_vault_event(self, context: DecoderContext) -> DecodingOutput:
        """Decode yearn v2 and v3 vault events."""
        out_event, in_event = None, None
        if context.tx_log.topics[0] == YEARN_V2_WITHDRAW_TOPIC:
            out_event, in_event = self._handle_withdraw_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V2,
            )
        elif context.tx_log.topics[0] == YEARN_V3_WITHDRAW_TOPIC:
            out_event, in_event = self._handle_withdraw_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V3,
            )
        elif context.tx_log.topics[0] == YEARN_V2_DEPOSIT_TOPIC:
            out_event, in_event = self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V2,
            )
        elif context.tx_log.topics[0] == YEARN_V3_DEPOSIT_TOPIC:
            out_event, in_event = self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V3,
            )

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )

        return DEFAULT_DECODING_OUTPUT

    def _decode_common_transfer_events_data(self, context: DecoderContext) -> tuple[YEARN_COUNTERPARTIES, 'EvmToken', 'FVal', 'ChecksumEvmAddress'] | None:  # noqa: E501
        """Decode common data from v1 and v2 events that only have transfer log events.
        Returns the counterparty, token, amount, and the vault address in a tuple,
        or None if the needed data is not found.
        """
        if (vault_address := context.transaction.to_address) is None:
            return None

        event_token = self.base.get_or_create_evm_token(context.tx_log.address)
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=event_token,
        )

        if context.transaction.to_address in self.vaults[CPT_YEARN_V1]:
            return CPT_YEARN_V1, event_token, amount, vault_address
        elif context.transaction.to_address in self.vaults[CPT_YEARN_V2]:
            return CPT_YEARN_V2, event_token, amount, vault_address

        return None

    def _maybe_get_other_transfer_event(
            self,
            context: DecoderContext,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str,
    ) -> 'EvmEvent | None':
        """Find matching event in decoded_events, to be used for event reordering.
        Returns the event or None if no matching event is found.

        The matching is too open here, but there isn't enough data available in the log
        to match anything against the asset, amount, or location_label.
        """
        for event in context.decoded_events:
            if (
                event.event_type == event_type and
                event.event_subtype == event_subtype and
                event.counterparty == counterparty
            ):
                return event

        return None

    def _decode_deposit_transfers(self, context: DecoderContext) -> DecodingOutput:
        """Decode v1 and v2 deposit events that only have transfer log events."""
        if (common_data := self._decode_common_transfer_events_data(context)) is None:
            return DEFAULT_DECODING_OUTPUT

        counterparty, event_token, amount, vault_address = common_data
        from_address = bytes_to_address(context.tx_log.topics[1])
        if from_address == ZERO_ADDRESS:
            other_event = self._maybe_get_other_transfer_event(
                context=context,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                counterparty=counterparty,
            )
            context.action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=event_token,
                amount=amount,
                to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                to_notes=f'Receive {amount} {event_token.symbol} after deposit in a {counterparty} vault',  # noqa: E501
                to_counterparty=counterparty,
                paired_events_data=([other_event], True) if other_event is not None else None,
            ))
        else:
            other_event = self._maybe_get_other_transfer_event(
                context=context,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                counterparty=counterparty,
            )
            context.action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=event_token,
                amount=amount,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                to_notes=f'Deposit {amount} {event_token.symbol} in {counterparty} vault {_get_vault_token_name(vault_address)}',  # noqa: E501
                to_counterparty=counterparty,
                paired_events_data=([other_event], False) if other_event is not None else None,
            ))

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdraw_transfers(self, context: DecoderContext) -> DecodingOutput:
        """Decode v1 and v2 withdraw events that only have transfer log events."""
        if (common_data := self._decode_common_transfer_events_data(context)) is None:
            return DEFAULT_DECODING_OUTPUT

        counterparty, vault_token, amount, vault_address = common_data
        to_address = bytes_to_address(context.tx_log.topics[2])
        if to_address == ZERO_ADDRESS:
            other_event = self._maybe_get_other_transfer_event(
                context=context,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                counterparty=counterparty,
            )
            context.action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=vault_token,
                amount=amount,
                to_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                to_notes=f'Return {amount} {vault_token.symbol} to a {counterparty} vault',
                to_counterparty=counterparty,
                paired_events_data=([other_event], False) if other_event is not None else None,
            ))
        else:
            other_event = self._maybe_get_other_transfer_event(
                context=context,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                counterparty=counterparty,
            )
            context.action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=vault_token,
                amount=amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                to_notes=f'Withdraw {amount} {vault_token.symbol} from {counterparty} vault {_get_vault_token_name(vault_address)}',  # noqa: E501
                to_counterparty=counterparty,
                paired_events_data=([other_event], True) if other_event is not None else None,
            ))

        return DEFAULT_DECODING_OUTPUT

    def _decode_v2_increase_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decode increase deposit events for yearn v2."""
        if context.tx_log.topics[0] == YEARN_V2_INCREASE_DEPOSIT_TOPIC:
            out_event, in_event = self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V2,
            )
            maybe_reshuffle_events(
                ordered_events=[out_event, in_event],
                events_list=context.decoded_events,
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return dict.fromkeys(
            (self.vaults[CPT_YEARN_V2] | self.vaults[CPT_YEARN_V3]),
            (self._decode_vault_event,),
        ) | {YEARN_PARTNER_TRACKER: (self._decode_v2_increase_deposit,)}

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            YEARN_DEPOSIT_4_BYTES: {TRANSFER_TOPIC: self._decode_deposit_transfers},
            YEARN_DEPOSIT_AMOUNT_4_BYTES: {TRANSFER_TOPIC: self._decode_deposit_transfers},
            YEARN_WITHDRAW_4_BYTES: {TRANSFER_TOPIC: self._decode_withdraw_transfers},
            YEARN_WITHDRAW_AMOUNT_4_BYTES: {TRANSFER_TOPIC: self._decode_withdraw_transfers},
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(identifier=CPT_YEARN_V1, label=YEARN_LABEL_V1, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V2, label=YEARN_LABEL_V2, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V3, label=YEARN_LABEL_V3, image=YEARN_ICON),
        )
