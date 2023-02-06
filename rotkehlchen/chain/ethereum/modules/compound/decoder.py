import logging
from typing import Any, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_crypto_asset_by_symbol
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.assets import A_COMP
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import COMPTROLLER_PROXY_ADDRESS, CPT_COMPOUND

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MINT_COMPOUND_TOKEN = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
REDEEM_COMPOUND_TOKEN = b'\xe5\xb7T\xfb\x1a\xbb\x7f\x01\xb4\x99y\x1d\x0b\x82\n\xe3\xb6\xaf4$\xac\x1cYv\x8e\xdbS\xf4\xec1\xa9)'  # noqa: E501
DISTRIBUTED_SUPPLIER_COMP = b',\xae\xcd\x17\xd0/V\xfa\x89w\x05\xdc\xc7@\xda-#|7?phoN\r\x9b\xd3\xbf\x04\x00\xeaz'  # noqa: E501


class CompoundDecoder(DecoderInterface):

    def _decode_mint(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
            compound_token: EvmToken,
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        minter = hex_or_bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(minter):
            return None, []

        mint_amount_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        minted_amount_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        underlying_asset = get_crypto_asset_by_symbol(
            symbol=compound_token.symbol[1:],
            chain_id=compound_token.chain_id,
        )
        if underlying_asset is None:
            return None, []
        underlying_asset = underlying_asset.resolve_to_crypto_asset()

        mint_amount = asset_normalized_value(mint_amount_raw, underlying_asset)
        minted_amount = token_normalized_value(minted_amount_raw, compound_token)
        out_event = None
        for event in decoded_events:
            # Find the transfer event which should have come before the minting
            if event.event_type == HistoryEventType.SPEND and event.asset == underlying_asset and event.balance.amount == mint_amount:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_COMPOUND
                event.notes = f'Deposit {mint_amount} {underlying_asset.symbol} to compound'
                out_event = event
                break

        if out_event is None:
            log.debug(f'At compound mint decoding of tx {transaction.tx_hash.hex()} the out event was not found')  # noqa: E501
            return None, []

        # also create an action item for the receive of the cTokens
        action_item = ActionItem(
            action='transform',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=compound_token,
            amount=minted_amount,
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            to_notes=f'Receive {minted_amount} {compound_token.symbol} from compound',
            to_counterparty=CPT_COMPOUND,
            paired_event_data=(out_event, True),
        )
        return None, [action_item]

    def _decode_redeem(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
            compound_token: EvmToken,
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        redeemer = hex_or_bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(redeemer):
            return None, []

        redeem_amount_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        redeem_tokens_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        underlying_token = get_crypto_asset_by_symbol(
            symbol=compound_token.symbol[1:],
            chain_id=compound_token.chain_id,
        )
        if underlying_token is None:
            return None, []

        underlying_token = underlying_token.resolve_to_crypto_asset()
        redeem_amount = asset_normalized_value(redeem_amount_raw, underlying_token)
        redeem_tokens = token_normalized_value(redeem_tokens_raw, compound_token)
        out_event = in_event = None
        for event in decoded_events:
            # Find the transfer event which should have come before the redeeming
            if event.event_type == HistoryEventType.RECEIVE and event.asset == underlying_token and event.balance.amount == redeem_amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_COMPOUND
                event.notes = f'Withdraw {redeem_amount} {underlying_token.symbol} from compound'
                in_event = event
            if event.event_type == HistoryEventType.SPEND and event.asset == compound_token and event.balance.amount == redeem_tokens:  # noqa: E501
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_COMPOUND
                event.notes = f'Return {redeem_tokens} {compound_token.symbol} to compound'
                out_event = event

        maybe_reshuffle_events(out_event=out_event, in_event=in_event, events_list=decoded_events)
        return None, []

    def decode_compound_token_movement(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[list[ActionItem]],  # pylint: disable=unused-argument
            compound_token: EvmToken,
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] == MINT_COMPOUND_TOKEN:
            log.debug(f'Hash: {transaction.tx_hash.hex()}')
            return self._decode_mint(transaction=transaction, tx_log=tx_log, decoded_events=decoded_events, compound_token=compound_token)  # noqa: E501

        if tx_log.topics[0] == REDEEM_COMPOUND_TOKEN:
            return self._decode_redeem(tx_log=tx_log, decoded_events=decoded_events, compound_token=compound_token)  # noqa: E501

        return None, []

    def decode_comp_claim(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[list[ActionItem]],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        """Example tx:
        https://etherscan.io/tx/0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807
        """
        if tx_log.topics[0] != DISTRIBUTED_SUPPLIER_COMP:
            return None, []

        supplier_address = hex_or_bytes_to_address(tx_log.topics[2])
        if not self.base.is_tracked(supplier_address):
            return None, []

        comp_raw_amount = hex_or_bytes_to_int(tx_log.data[0:32])
        if comp_raw_amount == 0:
            return None, []  # do not count zero comp collection

        # A DistributedSupplierComp event can happen without a transfer. Just accrues
        # comp in the Comptroller until enough for a transfer is there. We should only
        # count a payout if the transfer occurs
        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == supplier_address and event.asset == A_COMP and event.counterparty == COMPTROLLER_PROXY_ADDRESS:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_COMPOUND
                event.notes = f'Collect {event.balance.amount} COMP from compound'
                break

        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        compound_tokens = GlobalDBHandler().get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='compound',
        )
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        for token in compound_tokens:
            if token == A_COMP:
                continue

            mapping[token.evm_address] = (self.decode_compound_token_movement, token)
        mapping[COMPTROLLER_PROXY_ADDRESS] = (self.decode_comp_claim,)
        return mapping

    def counterparties(self) -> list[str]:
        return [CPT_COMPOUND]
