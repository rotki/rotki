import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, cast

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
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
from rotkehlchen.chain.evm.constants import (
    DEPOSIT_TOPIC,
    STAKE_TOPIC,
    WITHDRAW_TOPIC_V3,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

YEARN_DEPOSIT_4_BYTES: Final = b'\x83@\xf5I'
YEARN_DEPOSIT_NO_LOGS_4_BYTES: Final = b'\xb6\xb5_%'
YEARN_V2_INCREASE_DEPOSIT_TOPIC: Final = b"\xdb\x11\x01&'\xbc\xb8W\xec\x91^\x92\xe4\xc5\xa6\\\x80\t\x8e\xa7r\x90\xa7\xb3-Y\xa8\xef+>\xa4\x1b"  # noqa: E501
YEARN_COUNTERPARTIES: TypeAlias = Literal['yearn-v1', 'yearn-v2', 'yearn-v3']


def _get_vault_token_name(vault_address: 'ChecksumEvmAddress') -> str:
    try:
        vault_token = EvmToken(ethaddress_to_identifier(vault_address))
        vault_token_name = vault_token.name.strip()  # need strip since some names have whitespaces
    except (UnknownAsset, WrongAssetType):
        vault_token_name = str(vault_address)

    return vault_token_name


class YearnDecoder(EvmDecoderInterface, ReloadableDecoderMixin):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
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
        if should_update_protocol_cache(self.base.database, CacheType.YEARN_VAULTS) is True:
            query_yearn_vaults(
                db=self.node_inquirer.database,
                ethereum_inquirer=cast('EthereumInquirer', self.node_inquirer),
            )
        elif len(self.vaults[CPT_YEARN_V2]) != 0:
            return None  # we didn't update the globaldb cache and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = 'FROM evm_tokens WHERE protocol IN (?, ?, ?) AND chain=?'
            bindings = (
                CPT_YEARN_V1,
                CPT_YEARN_V2,
                CPT_YEARN_V3,
                ChainID.ETHEREUM.serialize_for_db(),
            )
            cursor.execute(f'SELECT COUNT(*) {query_body}', bindings)
            if cursor.fetchone()[0] == len(self.vaults[CPT_YEARN_V1]) + len(self.vaults[CPT_YEARN_V2]) + len(self.vaults[CPT_YEARN_V3]):  # noqa: E501
                return None  # up to date

            # we are missing new vaults. Populate the cache
            cursor.execute(f'SELECT protocol, address {query_body}', bindings)
            for row in cursor:
                self.vaults[row[0]].add(string_to_evm_address(row[1]))

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
                event.notes = f'Return {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to a {counterparty} vault'  # noqa: E501
                return_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.vaults[counterparty]
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = counterparty
                vault_token_name = _get_vault_token_name(event.address)
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {counterparty} vault {vault_token_name}'  # noqa: E501
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
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = counterparty
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {counterparty} vault'  # noqa: E501
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
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} after deposit in a {counterparty} vault'  # noqa: E501
                receive_event = event

        return deposit_event, receive_event

    def _handle_transfer_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode v1 and v2 vault events that only have transfer log events."""
        if not self.base.any_tracked((
                (from_address := bytes_to_address(context.tx_log.topics[1])),
                (to_address := bytes_to_address(context.tx_log.topics[2])),
        )):
            return DEFAULT_EVM_DECODING_OUTPUT  # can happen as other transfers of token may be hit in same transaction  # noqa: E501

        counterparty = CPT_YEARN_V1 if (vault_address := context.tx_log.address) in self.vaults[CPT_YEARN_V1] else CPT_YEARN_V2  # noqa: E501

        # For some deposits one of the transfers is already decoded and the action items
        # can't modify it, so it needs to be found in decoded_events and modified there.
        if context.transaction.input_data.startswith(YEARN_DEPOSIT_NO_LOGS_4_BYTES):
            self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=counterparty,  # type: ignore  # will always be either CPT_YEARN_V1 or CPT_YEARN_V2
            )

        vault_token = self.base.get_or_create_evm_token(vault_address)
        if vault_token.underlying_tokens is not None and len(vault_token.underlying_tokens) > 0:
            underlying_vault_token = self.base.get_or_create_evm_token(vault_token.underlying_tokens[0].address)  # noqa: E501
        else:
            log.error(f'Failed to find underlying token for yearn vault {vault_address}')
            return DEFAULT_EVM_DECODING_OUTPUT

        vault_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=vault_token,
        )

        for tx_log in context.all_logs:
            if (
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    tx_log != context.tx_log and
                    tx_log.address == underlying_vault_token.evm_address and
                    (  # either from/to must be tracked to not hit other transfers of token in transaction  # noqa: E501
                        self.base.is_tracked(bytes_to_address(tx_log.topics[1])) or
                        self.base.is_tracked(bytes_to_address(tx_log.topics[2]))
                    )

            ):
                underlying_transfer_tx_log = tx_log
                break
        else:
            log.error(f'Failed to find transfer of yearn vault underlying token for {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        underlying_amount = token_normalized_value(
            token_amount=int.from_bytes(underlying_transfer_tx_log.data[0:32]),
            token=underlying_vault_token,
        )

        if from_address == ZERO_ADDRESS:  # deposit
            return EvmDecodingOutput(action_items=[
                ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.SPEND,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=underlying_vault_token,
                    amount=underlying_amount,
                    to_event_type=HistoryEventType.DEPOSIT,
                    to_event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                    to_notes=f'Deposit {underlying_amount} {underlying_vault_token.symbol} in {counterparty} vault {_get_vault_token_name(vault_token.evm_address)}',  # noqa: E501
                    to_counterparty=counterparty,
                ), ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=vault_token,
                    amount=vault_amount,
                    to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    to_notes=f'Receive {vault_amount} {vault_token.symbol} after deposit in a {counterparty} vault',  # noqa: E501
                    to_counterparty=counterparty,
                ),
            ])
        elif to_address == ZERO_ADDRESS:  # withdraw
            return EvmDecodingOutput(action_items=[
                ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.SPEND,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=vault_token,
                    amount=vault_amount,
                    to_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                    to_notes=f'Return {vault_amount} {vault_token.symbol} to a {counterparty} vault',  # noqa: E501
                    to_counterparty=counterparty,
                ), ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=underlying_vault_token,
                    amount=underlying_amount,
                    to_event_type=HistoryEventType.WITHDRAWAL,
                    to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                    to_notes=f'Withdraw {underlying_amount} {underlying_vault_token.symbol} from {counterparty} vault {_get_vault_token_name(vault_token.evm_address)}',  # noqa: E501
                    to_counterparty=counterparty,
                ),
            ])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vault_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode yearn v1 and v2 vault events."""
        if context.tx_log.topics[0] == STAKE_TOPIC:
            out_event, in_event = self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V2,
            )
            maybe_reshuffle_events(
                ordered_events=[out_event, in_event],
                events_list=context.decoded_events,
            )
        elif (
            context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            not context.transaction.input_data.startswith(YEARN_DEPOSIT_4_BYTES)  # decoded via STAKE_TOPIC above  # noqa: E501
        ):
            return self._handle_transfer_events(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_v3_vault_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode yearn v3 vault events."""
        out_event, in_event, is_deposit = None, None, False
        if context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            out_event, in_event = self._handle_withdraw_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V3,
            )
        elif context.tx_log.topics[0] == DEPOSIT_TOPIC:
            out_event, in_event = self._handle_deposit_events(
                events=context.decoded_events,
                counterparty=CPT_YEARN_V3,
            )
            is_deposit = True
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if out_event is None or in_event is None:
            log.error(f'Failed to find both out and in events for yearn v3 vault transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # Special case for Curve Savings - it's actually a yearn v3 vault, so we can simply update
        # the events here and avoid needing a separate Curve Savings decoder.
        if (vault_address := context.tx_log.address) == string_to_evm_address('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'):  # scrvUSD token  # noqa: E501
            out_event.counterparty = in_event.counterparty = CPT_CURVE
            out_event.address = in_event.address = vault_address
            if is_deposit:
                out_event.notes = f'Deposit {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in Curve Savings'  # noqa: E501
                in_event.notes = f'Receive {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} after deposit in Curve Savings'  # noqa: E501
            else:
                out_event.notes = f'Return {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} to Curve Savings'  # noqa: E501
                in_event.notes = f'Withdraw {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} from Curve Savings'  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_v2_increase_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
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

        return DEFAULT_EVM_DECODING_OUTPUT

    def _reorder_events(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Reorder events for v1 and v2 vault transactions decoded by _handle_transfer_events."""
        out_event, in_event = None, None
        for event in decoded_events:
            if event.counterparty not in {CPT_YEARN_V1, CPT_YEARN_V2, CPT_YEARN_V3}:
                continue

            if (
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.RETURN_WRAPPED) or  # noqa: E501
                (event.event_type == HistoryEventType.DEPOSIT and event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED)  # noqa: E501
            ):
                out_event = event
            elif (
                (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED) or  # noqa: E501
                (event.event_type == HistoryEventType.WITHDRAWAL and event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED)  # noqa: E501
            ):
                in_event = event

        if out_event is None or in_event is None:
            log.error(f'Failed to find both out and in events for yearn vault transaction {transaction}')  # noqa: E501
            return decoded_events

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return dict.fromkeys(
            (self.vaults[CPT_YEARN_V1] | self.vaults[CPT_YEARN_V2]),
            (self._decode_vault_event,),
        ) | dict.fromkeys(
            self.vaults[CPT_YEARN_V3],
            (self._decode_v3_vault_event,),
        ) | {YEARN_PARTNER_TRACKER: (self._decode_v2_increase_deposit,)}

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return (
            dict.fromkeys(self.vaults[CPT_YEARN_V1], CPT_YEARN_V1) |
            dict.fromkeys(self.vaults[CPT_YEARN_V2], CPT_YEARN_V2)
        )

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_YEARN_V1: [(0, self._reorder_events)],
            CPT_YEARN_V2: [(0, self._reorder_events)],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(identifier=CPT_YEARN_V1, label=YEARN_LABEL_V1, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V2, label=YEARN_LABEL_V2, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V3, label=YEARN_LABEL_V3, image=YEARN_ICON),
        )
