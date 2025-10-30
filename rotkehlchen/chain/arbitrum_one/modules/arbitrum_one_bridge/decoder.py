import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from eth_typing.abi import ABI

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.decoding.interfaces import ArbitrumDecoderInterface
from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


BRIDGE_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000000064')
L2_ERC20_GATEWAY: Final = string_to_evm_address('0x09e9222E96E7B4AE2a407B98d48e330053351EEe')
L2_GATEWAY_ROUTER: Final = string_to_evm_address('0x5288c571Fd7aD117beA99bF60FE0846C4E84F933')
TRANSFER_ROUTED: Final = b'\x85)\x1d\xff!a\xa9</\x12\xc8\x19\xd3\x18\x89\xc9lc\x04!\x16\xf5\xbcZ Z\xa7\x01\xc2\xc4)\xf5'  # noqa: E501
TOKEN_WITHDRAWAL_INITIATED: Final = b'0s\xa7N\xcbr\x8d\x10\xbew\x9f\xe1\x9at\xa1B\x8e F\x8f[M\x16{\xf9\xc7=\x90g\x84}s'  # noqa: E501
L2_TO_L1_TX: Final = b'>z\xaf\xa7}\xbf\x18k\x7f\xd4\x88\x00k\xef\xf8\x93tL\xaa<Oo)\x9e\x8ap\x9f\xa2\x08st\xfc'  # https://github.com/OffchainLabs/bold/blob/4c45c226da2662f357450fcce9270bb00324eb57/contracts/src/precompiles/ArbSys.sol#L113  # noqa: E501
DEPOSIT_TX_TYPE: Final = 100  # A deposit of ETH from L1 to L2 via the Arbitrum bridge.
ERC20_DEPOSIT_FINALIZED: Final = b'\xc7\xf2\xe9\xc5\\@\xa5\x0f\xbc!}\xfcp\xcd9\xa2"\x94\r\xfab\x14Z\xa0\xcaI\xeb\x955\xd4\xfc\xb2'  # noqa: E501
WITHDRAW_ETH_METHOD: Final = b'%\xe1`c'


