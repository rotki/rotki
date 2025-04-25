import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CHILD_LIQUIDITY_GAUGE_FACTORY,
    CPT_CURVE,
    CURVE_SWAP_ROUTER_NG,
    GAUGE_VOTE,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_CRV, A_CRV_3CRV, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

from .constants import (
    AAVE_POOLS,
    CLAIMED,
    CURVE_DEPOSIT_CONTRACTS,
    CURVE_SWAP_ROUTER,
    DEPOSIT_AND_STAKE_ZAP,
    FEE_DISTRIBUTOR,
    GAUGE_BRIBE_V2,
    GAUGE_BRIBE_V2_ASSETS,
    GAUGE_CONTROLLER,
    VOTING_ESCROW,
    VOTING_ESCROW_DEPOSIT,
    VOTING_ESCROW_WITHDRAW,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=AAVE_POOLS,
            curve_deposit_contracts=CURVE_DEPOSIT_CONTRACTS | {DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers={CURVE_SWAP_ROUTER, CURVE_SWAP_ROUTER_NG},
            gauge_factory_address=CHILD_LIQUIDITY_GAUGE_FACTORY,
        )

    def _decode_gauge_bribe(
            self,
            context: DecoderContext,
            asset_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Back in the day they had bribe directly in the gauge giving tokens without any
        other logs. So this is checking if there is a transfer from the bribe gauge of any of
        a predetermined list of tokens"""
        if (
                context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(context.tx_log.topics[1]) == GAUGE_BRIBE_V2 and  # from
                self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            suffix = '' if user_address == context.transaction.from_address else f' for {user_address}'  # noqa: E501
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=(asset := self.base.get_or_create_evm_token(asset_address)),
                to_event_subtype=HistoryEventSubType.REWARD,
                to_notes=f'Claim {{amount}} {asset.resolve_to_asset_with_symbol().symbol} as veCRV voting bribe{suffix}',  # amount filled in by action item  # noqa: E501
                to_counterparty=CPT_CURVE,
            )
            return DecodingOutput(action_items=[action_item], matched_counterparty=CPT_CURVE)

        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_gauge_votes(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != GAUGE_VOTE:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.data[32:64])):
            return DEFAULT_DECODING_OUTPUT

        user_note = '' if user_address == context.transaction.from_address else f' from {user_address}'  # noqa: E501
        gauge_address = bytes_to_address(context.tx_log.data[64:96])
        vote_weight = int.from_bytes(context.tx_log.data[96:128])
        if vote_weight == 0:
            verb = 'Reset vote'
            weight_note = ''
        else:
            verb = 'Vote'
            weight_note = f' with {vote_weight / 100}% voting power'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.native_currency,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'{verb}{user_note} for {gauge_address} curve gauge{weight_note}',
            address=gauge_address,
            counterparty=CPT_CURVE,
            product=EvmProduct.GAUGE,
        )
        return DecodingOutput(event=event, refresh_balances=False)

    def _decode_fee_distribution(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        suffix = ''
        if user_address != context.transaction.from_address:
            suffix = f' for {user_address}'

        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_CRV_3CRV,
            amount=token_normalized_value_decimals(token_amount=raw_amount, token_decimals=DEFAULT_TOKEN_DECIMALS),  # noqa: E501
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.REWARD,
            to_notes=f'Claim {{amount}} 3CRV as part of curve fees distribution{suffix}',
            to_counterparty=CPT_CURVE,
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_voting_escrow(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == VOTING_ESCROW_DEPOSIT:
            method = self._decode_voting_escrow_deposit
        elif context.tx_log.topics[0] == VOTING_ESCROW_WITHDRAW:
            method = self._decode_voting_escrow_withdraw
        else:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        return method(
            context=context,
            amount=token_normalized_value_decimals(token_amount=raw_amount, token_decimals=DEFAULT_TOKEN_DECIMALS),  # noqa: E501
            suffix='' if user_address == context.transaction.from_address else f' for {user_address}',  # noqa: E501
        )

    def _decode_voting_escrow_deposit(self, context: DecoderContext, amount: FVal, suffix: str) -> DecodingOutput:  # noqa: E501
        locktime = Timestamp(int.from_bytes(context.tx_log.topics[2]))
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_CRV and event.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Lock {amount} CRV in vote escrow until {timestamp_to_date(locktime, formatstr="%d/%m/%Y %H:%M:%S")}{suffix}'  # noqa: E501
                event.extra_data = {'locktime': locktime}
                break
        else:  # not found
            log.error(f'CRV vote escrow locking transfer was not found for {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_voting_escrow_withdraw(self, context: DecoderContext, amount: FVal, suffix: str) -> DecodingOutput:  # noqa: E501
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_CRV and event.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Withdraw {amount} CRV from vote escrow{suffix}'
                break
        else:  # not found
            log.error(f'CRV vote escrow withdrawal transfer was not found for {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods
    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_CURVE: super(CurveDecoder, CurveDecoder).possible_products().get(CPT_CURVE, []) + [EvmProduct.BRIBE],  # noqa: E501
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            GAUGE_CONTROLLER: (self._decode_curve_gauge_votes,),
            FEE_DISTRIBUTOR: (self._decode_fee_distribution,),
            VOTING_ESCROW: (self._decode_voting_escrow,),
        } | {
            address: (self._decode_gauge_bribe, address) for address in GAUGE_BRIBE_V2_ASSETS
        }
