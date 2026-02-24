import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.assets.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, WITHDRAW_TOPIC_V2, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.woo_fi.constants import (
    CPT_WOO_FI,
    CPT_WOO_FI_LABEL,
    LAYER_ZERO_EID_TO_CHAIN_ID,
    WOO_CROSS_SWAP_ON_DEST_CHAIN_TOPIC,
    WOO_CROSS_SWAP_ON_SRC_CHAIN_TOPIC,
    WOO_CROSS_SWAP_ROUTER_V5,
    WOO_INSTANT_WITHDRAW_TOPIC,
    WOO_REQUEST_WITHDRAW_TOPIC,
    WOO_ROUTER_SWAP_TOPIC,
    WOO_ROUTER_V2,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WooVaultInfo(NamedTuple):
    """Contract addresses for a given WooFi earn vault."""
    token: 'ChecksumEvmAddress'
    supercharger: 'ChecksumEvmAddress'
    withdraw_manager: 'ChecksumEvmAddress'


class WooFiCommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            earn_vaults: list[WooVaultInfo],
    ) -> None:
        """Common decoder for the WOOFi protocol.
        `earn_tokens` is a list of WooVaultInfo tuples. Each tuple contains the address of the
        token, supercharger and withdraw manager contracts for a given vault.
        Deployment addresses for each chain can be found here:
        https://learn.woo.org/woofi-docs/woofi-dev-docs/references/readme
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.superchargers = {}
        self.withdrawal_managers = {}
        for earn_vault in earn_vaults:
            self.superchargers[earn_vault.supercharger] = earn_vault.token
            self.withdrawal_managers[earn_vault.withdraw_manager] = earn_vault.token

    def _decode_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode swaps made via the WooFi router."""
        if context.tx_log.topics[0] != WOO_ROUTER_SWAP_TOPIC or not self.base.any_tracked([
            (from_address := bytes_to_address(context.tx_log.data[96:128])),
            (to_address := bytes_to_address(context.tx_log.topics[3])),
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=(from_asset := self.base.get_or_create_evm_asset(
                address=bytes_to_address(context.tx_log.topics[1]),
            )),
        )
        to_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[64:96]),
            asset=(to_asset := self.base.get_or_create_evm_asset(
                address=bytes_to_address(context.tx_log.topics[2]),
            )),
        )
        out_event = in_event = None
        for event in context.decoded_events:
            if (((
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.SPEND
                )) and
                event.asset == from_asset and
                event.amount == from_amount and
                event.location_label == from_address
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_WOO_FI
                event.notes = f'Swap {from_amount} {from_asset.symbol} in {CPT_WOO_FI_LABEL}'
                out_event = event
            elif (((
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.RECEIVE
                )) and
                event.asset == to_asset and
                event.amount == to_amount and
                event.location_label == to_address
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_WOO_FI
                event.notes = f'Receive {to_amount} {to_asset.symbol} after {CPT_WOO_FI_LABEL} swap'  # noqa: E501
                in_event = event

        if out_event is None and in_event is None:
            log.error(f'Failed to find both sides of WooFi swap in {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=[out_event, in_event],
        )
        return EvmDecodingOutput(process_swaps=True)

    def _decode_cross_chain_swap(
            self,
            context: DecoderContext,
            on_src: bool,
            user_address: 'ChecksumEvmAddress',
            bridge_asset_address: 'ChecksumEvmAddress',
            bridge_amount_raw: int,
            swap_asset_address: 'ChecksumEvmAddress',
            swap_amount_raw: int,
    ) -> EvmDecodingOutput:
        """Decode either the source chain or destination chain WooFi cross-chain swap events.
        The `on_src` parameter indicates whether we are decoding the events on the source chain
        or the destination chain side of the bridge.
        A WooFi cross-chain swap may include all or some of the following steps:
        1. Swap asset A to asset B on the source chain
        2. Bridge asset B to asset C on the destination chain
        3. Swap asset C to asset D on the destination chain
        https://learn.woo.org/woofi/crosschain-swaps
        The user will only send/receive asset A or D. So we need to create the missing bridge
        and swap events to provide a clear picture of the actual operations that were performed.
        """
        if not self.base.is_tracked(user_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        bridge_amount = asset_normalized_value(
            amount=bridge_amount_raw,
            asset=(bridge_asset := self.base.get_or_create_evm_asset(bridge_asset_address)),
        )
        swap_amount = asset_normalized_value(
            amount=swap_amount_raw,
            asset=(swap_asset := self.base.get_or_create_evm_asset(swap_asset_address)),
        )
        this_chain = self.node_inquirer.chain_id.label()
        if (chain_id := LAYER_ZERO_EID_TO_CHAIN_ID.get(eid := int.from_bytes(context.tx_log.data[0:32]))) is not None:  # noqa: E501
            other_chain = chain_id.label()
        else:
            other_chain = f'unknown chain (LayerZero EID: {eid})'

        swap_spend_notes = f'Swap {{amount}} {{asset}} in {CPT_WOO_FI_LABEL}'
        swap_receive_notes = f'Receive {{amount}} {{asset}} after {CPT_WOO_FI_LABEL} swap'
        if on_src:
            swap_expected_type = HistoryEventType.SPEND
            swap_expected_subtype = HistoryEventSubType.SPEND
            swap_other_side_subtype = HistoryEventSubType.RECEIVE
            swap_existing_side_notes = swap_spend_notes
            swap_other_side_notes = swap_receive_notes
            bridge_expected_type = HistoryEventType.SPEND
            bridge_new_type = HistoryEventType.DEPOSIT
            from_to_notes = f'from {this_chain} to {other_chain}'
        else:
            swap_expected_type = HistoryEventType.RECEIVE
            swap_expected_subtype = HistoryEventSubType.RECEIVE
            swap_other_side_subtype = HistoryEventSubType.SPEND
            swap_existing_side_notes = swap_receive_notes
            swap_other_side_notes = swap_spend_notes
            bridge_expected_type = HistoryEventType.RECEIVE
            bridge_new_type = HistoryEventType.WITHDRAWAL
            from_to_notes = f'from {other_chain} to {this_chain}'

        bridge_event_notes = f'Bridge {bridge_amount} {bridge_asset.symbol} {from_to_notes} via {CPT_WOO_FI_LABEL}'  # noqa: E501
        has_swap = bridge_asset != swap_asset
        swap_event = other_swap_event = bridge_event = bridge_fee_event = None
        for event in context.decoded_events:
            if (
                has_swap and
                ((
                    event.event_type == swap_expected_type and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == swap_expected_subtype
                )) and
                event.asset == swap_asset and
                event.amount == swap_amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = swap_expected_subtype
                event.counterparty = CPT_WOO_FI
                event.notes = swap_existing_side_notes.format(
                    amount=swap_amount,
                    asset=swap_asset.symbol,
                )
                swap_event = event
            elif (
                not has_swap and
                event.event_type == bridge_expected_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == bridge_asset and
                event.amount == bridge_amount and
                event.location_label == user_address
            ):
                event.event_type = bridge_new_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_WOO_FI
                event.notes = bridge_event_notes
                bridge_event = event
            elif (
                on_src and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_WOO_FI
                event.notes = f'Spend {event.amount} {self.node_inquirer.native_token.symbol} as {CPT_WOO_FI_LABEL} bridge fee'  # noqa: E501
                bridge_fee_event = event

        if has_swap and swap_event is not None:
            context.decoded_events.extend([(other_swap_event := self.base.make_event_next_index(
                tx_ref=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.TRADE,
                event_subtype=swap_other_side_subtype,
                asset=bridge_asset,
                amount=bridge_amount,
                location_label=user_address,
                notes=swap_other_side_notes.format(
                    amount=bridge_amount,
                    asset=bridge_asset.symbol,
                ),
                counterparty=CPT_WOO_FI,
            )), (bridge_event := self.base.make_event_next_index(
                tx_ref=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=bridge_new_type,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=bridge_asset,
                amount=bridge_amount,
                location_label=user_address,
                notes=bridge_event_notes,
                counterparty=CPT_WOO_FI,
                address=context.tx_log.address,
            ))])

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(
                [swap_event, other_swap_event, bridge_event, bridge_fee_event]
                if on_src else [bridge_event, other_swap_event, swap_event]
            ),
        )
        return EvmDecodingOutput(process_swaps=True)

    def _decode_cross_swap_router_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode log events emitted by the WooFi cross-swap router contract."""
        if context.tx_log.topics[0] == WOO_CROSS_SWAP_ON_SRC_CHAIN_TOPIC:
            return self._decode_cross_chain_swap(
                context=context,
                on_src=True,
                user_address=bytes_to_address(context.tx_log.topics[2]),
                bridge_asset_address=bytes_to_address(context.tx_log.data[96:128]),
                bridge_amount_raw=int.from_bytes(context.tx_log.data[160:192]),
                swap_asset_address=bytes_to_address(context.tx_log.data[32:64]),
                swap_amount_raw=int.from_bytes(context.tx_log.data[64:96]),
            )
        if context.tx_log.topics[0] == WOO_CROSS_SWAP_ON_DEST_CHAIN_TOPIC:
            return self._decode_cross_chain_swap(
                context=context,
                on_src=False,
                user_address=bytes_to_address(context.tx_log.topics[3]),
                bridge_asset_address=bytes_to_address(context.tx_log.data[32:64]),
                bridge_amount_raw=int.from_bytes(context.tx_log.data[64:96]),
                swap_asset_address=bytes_to_address(context.tx_log.data[160:192]),
                swap_amount_raw=int.from_bytes(context.tx_log.data[224:256]),
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_supercharger_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode deposits into WooFi supercharger vaults."""
        if not self.base.any_tracked([
            (depositor_address := bytes_to_address(context.tx_log.topics[1])),
            (receiver_address := bytes_to_address(context.tx_log.topics[2])),
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=(shares_asset := self.base.get_or_create_evm_token(context.tx_log.address)),
        )
        assets_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=(underlying_asset := self.base.get_or_create_evm_asset(
                address=self.superchargers[context.tx_log.address],
            )),
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == assets_amount and
                event.location_label == depositor_address and
                event.address == context.tx_log.address and
                (event.asset == underlying_asset or (
                    underlying_asset == self.node_inquirer.wrapped_native_token and
                    event.asset == self.node_inquirer.native_token
                ))
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Deposit {assets_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in a {CPT_WOO_FI_LABEL} supercharger vault'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares_amount and
                event.asset == shares_asset and
                event.location_label == receiver_address and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Receive {shares_amount} {shares_asset.symbol} after {CPT_WOO_FI_LABEL} supercharger deposit'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_supercharger_request_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode WooFi supercharger vault withdrawal requests."""
        if not self.base.is_tracked(owner_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=(shares_asset := self.base.get_or_create_evm_token(context.tx_log.address)),
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares_amount and
                event.asset == shares_asset and
                event.location_label == owner_address and
                event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Return {shares_amount} {shares_asset.symbol} to {CPT_WOO_FI_LABEL} supercharger vault'  # noqa: E501

        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=(underlying_asset := self.base.get_or_create_evm_asset(
                address=self.superchargers[context.tx_log.address],
            )),
            amount=(assets_amount := asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=underlying_asset,
            )),
            location_label=owner_address,
            notes=f'Request withdrawal of {assets_amount} {underlying_asset.symbol} from {CPT_WOO_FI_LABEL} supercharger vault',  # noqa: E501
            counterparty=CPT_WOO_FI,
            address=context.tx_log.address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_instant_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode WooFi supercharger vault instant withdrawals."""
        if not self.base.is_tracked(owner_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        assets_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=(underlying_asset := self.base.get_or_create_evm_asset(
                address=self.superchargers[context.tx_log.address],
            )),
        )
        vault_asset = self.base.get_or_create_evm_asset(
            address=context.tx_log.address,
        )
        fee_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[64:96]),
            asset=underlying_asset,
        )
        actual_receive_amount = assets_amount - fee_amount
        out_event = in_event = actual_receive_asset = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == vault_asset and
                event.location_label == owner_address and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Return {event.amount} {vault_asset.symbol} to {CPT_WOO_FI_LABEL} supercharger vault'  # noqa: E501
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == actual_receive_amount and
                event.location_label == owner_address and
                event.address == context.tx_log.address and
                (event.asset == underlying_asset or (
                    underlying_asset == self.node_inquirer.wrapped_native_token and
                    event.asset == self.node_inquirer.native_token
                ))
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.amount = assets_amount
                actual_receive_asset = event.asset.resolve_to_asset_with_symbol()
                event.notes = f'Withdraw {event.amount} {actual_receive_asset.symbol} from {CPT_WOO_FI_LABEL} supercharger vault'  # noqa: E501
                in_event = event

        if out_event is None or in_event is None or actual_receive_asset is None:
            log.error(
                f'Failed to find both out and in events for {CPT_WOO_FI_LABEL} '
                f'instant withdrawal in {context.transaction}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        context.decoded_events.append(fee_event := self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.FEE,
            asset=in_event.asset,
            amount=fee_amount,
            location_label=owner_address,
            notes=f'Spend {fee_amount} {actual_receive_asset.symbol} as {CPT_WOO_FI_LABEL} instant withdrawal fee',  # noqa: E501
            counterparty=CPT_WOO_FI,
            address=context.tx_log.address,
        ))
        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(out_event, in_event, fee_event),
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_supercharger_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode log events emitted by the WooFi supercharger contracts."""
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            return self._decode_supercharger_deposit(context=context)
        if context.tx_log.topics[0] == WOO_REQUEST_WITHDRAW_TOPIC:
            return self._decode_supercharger_request_withdraw(context=context)
        if context.tx_log.topics[0] == WOO_INSTANT_WITHDRAW_TOPIC:
            return self._decode_instant_withdraw(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode WooFi supercharger vault withdrawals via the withdrawal manager."""
        if context.tx_log.topics[0] != WITHDRAW_TOPIC_V2 or not self.base.is_tracked(
            address=(user_address := bytes_to_address(context.tx_log.topics[1])),
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=(underlying_asset := self.base.get_or_create_evm_asset(
                address=self.withdrawal_managers[context.tx_log.address],
            )),
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                (event.asset == underlying_asset or (
                    underlying_asset == self.node_inquirer.wrapped_native_token and
                    event.asset == self.node_inquirer.native_token
                ))
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Withdraw {amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {CPT_WOO_FI_LABEL} supercharger vault'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            WOO_ROUTER_V2: (self._decode_swap,),
            WOO_CROSS_SWAP_ROUTER_V5: (self._decode_cross_swap_router_events,),
        } | dict.fromkeys(self.superchargers, (self._decode_supercharger_events,)) \
        | dict.fromkeys(self.withdrawal_managers, (self._decode_withdraw,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_WOO_FI,
            label=CPT_WOO_FI_LABEL,
            image='woo_fi.svg',
        ),)
