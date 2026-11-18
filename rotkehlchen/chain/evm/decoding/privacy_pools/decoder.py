from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.ethereum.modules.oneinch.liquidity.constants import (
    DEPOSITED as V2_PP_ROUTER_DEPOSITED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_PRIVACY_POOLS,
    ENTRYPOINT_DEPOSITED_TOPIC,
    PRIVACY_POOLS_CPT_DETAILS,
    PRIVACY_POOLS_LABEL,
    RAGEQUIT_TOPIC,
    V2_ENTRYPOINT,
    V2_POOL_RAGEQUIT_TOPIC,
    V2_POOL_VAULT,
    V2_PP_ROUTER_WITHDRAWN_TOPIC,
    V2_RELAY,
    V2_RELAYED_BATCH_TOPIC,
    V2_RELAYED_TOPIC,
    WITHDRAWAL_RELAYED_TOPIC,
    PrivacyPoolsDeployment,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class PrivacyPoolsDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            deployment: PrivacyPoolsDeployment,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.deployment = deployment

    def _get_pool_asset(
            self,
            pool_address: ChecksumEvmAddress,
            context: DecoderContext,
            amount_raw: int,
    ) -> CryptoAsset | None:
        if pool_address == self.deployment.native_pool:
            return self.node_inquirer.native_token

        if (token_address := self.deployment.token_pools.get(pool_address)) is not None:
            return self.base.get_or_create_evm_token(token_address)

        for log in context.all_logs:
            if (
                log.log_index < context.tx_log.log_index and
                len(log.topics) == 3 and
                log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(log.topics[1]) == self.deployment.entrypoint and
                bytes_to_address(log.topics[2]) == pool_address and
                int.from_bytes(log.data[:32]) == amount_raw
            ):
                return self.base.get_or_create_evm_token(log.address)

        return None

    def _apply_deposit(
            self,
            context: DecoderContext,
            depositor: ChecksumEvmAddress,
            contract_address: ChecksumEvmAddress,
            asset: CryptoAsset,
            deposited_amount: FVal,
            fee_amount: FVal | None = None,
            handle_refund: bool = False,
    ) -> EvmDecodingOutput:
        min_spend_amount = deposited_amount + (fee_amount if fee_amount is not None else ZERO)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == depositor and
                event.address == contract_address and
                event.asset == asset and
                event.amount >= min_spend_amount
            ):
                actual_fee = fee_amount if fee_amount is not None else event.amount - deposited_amount  # noqa: E501
                if handle_refund and (refund_amount := event.amount - (deposited_amount + actual_fee)) > ZERO:  # noqa: E501
                    for other_event in context.decoded_events:
                        if (
                            other_event.event_type == HistoryEventType.RECEIVE and
                            other_event.event_subtype == HistoryEventSubType.NONE and
                            other_event.location_label == depositor and
                            other_event.address == contract_address and
                            other_event.asset == asset and
                            other_event.amount == refund_amount
                        ):
                            context.decoded_events.remove(other_event)
                            break

                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                event.amount = deposited_amount
                event.counterparty = CPT_PRIVACY_POOLS
                event.notes = f'Deposit {deposited_amount} {asset.symbol} in {PRIVACY_POOLS_LABEL}'
                new_events: list[EvmEvent] = []
                if actual_fee > ZERO:
                    new_events.append(self.base.make_event_next_index(
                        tx_ref=context.transaction.tx_hash,
                        timestamp=context.transaction.timestamp,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=asset,
                        amount=actual_fee,
                        location_label=depositor,
                        notes=f'Spend {actual_fee} {asset.symbol} as a {PRIVACY_POOLS_LABEL} deposit fee',  # noqa: E501
                        counterparty=CPT_PRIVACY_POOLS,
                        address=contract_address,
                    ))
                return EvmDecodingOutput(events=new_events)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _apply_withdrawal(
            self,
            context: DecoderContext,
            recipient: ChecksumEvmAddress,
            contract_address: ChecksumEvmAddress,
            asset: CryptoAsset,
            withdrawn_amount: FVal,
            fee_amount: FVal,
            expected_receive_amount: FVal,
            match_any_sender: bool = False,
    ) -> EvmDecodingOutput:
        withdrawal_notes = f'Withdraw {withdrawn_amount} {asset.symbol} from {PRIVACY_POOLS_LABEL}'
        fee_notes = f'Spend {fee_amount} {asset.symbol} as a {PRIVACY_POOLS_LABEL} withdrawal fee'

        for event in context.decoded_events:
            if (
                event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.WITHDRAWAL) and
                event.location_label == recipient and
                (match_any_sender or event.address == contract_address) and
                event.asset == asset and
                event.amount == expected_receive_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.amount = withdrawn_amount
                event.counterparty = CPT_PRIVACY_POOLS
                event.notes = withdrawal_notes
                event.address = contract_address
                new_events: list[EvmEvent] = []
                if fee_amount > ZERO:
                    new_events.append(self.base.make_event_next_index(
                        tx_ref=context.transaction.tx_hash,
                        timestamp=context.transaction.timestamp,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=asset,
                        amount=fee_amount,
                        location_label=recipient,
                        notes=fee_notes,
                        counterparty=CPT_PRIVACY_POOLS,
                        address=contract_address,
                    ))
                return EvmDecodingOutput(events=new_events)

        events = [self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=asset,
            amount=withdrawn_amount,
            location_label=recipient,
            notes=withdrawal_notes,
            counterparty=CPT_PRIVACY_POOLS,
            address=contract_address,
        )]
        if fee_amount > ZERO:
            events.append(self.base.make_event_next_index(
                tx_ref=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=asset,
                amount=fee_amount,
                location_label=recipient,
                notes=fee_notes,
                counterparty=CPT_PRIVACY_POOLS,
                address=contract_address,
            ))
        return EvmDecodingOutput(events=events)

    def _apply_ragequit(
            self,
            context: DecoderContext,
            ragequitter: ChecksumEvmAddress,
            pool_address: ChecksumEvmAddress,
            asset: CryptoAsset,
            amount: FVal,
    ) -> EvmDecodingOutput:
        notes = f'Withdraw {amount} {asset.symbol} from {PRIVACY_POOLS_LABEL} via ragequit'
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == ragequitter and
                event.address == pool_address and
                event.asset == asset and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.counterparty = CPT_PRIVACY_POOLS
                event.notes = notes
                return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=asset,
            amount=amount,
            location_label=ragequitter,
            notes=notes,
            counterparty=CPT_PRIVACY_POOLS,
            address=pool_address,
        )])

    def _decode_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            self.deployment.entrypoint is None or
            not self.base.is_tracked(depositor := bytes_to_address(context.tx_log.topics[1]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        pool_address = bytes_to_address(context.tx_log.topics[2])
        amount_raw = int.from_bytes(context.tx_log.data[32:64])
        if (asset := self._get_pool_asset(
            pool_address=pool_address,
            context=context,
            amount_raw=amount_raw,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        return self._apply_deposit(
            context=context,
            depositor=depositor,
            contract_address=self.deployment.entrypoint,
            asset=asset,
            deposited_amount=asset_normalized_value(amount=amount_raw, asset=asset),
        )

    def _decode_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            self.deployment.entrypoint is None or
            not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[3]))
        withdrawn_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=asset,
        )
        fee_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=asset,
        )
        return self._apply_withdrawal(
            context=context,
            recipient=recipient,
            contract_address=self.deployment.entrypoint,
            asset=asset,
            withdrawn_amount=withdrawn_amount,
            fee_amount=fee_amount,
            expected_receive_amount=withdrawn_amount - fee_amount,
        )

    def _decode_entrypoint_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == ENTRYPOINT_DEPOSITED_TOPIC:
            return self._decode_deposit(context)
        if context.tx_log.topics[0] == WITHDRAWAL_RELAYED_TOPIC:
            return self._decode_withdrawal(context)
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_ragequit(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != RAGEQUIT_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(ragequitter := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        pool_address = context.tx_log.address
        amount_raw = int.from_bytes(context.tx_log.data[64:96])
        if (asset := self._get_pool_asset(
            pool_address=pool_address,
            context=context,
            amount_raw=amount_raw,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        return self._apply_ragequit(
            context=context,
            ragequitter=ragequitter,
            pool_address=pool_address,
            asset=asset,
            amount=asset_normalized_value(amount=amount_raw, asset=asset),
        )

    def _decode_v2_entrypoint_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != ENTRYPOINT_DEPOSITED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(depositor := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[1]))
        deposited_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=asset,
        )
        fee_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=asset,
        )
        return self._apply_deposit(
            context=context,
            depositor=depositor,
            contract_address=V2_ENTRYPOINT,
            asset=asset,
            deposited_amount=deposited_amount,
            fee_amount=fee_amount,
        )

    def _decode_v2_ragequit(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != V2_POOL_RAGEQUIT_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(ragequitter := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[2]))
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=asset,
        )
        return self._apply_ragequit(
            context=context,
            ragequitter=ragequitter,
            pool_address=V2_POOL_VAULT,
            asset=asset,
            amount=amount,
        )

    def _decode_v2_relay(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (V2_RELAYED_TOPIC, V2_RELAYED_BATCH_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[1]))
        net_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=asset,
        )
        fee_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=asset,
        )
        gas_funding_raw = int.from_bytes(context.tx_log.data[64:96])
        expected_receive_amount = net_amount
        if asset == self.node_inquirer.native_token and gas_funding_raw > 0:
            expected_receive_amount += asset_normalized_value(
                amount=gas_funding_raw,
                asset=self.node_inquirer.native_token,
            )

        return self._apply_withdrawal(
            context=context,
            recipient=recipient,
            contract_address=V2_RELAY,
            asset=asset,
            withdrawn_amount=net_amount + fee_amount,
            fee_amount=fee_amount,
            expected_receive_amount=expected_receive_amount,
        )

    def _decode_v2_router_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(payer := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        router_address = context.tx_log.address
        router_underlying = self.deployment.v2_routers.get(router_address)
        asset: CryptoAsset = (
            self.node_inquirer.native_token
            if router_underlying is None
            else self.base.get_or_create_evm_token(router_underlying)
        )
        value_shares_raw = int.from_bytes(context.tx_log.data[:32])
        total_underlying_raw = int.from_bytes(context.tx_log.data[32:64])
        total_shares_raw = int.from_bytes(context.tx_log.data[64:96])
        if total_shares_raw > value_shares_raw and total_shares_raw > 0:
            fee_underlying_raw = total_underlying_raw - (
                total_underlying_raw * value_shares_raw // total_shares_raw
            )
        else:
            fee_underlying_raw = 0

        deposited_amount = asset_normalized_value(
            amount=total_underlying_raw - fee_underlying_raw,
            asset=asset,
        )
        fee_amount = asset_normalized_value(amount=fee_underlying_raw, asset=asset)
        return self._apply_deposit(
            context=context,
            depositor=payer,
            contract_address=router_address,
            asset=asset,
            deposited_amount=deposited_amount,
            fee_amount=fee_amount,
            handle_refund=router_underlying is None,
        )

    def _decode_v2_router_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[3])):
            return DEFAULT_EVM_DECODING_OUTPUT

        router_address = context.tx_log.address
        router_underlying = self.deployment.v2_routers.get(router_address)
        asset: CryptoAsset = (
            self.node_inquirer.native_token
            if router_underlying is None
            else self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[2]))
        )
        net_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=asset,
        )
        fee_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[128:160]),
            asset=asset,
        )
        gas_funding_raw = int.from_bytes(context.tx_log.data[160:192])
        expected_receive_amount = net_amount
        if router_underlying is None and gas_funding_raw > 0:
            expected_receive_amount += asset_normalized_value(
                amount=gas_funding_raw,
                asset=self.node_inquirer.native_token,
            )

        return self._apply_withdrawal(
            context=context,
            recipient=recipient,
            contract_address=router_address,
            asset=asset,
            withdrawn_amount=net_amount + fee_amount,
            fee_amount=fee_amount,
            expected_receive_amount=expected_receive_amount,
            match_any_sender=router_underlying is not None,
        )

    def _decode_v2_router_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == V2_PP_ROUTER_DEPOSITED_TOPIC:
            return self._decode_v2_router_deposit(context)
        if context.tx_log.topics[0] == V2_PP_ROUTER_WITHDRAWN_TOPIC:
            return self._decode_v2_router_withdrawal(context)
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoders: dict[ChecksumEvmAddress, tuple[Any, ...]] = {
            V2_ENTRYPOINT: (self._decode_v2_entrypoint_events,),
            V2_POOL_VAULT: (self._decode_v2_ragequit,),
            V2_RELAY: (self._decode_v2_relay,),
            **dict.fromkeys(self.deployment.v2_routers, (self._decode_v2_router_events,)),
        }
        if self.deployment.entrypoint is not None:
            decoders[self.deployment.entrypoint] = (self._decode_entrypoint_events,)
        if self.deployment.native_pool is not None:
            decoders[self.deployment.native_pool] = (self._decode_ragequit,)
        decoders.update(dict.fromkeys(self.deployment.token_pools, (self._decode_ragequit,)))
        return decoders

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (PRIVACY_POOLS_CPT_DETAILS,)
