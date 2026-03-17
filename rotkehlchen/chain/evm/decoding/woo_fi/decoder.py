import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import (
    asset_normalized_value,
    asset_raw_value,
    get_evm_token,
    get_or_create_evm_token,
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC,
    HARVEST_TOPIC,
    STAKE_TOPIC,
    UNSTAKE_TOPIC,
    WITHDRAW_TOPIC_V2,
    ZERO_ADDRESS,
)
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
    WOO_INSTANT_UNSTAKE_TOPIC,
    WOO_INSTANT_WITHDRAW_TOPIC,
    WOO_ON_REWARDED_TOPIC,
    WOO_REQUEST_WITHDRAW_TOPIC,
    WOO_RESERVE_WITHDRAW_TOPIC,
    WOO_REWARD_MASTER_CHEF,
    WOO_REWARD_MASTER_CHEF_ABI,
    WOO_ROUTER_SWAP_TOPIC,
    WOO_ROUTER_V2,
    WOO_STAKE_ON_LOCAL_TOPIC,
    WOO_STAKE_ON_PROXY_TOPIC,
    WOO_UNSTAKE_ON_LOCAL_TOPIC,
    WOO_UNSTAKE_ON_PROXY_TOPIC,
)
from rotkehlchen.constants import ONE
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset, EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
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
            woo_token_address: 'ChecksumEvmAddress',
            stake_v1_address: 'ChecksumEvmAddress | None' = None,
            stake_v2_address: 'ChecksumEvmAddress | None' = None,
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
        self.woo_token_address = woo_token_address
        self.stake_v1_address = stake_v1_address
        self.stake_v2_address = stake_v2_address
        self.rewarder_addresses: dict[int, ChecksumEvmAddress] = {}
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
        if len(context.tx_log.topics) == 2:
            if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
                return DEFAULT_EVM_DECODING_OUTPUT
            depositor_address = receiver_address = user_address
        elif not self.base.any_tracked([
            (depositor_address := bytes_to_address(context.tx_log.topics[1])),
            (receiver_address := bytes_to_address(context.tx_log.topics[2])),
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        assets_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=(underlying_token := self.base.get_or_create_evm_token(
                address=self.superchargers[context.tx_log.address],
            )),
        )
        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=(shares_asset := get_or_create_evm_token(
                userdb=self.node_inquirer.database,
                evm_address=context.tx_log.address,
                chain_id=self.node_inquirer.chain_id,
                protocol=CPT_WOO_FI,
                underlying_tokens=[UnderlyingToken(
                    address=underlying_token.evm_address,
                    token_kind=underlying_token.token_kind,
                    weight=ONE,
                )],
            )),
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == assets_amount and
                event.location_label == depositor_address and
                event.address == context.tx_log.address and
                (event.asset == underlying_token or (
                    underlying_token == self.node_inquirer.wrapped_native_token and
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

    def _decode_request_withdraw(
            self,
            context: DecoderContext,
            shares_asset: 'EvmToken',
            return_notes: str,
            underlying_asset: 'CryptoAsset',
            info_notes: str,
    ) -> EvmDecodingOutput:
        """Decode withdrawal requests for supercharger vaults and WOO staking."""
        if not self.base.is_tracked(owner_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=shares_asset,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares_amount and
                event.asset == shares_asset and
                event.location_label == owner_address and
                event.address in (context.tx_log.address, ZERO_ADDRESS)
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = return_notes.format(amount=shares_amount, asset=shares_asset.symbol)

        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=underlying_asset,
            amount=(assets_amount := asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=underlying_asset,
            )),
            location_label=owner_address,
            notes=info_notes.format(amount=assets_amount, asset=underlying_asset.symbol),
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
        if context.tx_log.topics[0] in (DEPOSIT_TOPIC, STAKE_TOPIC):
            return self._decode_supercharger_deposit(context=context)
        if context.tx_log.topics[0] == WOO_REQUEST_WITHDRAW_TOPIC:
            return self._decode_request_withdraw(
                context=context,
                shares_asset=self.base.get_or_create_evm_token(context.tx_log.address),
                return_notes=f'Return {{amount}} {{asset}} to {CPT_WOO_FI_LABEL} supercharger vault',  # noqa: E501
                underlying_asset=self.base.get_or_create_evm_asset(
                    address=self.superchargers[context.tx_log.address],
                ),
                info_notes=f'Request withdrawal of {{amount}} {{asset}} from {CPT_WOO_FI_LABEL} supercharger vault',  # noqa: E501
            )
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

    def _decode_stake_unstake_vault_token(
            self,
            context: DecoderContext,
            is_stake: bool,
    ) -> EvmDecodingOutput:
        """Decode WOOFi supercharger vault token stake/unstake events."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        self._maybe_decode_staked_vault_token_rewards(context=context)
        if is_stake:
            expected_event_type = HistoryEventType.SPEND
            new_event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            notes = f'Stake {{amount}} {{asset}} in {CPT_WOO_FI_LABEL}'
        else:
            expected_event_type = HistoryEventType.RECEIVE
            new_event_subtype = HistoryEventSubType.REMOVE_ASSET
            notes = f'Unstake {{amount}} {{asset}} from {CPT_WOO_FI_LABEL}'

        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        staking_event, reward_events = None, []
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                raw_amount == asset_raw_value(
                    amount=event.amount,
                    asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
                )
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = new_event_subtype
                event.counterparty = CPT_WOO_FI
                event.notes = notes.format(amount=event.amount, asset=resolved_asset.symbol)
                if event.extra_data is None:
                    event.extra_data = {}
                event.extra_data['woo_fi_pool_id'] = int.from_bytes(context.tx_log.topics[2])
                staking_event = event
            elif (
                event.event_type == HistoryEventType.STAKING and
                event.event_subtype == HistoryEventSubType.REWARD and
                event.counterparty == CPT_WOO_FI
            ):
                reward_events.append(event)

        if staking_event is None:
            log.error(f'Failed to find {CPT_WOO_FI_LABEL} staking event in {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(staking_event, *reward_events),
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stake_vault_token_harvest_rewards(
            self,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        """Decode harvesting rewards from staked supercharger vault tokens.
        This handles rewards associated with a Harvest log event on the WOO_REWARD_MASTER_CHEF
        contract. Other types of rewards are handled in _maybe_decode_staked_vault_token_rewards.
        """
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        self._maybe_decode_staked_vault_token_rewards(context=context)
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=(reward_token := self.base.get_or_create_evm_token(
                address=self.stake_v1_address if self.stake_v1_address is not None else self.woo_token_address,  # noqa: E501
            )),
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount and
                event.asset == reward_token and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_WOO_FI
                event.notes = f'Receive {event.amount} {reward_token.symbol} as {CPT_WOO_FI_LABEL} staking reward'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_rewarder_address(self, pool_id: int) -> 'ChecksumEvmAddress | None':
        """Get the address of the Rewarder contract associated with a given pool id.
        Stores the address in a temporary cache for future lookups in a given decoding run.
        """
        if (rewarder_address := self.rewarder_addresses.get(pool_id)) is None:
            if len(result := self.node_inquirer.call_contract(
                contract_address=WOO_REWARD_MASTER_CHEF,
                abi=WOO_REWARD_MASTER_CHEF_ABI,
                method_name='poolInfo',
                arguments=[pool_id],
            )) != 5:
                log.error(f'Failed to retrieve poolInfo for pool id {pool_id} from WOOFi RewardMasterChef contract.')  # noqa: E501
                return None

            rewarder_address = deserialize_evm_address(result[4])
            self.rewarder_addresses[pool_id] = rewarder_address

        return rewarder_address if rewarder_address != ZERO_ADDRESS else None

    def _maybe_decode_staked_vault_token_rewards(self, context: DecoderContext) -> None:
        """Decode rewards that may be present in txs involving the WOO_REWARD_MASTER_CHEF contract.
        Handles two cases:
        * WOO or xWOO tokens received from the master chef contract with no associated log event
        * Any token received from the Rewarder contract associated with the current pool id
          matching the amount in the OnRewarded log.
        """
        raw_on_rewarded_amount = user_address = None
        if (rewarder_address := self._get_rewarder_address(
            pool_id=int.from_bytes(context.tx_log.topics[2]),
        )) is not None:
            for tx_log in context.all_logs:
                if (
                    tx_log.address == rewarder_address and
                    len(tx_log.topics) > 0 and
                    tx_log.topics[0] == WOO_ON_REWARDED_TOPIC and
                    self.base.is_tracked(user_address := bytes_to_address(tx_log.topics[1]))
                ):
                    raw_on_rewarded_amount = int.from_bytes(tx_log.data[0:32])
                    break

        woo_xwoo_address = self.woo_token_address if self.stake_v1_address is None else self.stake_v1_address  # noqa: E501
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                ((
                    event.address == WOO_REWARD_MASTER_CHEF and
                    woo_xwoo_address in event.asset.identifier
                ) or (
                    user_address is not None and
                    event.location_label == user_address and
                    rewarder_address is not None and
                    event.address == rewarder_address and
                    raw_on_rewarded_amount == asset_raw_value(
                        amount=event.amount,
                        asset=event.asset.resolve_to_crypto_asset(),
                    )
                ))
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_WOO_FI
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as {CPT_WOO_FI_LABEL} staking reward'  # noqa: E501

    def _decode_master_chef_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with staking supercharger vault tokens on the
        WOO_REWARD_MASTER_CHEF contract.
        """
        if context.tx_log.topics[0] == STAKE_TOPIC:
            return self._decode_stake_unstake_vault_token(context=context, is_stake=True)
        if context.tx_log.topics[0] == UNSTAKE_TOPIC:
            return self._decode_stake_unstake_vault_token(context=context, is_stake=False)
        if context.tx_log.topics[0] == HARVEST_TOPIC:
            return self._decode_stake_vault_token_harvest_rewards(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_v1_stake_woo(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode staking WOO tokens on the stake_v1 contract."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        deposit_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # WOO has 18 decimals
        )
        mint_shares = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # xWOO has 18 decimals
        )
        out_event = in_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == deposit_amount and
                self.woo_token_address in event.asset.identifier and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Stake {deposit_amount} WOO in {CPT_WOO_FI_LABEL}'
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == mint_shares and
                context.tx_log.address in event.asset.identifier and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Receive {mint_shares} xWOO after staking in {CPT_WOO_FI_LABEL}'
                in_event = event

        if out_event is None or in_event is None:
            log.error(
                f'Failed to find both out and in events for {CPT_WOO_FI_LABEL} '
                f'staking deposit in {context.transaction}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(out_event, in_event),
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_v1_unstake(self, context: DecoderContext, is_instant: bool) -> EvmDecodingOutput:
        """Decode unstake of WOO tokens from the stake_v1 contract."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        withdraw_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # WOO has 18 decimals
        )
        out_event = in_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == withdraw_amount and
                self.woo_token_address in event.asset.identifier and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Unstake {withdraw_amount} WOO from {CPT_WOO_FI_LABEL}'
                in_event = event
            elif (
                is_instant and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                context.tx_log.address in event.asset.identifier and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_WOO_FI
                event.notes = f'Return {event.amount} xWOO to {CPT_WOO_FI_LABEL}'
                out_event = event

        if is_instant and (out_event is None or in_event is None):
            log.error(
                f'Failed to find both out and in events for {CPT_WOO_FI_LABEL} '
                f'instant unstake in {context.transaction}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(out_event, in_event),
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stake_v1_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with the stake_v1 (xWOO token) contract."""
        if (
            (xwoo := get_evm_token(
                evm_address=context.tx_log.address,
                chain_id=self.node_inquirer.chain_id,
            )) is None or
            xwoo.protocol != CPT_WOO_FI or
            xwoo.underlying_tokens is None or
            len(xwoo.underlying_tokens) != 1
        ):  # Ensure the xWOO token exists with the proper protocol and underlying asset
            get_or_create_evm_token(
                userdb=self.node_inquirer.database,
                evm_address=context.tx_log.address,
                chain_id=self.node_inquirer.chain_id,
                evm_inquirer=self.node_inquirer,
                protocol=CPT_WOO_FI,
                underlying_tokens=[UnderlyingToken(
                    address=self.base.get_or_create_evm_token(
                        address=self.woo_token_address,
                    ).evm_address,
                    token_kind=TokenKind.ERC20,
                    weight=ONE,
                )],
            )

        if context.tx_log.topics[0] == STAKE_TOPIC:
            return self._decode_v1_stake_woo(context=context)
        if context.tx_log.topics[0] == WOO_RESERVE_WITHDRAW_TOPIC:
            return self._decode_request_withdraw(
                context=context,
                shares_asset=self.base.get_or_create_evm_token(context.tx_log.address),
                return_notes=f'Return {{amount}} {{asset}} to {CPT_WOO_FI_LABEL}',
                underlying_asset=self.base.get_or_create_evm_asset(self.woo_token_address),
                info_notes=f'Request unstake of {{amount}} {{asset}} from {CPT_WOO_FI_LABEL}',
            )
        if context.tx_log.topics[0] == UNSTAKE_TOPIC:
            return self._decode_v1_unstake(context=context, is_instant=False)
        if context.tx_log.topics[0] == WOO_INSTANT_UNSTAKE_TOPIC:
            return self._decode_v1_unstake(context=context, is_instant=True)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_v2_stake_unstake(
            self,
            context: DecoderContext,
            on_proxy: bool,
            is_stake: bool,
    ) -> EvmDecodingOutput:
        """Decode staking/unstaking of WOO tokens on the stake_v2 contract.
        `on_proxy` indicates whether the stake_v2 contract is a staking proxy, in which case there
        will be LayerZero fees, or a local staking contract, in which case there are no fees.
        `is_stake` indicates whether this is a stake or unstake event.
        """
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        stake_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # WOO has 18 decimals
        )
        if is_stake:
            expected_event_type = HistoryEventType.SPEND
            new_event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            notes = f'Stake {stake_amount} WOO in {CPT_WOO_FI_LABEL}'
        else:
            expected_event_type = HistoryEventType.RECEIVE
            new_event_subtype = HistoryEventSubType.REMOVE_ASSET
            notes = f'Unstake {stake_amount} WOO from {CPT_WOO_FI_LABEL}'

        staking_event = fee_event = refund_event = None
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == stake_amount and
                self.woo_token_address in event.asset.identifier and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = new_event_subtype
                event.counterparty = CPT_WOO_FI
                event.notes = notes
                staking_event = event
                if not on_proxy:
                    break
            elif (
                on_proxy and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.location_label == user_address and
                event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_WOO_FI
                fee_event = event
            elif (
                on_proxy and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.location_label == user_address
            ):
                refund_event = event

        if on_proxy and fee_event is not None:
            if refund_event is not None and refund_event.amount < fee_event.amount:
                fee_event.amount -= refund_event.amount
                context.decoded_events.remove(refund_event)

            fee_event.notes = f'Spend {fee_event.amount} {self.node_inquirer.native_token.symbol} as {CPT_WOO_FI_LABEL} staking fee'  # noqa: E501

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=(staking_event, fee_event),
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_stake_v2_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with the stake_v2 contract."""
        if context.tx_log.topics[0] == WOO_STAKE_ON_PROXY_TOPIC:
            return self._decode_v2_stake_unstake(context=context, on_proxy=True, is_stake=True)
        if context.tx_log.topics[0] == WOO_STAKE_ON_LOCAL_TOPIC:
            return self._decode_v2_stake_unstake(context=context, on_proxy=False, is_stake=True)
        if context.tx_log.topics[0] == WOO_UNSTAKE_ON_PROXY_TOPIC:
            return self._decode_v2_stake_unstake(context=context, on_proxy=True, is_stake=False)
        if context.tx_log.topics[0] == WOO_UNSTAKE_ON_LOCAL_TOPIC:
            return self._decode_v2_stake_unstake(context=context, on_proxy=False, is_stake=False)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        mappings: dict[ChecksumEvmAddress, tuple[Any, ...]] = {
            WOO_ROUTER_V2: (self._decode_swap,),
            WOO_CROSS_SWAP_ROUTER_V5: (self._decode_cross_swap_router_events,),
            WOO_REWARD_MASTER_CHEF: (self._decode_master_chef_events,),
        }
        for address in self.superchargers:
            mappings[address] = (self._decode_supercharger_events,)
        for address in self.withdrawal_managers:
            mappings[address] = (self._decode_withdraw,)
        if self.stake_v1_address is not None:
            mappings[self.stake_v1_address] = (self._decode_stake_v1_events,)
        if self.stake_v2_address is not None:
            mappings[self.stake_v2_address] = (self._decode_stake_v2_events,)

        return mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_WOO_FI,
            label=CPT_WOO_FI_LABEL,
            image='woo_fi.svg',
        ),)
