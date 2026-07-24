import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType
from rotkehlchen.utils.misc import bytes_to_address

from .cache import (
    parse_creation_log,
    query_yearn_vesting_data,
    read_yearn_vesting_data_from_cache,
)
from .constants import (
    CLAIM,
    CPT_YEARN_VESTING,
    DISOWNED,
    ERC4626_VESTING_ESCROW_CREATED,
    FACTORIES,
    FACTORY_DEPLOYMENTS,
    PERMISSIONLESS_CLAIMS_SET,
    PRINCIPAL_CLAIM,
    REVOCATION_RENOUNCED,
    REVOKED_V3,
    REVOKED_V4_ERC4626,
    REVOKED_V4_TOKEN,
    RUG_PULL,
    SET_OPEN_CLAIM,
    TOKEN_VESTING_ESCROW_CREATED,
    VESTING_ESCROW_CREATED,
    VESTING_ESCROW_CREATED_V3,
    YEARN_VESTING_ICON,
    YEARN_VESTING_LABEL,
    YIELD_CLAIM,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

    from .constants import FactoryDeployment
    from .structures import VestingEscrowData

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CREATION_TOPIC_TO_EVENT = {
    VESTING_ESCROW_CREATED: 'VestingEscrowCreated',
    VESTING_ESCROW_CREATED_V3: 'VestingEscrowCreated',
    TOKEN_VESTING_ESCROW_CREATED: 'TokenVestingEscrowCreated',
    ERC4626_VESTING_ESCROW_CREATED: 'ERC4626VestingEscrowCreated',
}


class YearnVestingDecoder(EvmDecoderInterface, ReloadableDecoderMixin):
    def __init__(
            self,
            ethereum_inquirer: EthereumInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.escrows = read_yearn_vesting_data_from_cache()

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        if should_update_protocol_cache(
            userdb=self.base.database,
            cache_key=CacheType.YEARN_VESTING_ESCROWS,
        ):
            self.node_inquirer.ensure_cache_data_is_updated(
                cache_type=CacheType.YEARN_VESTING_ESCROWS,
                query_method=query_yearn_vesting_data,
            )

        cached_escrows = read_yearn_vesting_data_from_cache()
        new_addresses = cached_escrows.keys() - self.escrows.keys()
        self.escrows = cached_escrows
        if len(new_addresses) == 0:
            return None
        return {
            address: (self._decode_escrow_event, cached_escrows[address])
            for address in new_addresses
        }

    def _creation_deployment(self, context: DecoderContext) -> FactoryDeployment | None:
        event_name = CREATION_TOPIC_TO_EVENT.get(context.tx_log.topics[0])
        if event_name is None:
            return None
        return next((
            deployment for deployment in FACTORY_DEPLOYMENTS
            if (
                deployment.address == context.tx_log.address and
                deployment.event_name == event_name
            )
        ), None)

    def _transform_transfer(
            self,
            context: DecoderContext,
            token: EvmToken,
            raw_amount: int,
            location_label: ChecksumEvmAddress,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            notes: str,
            address: ChecksumEvmAddress,
    ) -> EvmEvent | None:
        amount = token_normalized_value(token_amount=raw_amount, token=token)
        for event in context.decoded_events:
            if (
                    event.event_type in {HistoryEventType.SPEND, HistoryEventType.RECEIVE} and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.amount == amount and
                    event.location_label == location_label
            ):
                event.event_type = event_type
                event.event_subtype = event_subtype
                event.counterparty = CPT_YEARN_VESTING
                event.notes = notes
                event.address = address
                return event
        return None

    def _decode_factory_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if (deployment := self._creation_deployment(context)) is None:
            return DEFAULT_EVM_DECODING_OUTPUT
        try:
            position = parse_creation_log(
                deployment=deployment,
                topics=context.tx_log.topics,
                data=context.tx_log.data,
            )
        except (IndexError, ValueError) as e:
            log.error('Failed to decode Yearn vesting factory event due to %s', e)
            return DEFAULT_EVM_DECODING_OUTPUT

        funding_token = self.base.get_or_create_evm_token(position.token)
        funding_amount = token_normalized_value(
            token_amount=position.funded_amount,
            token=funding_token,
        )
        if self.base.is_tracked(position.funder):
            self._transform_transfer(
                context=context,
                token=funding_token,
                raw_amount=position.funded_amount,
                location_label=position.funder,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                notes=f'Fund {funding_amount} {funding_token.symbol} in a Yearn vesting escrow for {position.recipient}',  # noqa: E501
                address=position.escrow,
            )

        events = []
        if self.base.is_tracked(position.recipient):
            grant_token_address = (
                position.token
                if position.kind == 'token'
                else position.asset_token
            )
            if grant_token_address is not None:
                grant_token = self.base.get_or_create_evm_token(grant_token_address)
                grant_amount = token_normalized_value(
                    token_amount=position.amount,
                    token=grant_token,
                )
                events.append(self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.GRANT,
                    asset=grant_token,
                    amount=grant_amount,
                    location_label=position.recipient,
                    notes=f'Receive a grant of {grant_amount} {grant_token.symbol} in a Yearn vesting escrow',  # noqa: E501
                    counterparty=CPT_YEARN_VESTING,
                    address=position.escrow,
                ))

        return EvmDecodingOutput(
            events=events,
            reload_decoders={'YearnVesting'},
        )

    def _decode_claim(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        receiver = bytes_to_address(context.tx_log.topics[1])
        raw_amount = int.from_bytes(context.tx_log.data[:32])
        token = self.base.get_or_create_evm_token(position.token)
        amount = token_normalized_value(token_amount=raw_amount, token=token)
        self._transform_transfer(
            context=context,
            token=token,
            raw_amount=raw_amount,
            location_label=receiver,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            notes=f'Claim {amount} {token.symbol} from a Yearn vesting escrow',
            address=position.escrow,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_principal_claim(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        receiver = bytes_to_address(context.tx_log.topics[1])
        raw_principal = int.from_bytes(context.tx_log.data[:32])
        raw_shares = int.from_bytes(context.tx_log.data[32:64])
        vault = self.base.get_or_create_evm_token(position.token)
        if position.asset_token is None:
            log.error('Missing asset token for ERC-4626 vesting escrow %s', position.escrow)
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_token(position.asset_token)
        shares = token_normalized_value(token_amount=raw_shares, token=vault)
        principal = token_normalized_value(token_amount=raw_principal, token=asset)
        event = self._transform_transfer(
            context=context,
            token=vault,
            raw_amount=raw_shares,
            location_label=receiver,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            notes=f'Claim {shares} {vault.symbol} representing {principal} {asset.symbol} principal from a Yearn vesting escrow',  # noqa: E501
            address=position.escrow,
        )
        if event is not None:
            event.extra_data = {
                'principal_asset': asset.identifier,
                'principal_amount': str(principal),
            }
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_yield_claim(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        recipient = bytes_to_address(context.tx_log.topics[1])
        raw_shares = int.from_bytes(context.tx_log.data[:32])
        vault = self.base.get_or_create_evm_token(position.token)
        shares = token_normalized_value(token_amount=raw_shares, token=vault)
        self._transform_transfer(
            context=context,
            token=vault,
            raw_amount=raw_shares,
            location_label=recipient,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            notes=f'Claim {shares} {vault.symbol} as yield from a Yearn vesting escrow',
            address=position.escrow,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_revocation(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        topic = context.tx_log.topics[0]
        if topic == RUG_PULL:
            recipient = bytes_to_address(context.tx_log.data[:32])
            raw_unvested = raw_transfer = int.from_bytes(context.tx_log.data[32:64])
            receiver = None
        elif topic == REVOKED_V3:
            recipient = bytes_to_address(context.tx_log.data[:32])
            raw_unvested = raw_transfer = int.from_bytes(context.tx_log.data[64:96])
            receiver = None
        else:
            recipient = bytes_to_address(context.tx_log.topics[1])
            receiver = bytes_to_address(context.tx_log.topics[3])
            raw_unvested = int.from_bytes(context.tx_log.data[:32])
            raw_transfer = (
                int.from_bytes(context.tx_log.data[32:64])
                if topic == REVOKED_V4_ERC4626
                else raw_unvested
            )

        transfer_token = self.base.get_or_create_evm_token(position.token)
        transfer_amount = token_normalized_value(
            token_amount=raw_transfer,
            token=transfer_token,
        )
        if receiver is not None and self.base.is_tracked(receiver):
            self._transform_transfer(
                context=context,
                token=transfer_token,
                raw_amount=raw_transfer,
                location_label=receiver,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                notes=f'Withdraw {transfer_amount} {transfer_token.symbol} after revoking a Yearn vesting escrow',  # noqa: E501
                address=position.escrow,
            )
        elif receiver is None:
            for event in context.decoded_events:
                if (
                        event.event_type == HistoryEventType.RECEIVE and
                        event.event_subtype == HistoryEventSubType.NONE and
                        event.asset == transfer_token and
                        event.amount == transfer_amount and
                        event.address == position.escrow
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                    event.counterparty = CPT_YEARN_VESTING
                    event.notes = f'Withdraw {transfer_amount} {transfer_token.symbol} after revoking a Yearn vesting escrow'  # noqa: E501
                    if event.location_label is not None:
                        receiver = string_to_evm_address(event.location_label)
                    break

        events = []
        if (
            raw_unvested != 0 and
            self.base.is_tracked(recipient) and
            recipient != receiver
        ):
            loss_token_address = (
                position.token
                if position.kind == 'token'
                else position.asset_token
            )
            if loss_token_address is not None:
                loss_token = self.base.get_or_create_evm_token(loss_token_address)
                loss_amount = token_normalized_value(
                    token_amount=raw_unvested,
                    token=loss_token,
                )
                events.append(self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.CLAWBACK,
                    asset=loss_token,
                    amount=loss_amount,
                    location_label=recipient,
                    notes=f'Claw back {loss_amount} {loss_token.symbol} of unvested principal from a Yearn vesting escrow',  # noqa: E501
                    counterparty=CPT_YEARN_VESTING,
                    address=position.escrow,
                ))

        return EvmDecodingOutput(events=events)

    def _decode_setting(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        topic = context.tx_log.topics[0]
        if topic in {DISOWNED, REVOCATION_RENOUNCED}:
            actor = (
                bytes_to_address(context.tx_log.data[:32])
                if topic == DISOWNED
                else bytes_to_address(context.tx_log.topics[1])
            )
            location_label = actor
            notes = 'Renounce revocation of a Yearn vesting escrow'
        else:
            location_label = position.recipient
            enabled = int.from_bytes(context.tx_log.data[:32]) != 0
            notes = f'{"Enable" if enabled else "Disable"} permissionless Yearn vesting claims'

        if not self.base.is_tracked(location_label):
            return DEFAULT_EVM_DECODING_OUTPUT
        token = self.base.get_or_create_evm_token(position.token)
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=token,
            amount=ZERO,
            location_label=location_label,
            notes=notes,
            counterparty=CPT_YEARN_VESTING,
            address=position.escrow,
        )])

    def _decode_escrow_event(
            self,
            context: DecoderContext,
            position: VestingEscrowData,
    ) -> EvmDecodingOutput:
        topic = context.tx_log.topics[0]
        if topic == CLAIM:
            return self._decode_claim(context=context, position=position)
        if topic == PRINCIPAL_CLAIM and position.kind == 'erc4626':
            return self._decode_principal_claim(context=context, position=position)
        if topic == YIELD_CLAIM and position.kind == 'erc4626':
            return self._decode_yield_claim(context=context, position=position)
        if topic in {RUG_PULL, REVOKED_V3, REVOKED_V4_TOKEN, REVOKED_V4_ERC4626}:
            return self._decode_revocation(context=context, position=position)
        if topic in {
            DISOWNED,
            SET_OPEN_CLAIM,
            REVOCATION_RENOUNCED,
            PERMISSIONLESS_CLAIMS_SET,
        }:
            return self._decode_setting(context=context, position=position)
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(FACTORIES, (self._decode_factory_event,)) | {
            address: (self._decode_escrow_event, position)
            for address, position in self.escrows.items()
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys((*FACTORIES, *self.escrows), CPT_YEARN_VESTING)

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_YEARN_VESTING,
            label=YEARN_VESTING_LABEL,
            image=YEARN_VESTING_ICON,
        ),)