L2_GATEWAY_ROUTE_CALCULATE_L2TOKEN_ABI: Final[ABI] = [{
    'inputs': [
        {
            'name': 'l1ERC20',
            'type': 'address',
        },
    ],
    'name': 'calculateL2TokenAddress',
    'outputs': [
        {
            'name': '',
            'type': 'address',
        },
    ],
    'stateMutability': 'view',
    'type': 'function',
}]


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ArbitrumOneBridgeDecoder(ArbitrumDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_transfer_routed(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != TRANSFER_ROUTED:
            return DEFAULT_EVM_DECODING_OUTPUT

        l1_token_address = bytes_to_address(context.tx_log.topics[1])
        to_asset = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=l1_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=None,  # don't have it since we are in arbitrum decoder
        )
        from_address = bytes_to_address(context.tx_log.topics[2])
        to_address = bytes_to_address(context.tx_log.topics[3])

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        try:
            raw_token_address = self.base.evm_inquirer.call_contract(
                contract_address=context.tx_log.address,  # the gateway router
                abi=L2_GATEWAY_ROUTE_CALCULATE_L2TOKEN_ABI,
                method_name='calculateL2TokenAddress',
                arguments=[l1_token_address],
            )
        except RemoteError as e:
            log.error(f'During arbitrum bridge erc20 withdrawal got error calling {context.tx_log.address} l2TokenAddress({l1_token_address}): {e!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        from_token_address = deserialize_evm_address(raw_token_address)

        for tx_log in context.all_logs:  # Check all logs to determine to find the token withdrawal
            if tx_log.topics[0] == TOKEN_WITHDRAWAL_INITIATED:
                context.tx_log = tx_log  # since this is a different log
                return self._decode_erc20_withdraw_event(
                    context=context,
                    from_address=from_address,
                    to_address=to_address,
                    from_token_address=from_token_address,
                    to_asset=to_asset,
                )

        # else we got a problem
        log.error(f'Could not find a WithdrawalInitiated event after a transfer routed for arbitrum {context.transaction.tx_hash!s}')  # noqa: E501
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_erc20_withdraw_event(
            self,
            context: DecoderContext,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            from_token_address: ChecksumEvmAddress,
            to_asset: EvmToken,
    ) -> EvmDecodingOutput:
        """Decodes an event for depositing ERC20 tokens into the bridge.
        (Sending assets from arbitrum one)
        """
        from_token = self.base.get_or_create_evm_token(from_token_address)
        raw_amount = int.from_bytes(context.tx_log.data[64:96])
        amount = asset_normalized_value(raw_amount, to_asset)
        to_label = f'address {to_address}'
        if to_address == from_address:
            to_label = ''

        # Corresponding transfer does not exist yet during decoding. So we create it
        # and send an action item to skip next one to not have duplicates
        notes = (
            f'Bridge {amount} {from_token.symbol} from Arbitrum One '
            f'to Ethereum{to_label} via Arbitrum One bridge'
        )
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=from_token,
            amount=amount,
            to_event_type=HistoryEventType.DEPOSIT,
            to_event_subtype=HistoryEventSubType.BRIDGE,
            to_notes=notes,
            to_counterparty=CPT_ARBITRUM_ONE,
        )
        return EvmDecodingOutput(action_items=[action_item])

    def _decode_eth_withdraw_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes an event for depositing ETH into the bridge (Removing ETH from arbitrum one)"""
        if (
            context.transaction.input_data[:4] != WITHDRAW_ETH_METHOD or
            context.tx_log.topics[0] != L2_TO_L1_TX
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_address = bytes_to_address(context.tx_log.topics[1])
        to_address = bytes_to_address(context.transaction.input_data[4:])  # only argument of input data is destination address # noqa: E501

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[128:160])
        amount = from_wei(FVal(raw_amount))
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.location_label == from_address and
                    event.asset == A_ETH and
                    event.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=from_address,
                    to_address=to_address,
                    from_chain=ChainID.ARBITRUM_ONE,
                    to_chain=ChainID.ETHEREUM,
                    amount=amount,
                    asset=self.eth,
                    expected_event_type=HistoryEventType.SPEND,
                    new_event_type=HistoryEventType.DEPOSIT,
                    counterparty=ARBITRUM_ONE_CPT_DETAILS,
                )
                break

        else:  # event was not found
            log.error(f'ETH withdraw transaction was not found for {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_eth_deposit_event(
            self,
            transaction: ArbitrumOneTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Decodes an event for withdrawing ETH from the bridge (Receiving ETH to arbitrum one)

        An example that Dimitris tried is this: https://arbiscan.io/tx/0x30505174f2f82a6513f21eb5177e59935a6da95d057e4c1972e65da90ea1c547

        We just judge by the transaction type this is a deposit and don't know who it came from.
        """
        if transaction.tx_type != DEPOSIT_TX_TYPE:
            return decoded_events

        to_address = transaction.to_address
        # Find the corresponding transfer event and update it
        for event in decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == to_address and
                    event.asset == A_ETH and
                    event.amount == from_wei(FVal(transaction.value))
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {event.amount} ETH from Ethereum to Arbitrum '
                    f'One via Arbitrum One bridge'
                )
                break

        else:  # event was not found
            log.error(
                f'ETH receiving transaction was not found in Arbitrum for {transaction.tx_hash!s}',
            )

        return decoded_events

    def _decode_erc20_deposit_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes an event for withdrawing ERC20 tokens from bridge
        (Receiving ECR20 tokens to arbitrum one)
        """
        if context.tx_log.topics[0] != ERC20_DEPOSIT_FINALIZED:
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        l1_token_address = bytes_to_address(context.tx_log.topics[1])
        from_address = bytes_to_address(context.tx_log.topics[2])
        to_address = bytes_to_address(context.tx_log.topics[3])
        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_label = f' address {from_address}' if from_address != to_address else ''

        for event in context.decoded_events:
            asset_resolved = self.eth if event.asset == A_ETH else event.asset.resolve_to_evm_token()  # noqa: E501
            amount = asset_normalized_value(raw_amount, asset_resolved)
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == to_address and
                    event.address == ZERO_ADDRESS and
                    event.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {amount} {asset_resolved.symbol} from Ethereum{from_label} '
                    f'to Arbitrum One via Arbitrum One bridge'
                )
                break

        else:  # event was not found
            log.error(
                f'Token receiving event was not found in Arbitrum for '
                f'{context.transaction.tx_hash!s} and L1 token {l1_token_address}',
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS: (self._decode_eth_withdraw_event,),
            L2_GATEWAY_ROUTER: (self._decode_transfer_routed,),
            L2_ERC20_GATEWAY: (self._decode_erc20_deposit_event,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ARBITRUM_ONE_CPT_DETAILS,)

    # -- ArbitrumDecoderInterface methods
    def decoding_by_tx_type(self) -> dict[int, list[tuple[int, Callable]]]:
        return {
            DEPOSIT_TX_TYPE: [
                (0, self._decode_eth_deposit_event),  # We need this rule because these transactions contain no logs and consequently we can only run a decoder as a post decoding rule  # noqa: E501
            ],
        }
