import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, UNSTAKE_TOPIC
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CHILD_LIQUIDITY_GAUGE_FACTORY,
    CPT_CURVE,
    GAUGE_VOTE,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_CRV, A_CRV_3CRV, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

from .constants import (
    AAVE_POOLS,
    CLAIMED,
    CURVE_DEPOSIT_CONTRACTS,
    CURVE_MINTER,
    CURVE_SWAP_ROUTERS,
    DEPOSIT_AND_STAKE_ZAP,
    FEE_DISTRIBUTOR_3CRV,
    FEE_DISTRIBUTOR_CRVUSD,
    GAUGE_BRIBE_V2,
    GAUGE_BRIBE_V2_ASSETS,
    GAUGE_CONTROLLER,
    VOTING_ESCROW,
    VOTING_ESCROW_DEPOSIT,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=AAVE_POOLS,
            curve_deposit_contracts=CURVE_DEPOSIT_CONTRACTS | {DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers=CURVE_SWAP_ROUTERS,
            crv_minter_addresses={CHILD_LIQUIDITY_GAUGE_FACTORY, CURVE_MINTER},
        )

    def _decode_gauge_bribe(
            self,
            context: DecoderContext,
            asset_address: ChecksumEvmAddress,
    ) -> EvmDecodingOutput:
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
            return EvmDecodingOutput(action_items=[action_item], matched_counterparty=CPT_CURVE)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_curve_gauge_votes(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != GAUGE_VOTE:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.data[32:64])):
            return DEFAULT_EVM_DECODING_OUTPUT

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
        )
        return EvmDecodingOutput(events=[event], refresh_balances=False)

    def _decode_fee_distribution(self, context: DecoderContext, asset: Asset, symbol: str) -> EvmDecodingOutput:  # noqa: E501
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        suffix = ''
        if user_address != context.transaction.from_address:
            suffix = f' for {user_address}'

        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=asset,
            amount=token_normalized_value_decimals(token_amount=raw_amount, token_decimals=DEFAULT_TOKEN_DECIMALS),  # noqa: E501
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.REWARD,
            to_notes=f'Claim {{amount}} {symbol} as part of curve fees distribution{suffix}',
            to_counterparty=CPT_CURVE,
        )
        return EvmDecodingOutput(action_items=[action_item])

    def _decode_voting_escrow(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == VOTING_ESCROW_DEPOSIT:
            method = self._decode_voting_escrow_deposit
        elif context.tx_log.topics[0] == UNSTAKE_TOPIC:
            method = self._decode_voting_escrow_withdraw
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        return method(
            context=context,
            amount=token_normalized_value_decimals(token_amount=raw_amount, token_decimals=DEFAULT_TOKEN_DECIMALS),  # noqa: E501
            suffix='' if user_address == context.transaction.from_address else f' for {user_address}',  # noqa: E501
        )

    def _decode_voting_escrow_deposit(self, context: DecoderContext, amount: FVal, suffix: str) -> EvmDecodingOutput:  # noqa: E501
        locktime = Timestamp(int.from_bytes(context.tx_log.topics[2]))
        value = int.from_bytes(context.tx_log.data[0:32])

        if value == 0:
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.UPDATE,
                asset=A_CRV,
                amount=ZERO,
                location_label=context.transaction.from_address,
                notes=f'Extend CRV vote escrow lock until {timestamp_to_date(locktime, formatstr="%d/%m/%Y %H:%M:%S")}{suffix}',  # noqa: E501
                address=context.tx_log.address,
                counterparty=CPT_CURVE,
                extra_data={'locktime': locktime},
            )
            return EvmDecodingOutput(events=[event], refresh_balances=False)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_CRV and event.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Lock {amount} CRV in vote escrow until {timestamp_to_date(locktime, formatstr="%d/%m/%Y %H:%M:%S")}{suffix}'  # noqa: E501
                event.extra_data = {'locktime': locktime}
                break
        else:  # not found
            log.error(f'CRV vote escrow locking transfer was not found for {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_voting_escrow_withdraw(self, context: DecoderContext, amount: FVal, suffix: str) -> EvmDecodingOutput:  # noqa: E501
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_CRV and event.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Withdraw {amount} CRV from vote escrow{suffix}'
                break
        else:  # not found
            log.error(f'CRV vote escrow withdrawal transfer was not found for {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            GAUGE_CONTROLLER: (self._decode_curve_gauge_votes,),
            FEE_DISTRIBUTOR_3CRV: (self._decode_fee_distribution, A_CRV_3CRV, '3CRV'),
            FEE_DISTRIBUTOR_CRVUSD: (self._decode_fee_distribution, Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'), 'crvUSD'),  # noqa: E501
            VOTING_ESCROW: (self._decode_voting_escrow,),
        } | {
            address: (self._decode_gauge_bribe, address) for address in GAUGE_BRIBE_V2_ASSETS
        }
