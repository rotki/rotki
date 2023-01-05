from typing import TYPE_CHECKING, Callable, Literal, Optional

from web3 import Web3

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import (
    UNISWAP_V2_ROUTER,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, generate_address_via_create2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501
# occurs when liquidity is added to uniswap v2 pool
MINT_SIGNATURE = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
BURN_SIGNATURE = b'\xdc\xcdA/\x0b\x12R\x81\x9c\xb1\xfd3\x0b\x93"L\xa4&\x12\x89+\xb3\xf4\xf7\x89\x97nm\x81\x93d\x96'  # noqa: E501
TRANSFER_SIGNATURE = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501

UNISWAP_V2_FACTORY = string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
UNISWAP_V2_INIT_CODE_HASH = '0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f'  # noqa: E501


class Uniswapv2Decoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.database = ethereum_inquirer.database
        self.ethereum_inquirer = ethereum_inquirer

    def _decode_basic_swap_info(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
    ) -> None:
        """
        Decodes only basic swap info. Basic swap info includes trying to find approval, spend and
        receive events for this particular swap but doesn't include ensuring order of events if the
        swap was made by an aggregator.
        """
        # amount_in is the amount that enters the pool and amount_out the one
        # that leaves the pool
        amount_in_token_0, amount_in_token_1 = hex_or_bytes_to_int(tx_log.data[0:32]), hex_or_bytes_to_int(tx_log.data[32:64])  # noqa: E501
        amount_out_token_0, amount_out_token_1 = hex_or_bytes_to_int(tx_log.data[64:96]), hex_or_bytes_to_int(tx_log.data[96:128])  # noqa: E501
        amount_in, amount_out = amount_in_token_0, amount_out_token_0
        if amount_in == ZERO:
            amount_in = amount_in_token_1
        if amount_out == ZERO:
            amount_out = amount_out_token_1

        decode_basic_uniswap_info(
            amount_sent=amount_in,
            amount_received=amount_out,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V2,
            notify_user=self.notify_user,
        )

    def _maybe_decode_v2_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        if tx_log.topics[0] == SWAP_SIGNATURE:
            if transaction.to_address == UNISWAP_V2_ROUTER:
                # If uniswap v2 router is used, then we can decode an entire swap.
                # Uniswap v2 router is a simple router that always has a single spend and a single
                # receive event.
                decode_uniswap_v2_like_swap(
                    tx_log=tx_log,
                    decoded_events=decoded_events,
                    transaction=transaction,
                    counterparty=CPT_UNISWAP_V2,
                    database=self.database,
                    ethereum_inquirer=self.ethereum_inquirer,
                    notify_user=self.notify_user,
                )
            else:
                # Else some aggregator (potentially complex) is used, so we decode only basic info
                # and other properties should be decoded by the aggregator decoding methods later.
                self._decode_basic_swap_info(tx_log=tx_log, decoded_events=decoded_events)

    def _maybe_decode_v2_liquidity_addition_and_removal(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        if tx_log.topics[0] == MINT_SIGNATURE:
            return self._decode_liquidity_addition_or_removal(
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
                event_action_type='addition',
            )
        if tx_log.topics[0] == BURN_SIGNATURE:
            return self._decode_liquidity_addition_or_removal(
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
                event_action_type='removal',
            )
        return None

    def _decode_liquidity_addition_or_removal(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
            event_action_type: Literal['addition', 'removal'],
    ) -> None:
        """
        This method decodes a liquidity addition or removal to Uniswap V2 pool.

        Examples of such transactions are:
        https://etherscan.io/tx/0x1bab8a89a6a3f8cb127cfaf7cd58809201a4e230d0a05f9e067674749605959e (deposit)
        https://etherscan.io/tx/0x0936a16e1d3655e832c60bed52040fd5ac0d99d03865d11225b3183dba318f43 (withdrawal)
        """  # noqa: E501
        maybe_pool_address = tx_log.address
        amount0_raw = hex_or_bytes_to_int(tx_log.data[:32])
        amount1_raw = hex_or_bytes_to_int(tx_log.data[32:64])

        token0: Optional['CryptoAsset'] = None
        token1: Optional['CryptoAsset'] = None
        event0_idx = event1_idx = None

        if event_action_type == 'addition':
            notes = 'Add {} {} of liquidity to Uniswap V2 LP {}'
            from_event_type = (HistoryEventType.SPEND, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)
        else:
            notes = 'Remove {} {} of liquidity from Uniswap V2 LP {}'
            from_event_type = (HistoryEventType.RECEIVE, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET)

        # First, get the tokens deposited into the pool. The reason for this approach is to circumvent  # noqa: E501
        # scenarios where the mint/burn event comes before the needed transfer events.
        for other_log in all_logs:
            if other_log.topics[0] == TRANSFER_SIGNATURE and hex_or_bytes_to_int(other_log.data[:32]) == amount0_raw:  # noqa: E501
                token0 = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=other_log.address,
                    chain_id=ChainID.ETHEREUM,
                    token_kind=EvmTokenKind.ERC20,
                    evm_inquirer=self.ethereum_inquirer,
                )
                token0 = self.eth if token0 == A_WETH else token0
            elif other_log.topics[0] == TRANSFER_SIGNATURE and hex_or_bytes_to_int(other_log.data[:32]) == amount1_raw:  # noqa: E501
                token1 = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=other_log.address,
                    chain_id=ChainID.ETHEREUM,
                    token_kind=EvmTokenKind.ERC20,
                    evm_inquirer=self.ethereum_inquirer,
                )
                token1 = self.eth if token1 == A_WETH else token1

        if token0 is None or token1 is None:
            return None

        amount0 = asset_normalized_value(amount0_raw, token0)
        amount1 = asset_normalized_value(amount1_raw, token1)

        # Second, find already decoded events of the transfers and store the id to mutate after
        # confirmation that it is indeed Uniswap V2 Pool.
        for idx, event in enumerate(decoded_events):
            resolved_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == from_event_type[0] and
                event.event_subtype == from_event_type[1] and
                resolved_asset == token0 and
                event.balance.amount == asset_normalized_value(amount0_raw, resolved_asset)
            ):
                event0_idx = idx

            elif (
                event.event_type == from_event_type[0] and
                event.event_subtype == from_event_type[1] and
                resolved_asset == token1 and
                event.balance.amount == asset_normalized_value(amount1_raw, resolved_asset)
            ):
                event1_idx = idx

        # Finally, determine the pool address from the pair of token addresses, if it matches the one  # noqa: E501
        # found earlier, mutate the decoded event or create an action item where necessary.
        pool_address = self._compute_v2_pool_address(token0, token1)
        if pool_address == maybe_pool_address:
            for asset, decoded_event_idx, amount in [(token0, event0_idx, amount0), (token1, event1_idx, amount1)]:  # noqa: E501
                if decoded_event_idx is None:
                    action_item = ActionItem(
                        action='transform',
                        sequence_index=tx_log.log_index,
                        from_event_type=from_event_type[0],
                        from_event_subtype=from_event_type[1],
                        asset=asset,
                        amount=amount,
                        to_event_type=to_event_type[0],
                        to_event_subtype=to_event_type[1],
                        to_notes=notes.format(amount, asset.symbol, pool_address),
                        to_counterparty=CPT_UNISWAP_V2,
                    )
                    action_items.append(action_item)
                    continue

                decoded_events[decoded_event_idx].counterparty = CPT_UNISWAP_V2
                decoded_events[decoded_event_idx].event_type = to_event_type[0]
                decoded_events[decoded_event_idx].event_subtype = to_event_type[1]
                decoded_events[decoded_event_idx].notes = notes.format(amount, asset.symbol, pool_address)  # noqa: E501

        return None

    @staticmethod
    def _compute_v2_pool_address(token0: CryptoAsset, token1: CryptoAsset) -> ChecksumEvmAddress:
        """
        Compute the Uniswap V2 pool address using CREATE2.

        May raise:
        - DeserializationError
        """
        try:
            token0 = A_WETH.resolve_to_evm_token() if token0 == A_ETH else token0.resolve_to_evm_token()  # noqa: E501
            token1 = A_WETH.resolve_to_evm_token() if token1 == A_ETH else token1.resolve_to_evm_token()  # noqa: E501
        except WrongAssetType:
            return ZERO_ADDRESS

        try:
            return generate_address_via_create2(
                address=UNISWAP_V2_FACTORY,
                # pylint: disable=no-value-for-parameter
                salt=Web3.toHex(Web3.solidityKeccak(abi_types=['address', 'address'], values=[token0.evm_address, token1.evm_address])),  # noqa: E501
                init_code=UNISWAP_V2_INIT_CODE_HASH,
                is_init_code_hashed=True,
            )
        except DeserializationError:
            return ZERO_ADDRESS

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_UNISWAP_V2]
