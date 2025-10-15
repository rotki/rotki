import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.curve.crvusd.constants import (
    CRVUSD_PEG_KEEPERS_AND_POOLS,
    CURVE_CRVUSD_CONTROLLER_ABI,
    PEG_KEEPER_PROVIDE_TOPIC,
    PEG_KEEPER_WITHDRAW_TOPIC,
)
from rotkehlchen.chain.ethereum.modules.curve.crvusd.utils import query_crvusd_controllers
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache, token_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.curve.lend.common import CurveBorrowRepayCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurvecrvusdDecoder(CurveBorrowRepayCommonDecoder, ReloadableDecoderMixin):
    """Decoder for crvUSD market events."""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.crvusd = EvmToken('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db.
        Returns a fresh addresses to decoders mapping."""
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.CURVE_CRVUSD_CONTROLLERS,
        ) is True:
            query_crvusd_controllers(evm_inquirer=self.node_inquirer)
        elif len(self.controllers) != 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            self.controllers = set(globaldb_get_general_cache_values(  # type: ignore[arg-type]  # strings from cache will be valid addresses
                cursor=cursor,
                key_parts=(
                    CacheType.CURVE_CRVUSD_CONTROLLERS,
                    str(self.node_inquirer.chain_id.serialize_for_db()),
                ),
            ))

        return self.addresses_to_decoders()

    def _get_controller_event_tokens_and_amounts(
            self,
            controller_address: 'ChecksumEvmAddress',
            context: DecoderContext,
    ) -> tuple['EvmToken', 'EvmToken', 'FVal', 'FVal'] | None:
        """Get the collateral token, borrowed token, and the corresponding amounts.
        Returns the tokens and amounts in a tuple or None on error.
        May raise:
         - ValueError
         - IndexError
        """
        if (collateral_token := self._maybe_get_cached_token(
                cache_type=CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
                contract_address=controller_address,
        )) is None:
            return None

        return (
            collateral_token,
            self.crvusd,
            token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[:32]),
                token=collateral_token,
            ),
            token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[32:64]),
                token=self.crvusd,
            ),
        )

    def maybe_decode_leveraged_borrow(self, context: DecoderContext) -> EvmDecodingOutput | None:
        """Decode events associated with creating a leveraged Curve position."""
        if (tokens_and_amounts := self._get_controller_event_tokens_and_amounts(
                controller_address=(controller_address := context.tx_log.address),
                context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve borrow transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral_token, _, collateral_amount, _ = tokens_and_amounts

        if (amm_address := self._maybe_get_cached_address_from_contract(
                cache_type=CacheType.CURVE_CRVUSD_AMM,
                contract_address=controller_address,
                contract_abi=CURVE_CRVUSD_CONTROLLER_ABI,
                contract_method='amm',
        )) is None:
            log.error(f'Failed to find AMM address for Curve crvUSD controller {controller_address} in transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # Find the amounts of collateral transferred to the AMM.
        collateral_sent, borrowed_collateral_amount = None, None
        for tx_log in context.all_logs:
            if (
                tx_log.address != collateral_token.evm_address or
                bytes_to_address(tx_log.topics[2]) != amm_address or
                tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER
            ):
                continue

            transfer_amount = token_normalized_value(
                token_amount=int.from_bytes(tx_log.data[0:32]),
                token=collateral_token,
            )
            if self.base.is_tracked(bytes_to_address(tx_log.topics[1])):
                collateral_sent = transfer_amount
            else:
                borrowed_collateral_amount = transfer_amount

        # If unable to find collateral sent to the amm from the tracked wallet or if the amount
        # sent is the same as the amount of collateral increase in this Borrow event then this is
        # not a leveraged loan. Return None so the logic continues to the normal loan decoding.
        if collateral_sent is None or collateral_sent == collateral_amount:
            return None

        if borrowed_collateral_amount is None:
            log.error(f'Failed to find borrowed amount for crvUSD leveraged loan in transaction {context.transaction!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # Find the amount of collateral supplied by the user by subtracting the amount borrowed
        # from the total collateral increase.
        collateral_increase = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=collateral_token,
        )
        collateral_sent = collateral_increase - borrowed_collateral_amount

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == amm_address and
                event.asset == collateral_token and
                event.amount == collateral_sent
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} {collateral_token.symbol} into a leveraged Curve position'  # noqa: E501
                event.counterparty = CPT_CURVE
                event.extra_data = {'controller_address': controller_address}
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_peg_keeper_update(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in {PEG_KEEPER_PROVIDE_TOPIC, PEG_KEEPER_WITHDRAW_TOPIC}:
            return DEFAULT_EVM_DECODING_OUTPUT

        # Get the pool address for this peg keeper (tx_log.address will be a valid key since this
        # function is called via the CRVUSD_PEG_KEEPERS_AND_POOLS mapping in addresses_to_decoders)
        pool_token_address = CRVUSD_PEG_KEEPERS_AND_POOLS[context.tx_log.address]

        # Unfortunately the peg keeper provide/withdraw event doesn't give much information,
        # so we have to find the transfer of the pool token from the peg keeper to the
        # tracked address and retrieve the raw reward amount from there.
        for tx_log in context.all_logs:
            if (
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                tx_log.address == pool_token_address and
                bytes_to_address(tx_log.topics[1]) == context.tx_log.address and
                self.base.is_tracked(bytes_to_address(tx_log.topics[2]))
            ):
                reward_raw_amount = int.from_bytes(tx_log.data[:32])
                break
        else:
            log.error(f'Failed to find reward amount for curve peg keeper update transaction {context.transaction!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(action_items=[
            ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                to_event_subtype=HistoryEventSubType.REWARD,
                asset=(reward_token := self.base.get_or_create_evm_token(address=pool_token_address)),  # noqa: E501
                amount=(reward_amount := token_normalized_value(
                    token_amount=reward_raw_amount,
                    token=reward_token,
                )),
                address=context.tx_log.address,
                to_counterparty=CPT_CURVE,
                to_notes=f'Receive {reward_amount} {reward_token.symbol} from Curve peg keeper update',  # noqa: E501
            ),
        ])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return (
            super().addresses_to_decoders() |
            dict.fromkeys(CRVUSD_PEG_KEEPERS_AND_POOLS, (self._decode_peg_keeper_update,))
        )
