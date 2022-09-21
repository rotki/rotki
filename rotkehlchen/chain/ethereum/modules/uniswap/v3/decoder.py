from typing import Callable, List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.types import EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_UNISWAP_V3

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67  # noqa: E501
# https://docs.uniswap.org/protocol/reference/core/interfaces/pool/IUniswapV3PoolEvents#swap
SWAP_SIGNATURE = b'\xc4 y\xf9JcP\xd7\xe6#_)\x17I$\xf9(\xcc*\xc8\x18\xebd\xfe\xd8\x00N\x11_\xbc\xcag'  # noqa: E501


class Uniswapv3Decoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _maybe_decode_v3_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> None:
        """Decode trade for uniswap v3. The approach is to read the events and detect the ones
        where the user sends and receives any asset. The swap events need to be consecutive and
        for that we use maybe_reshuffle_events.

        The swap method has as data the delta on the pool for the assets swapped so we make sure
        to use signed integers to detect the amounts.
        """
        out_event = in_event = None
        if tx_log.topics[0] == SWAP_SIGNATURE:
            received_eth = ZERO
            for event in decoded_events:
                if event.asset == A_ETH and event.event_type == HistoryEventType.RECEIVE:
                    received_eth += event.balance.amount

            buyer = hex_or_bytes_to_address(tx_log.topics[2])
            # Uniswap V3 represents the delta of tokens in the pool with a signed integer
            # for each token. In the transaction we have the difference of tokens in the pool
            # for the token0 [0:32] and the token1 [32:64]. If that difference is negative it
            # means that the tokens are leaving the pool (the user receives them) and if it is
            # positive they get into the pool (the user sends them to the pool)
            delta_token_0 = hex_or_bytes_to_int(tx_log.data[0:32], signed=True)
            delta_token_1 = hex_or_bytes_to_int(tx_log.data[32:64], signed=True)
            if delta_token_0 > 0:
                amount_received, amount_sent = delta_token_1, delta_token_0
            else:
                amount_received, amount_sent = delta_token_0, delta_token_1
            # We take the absolute value since we have it negative and we need it positive
            amount_received = abs(amount_received)

            for event in decoded_events:
                # When swapping token for ETH the WETH contract is called by the router and the
                # swap is not executed with the user in the topic but the router. This is when
                # tx_log.topics[1] == tx_log.topics[2]
                crypto_asset = event.asset.resolve_to_crypto_asset()
                if (
                    event.event_type == HistoryEventType.SPEND and
                    (event.location_label == buyer or tx_log.topics[1] == tx_log.topics[2]) and
                    (
                        event.balance.amount == (spent_amount := asset_normalized_value(amount=amount_sent, asset=event.asset)) or  # noqa: E501
                        event.asset == A_ETH and spent_amount + received_eth == event.balance.amount  # noqa: E501
                    )
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in uniswap-v3 from {event.location_label}'  # noqa: E501
                    out_event = event
                elif (
                    (
                        (event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.TRANSFER)) and  # noqa: E501
                        (event.location_label == buyer or event.asset == A_ETH) and
                        event.balance.amount == asset_normalized_value(amount=amount_received, asset=event.asset)  # noqa: E501
                    )
                ):
                    # In this branch of the condition we also add the transfer to correctly decode
                    # the case where ETH was sent to the user in a multi-step swap that was decoded
                    # by the event in the previous step. The check for the location label and the
                    # amount ensure that we are decoding the right event.
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} in uniswap-v3 from {event.location_label}'  # noqa: E501
                    in_event = event
                elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.balance.amount != asset_normalized_value(amount_received, event.asset)
                ):
                    # Those are assets returned due to a change in the swap price
                    event.event_type = HistoryEventType.TRANSFER
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = f'Refund of {event.balance.amount} {crypto_asset.symbol} in uniswap-v3 due to price change'  # noqa: E501

        maybe_reshuffle_events(out_event=out_event, in_event=in_event)

    # -- DecoderInterface methods

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_v3_swap,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_UNISWAP_V3]
