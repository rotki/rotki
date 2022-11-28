import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.decoding.constants import NAUGHTY_ERC721
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, EvmTokenKind, EvmTransaction, Location
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int, ts_sec_to_ms

from .constants import (
    CPT_GNOSIS_CHAIN,
    ERC20_APPROVE,
    ERC20_OR_ERC721_TRANSFER,
    GNOSIS_CHAIN_BRIDGE_RECEIVE,
    GOVERNORALPHA_PROPOSE,
    GOVERNORALPHA_PROPOSE_ABI,
    GTC_CLAIM,
    ONEINCH_CLAIM,
)
from .utils import address_is_exchange

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_inquirer: 'EthereumInquirer',
            transactions: 'EthereumTransactions',
    ):
        super().__init__(
            database=database,
            evm_inquirer=ethereum_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[  # rules to try for all tx receipt logs decoding
                self._maybe_decode_erc20_approve,
                self._maybe_decode_erc20_721_transfer,
                self._maybe_enrich_transfers,
                self._maybe_decode_governance,
            ],
            misc_counterparties=[CPT_GNOSIS_CHAIN],
            address_is_exchange_fn=address_is_exchange,
        )

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_APPROVE or token is None:
            return None

        if len(tx_log.topics) == 3:
            owner_address = hex_or_bytes_to_address(tx_log.topics[1])
            spender_address = hex_or_bytes_to_address(tx_log.topics[2])
            amount_raw = hex_or_bytes_to_int(tx_log.data)
        elif len(tx_log.topics) == 1 and len(tx_log.data) == 96:  # malformed erc20 approve (finance.vote)  # noqa: E501
            owner_address = hex_or_bytes_to_address(tx_log.data[:32])
            spender_address = hex_or_bytes_to_address(tx_log.data[32:64])
            amount_raw = hex_or_bytes_to_int(tx_log.data[64:])
        else:
            log.debug(
                f'Got an ERC20 approve event with unknown structure '
                f'in transaction {transaction.tx_hash.hex()}',
            )
            return None

        if not any(self.base.is_tracked(x) for x in (owner_address, spender_address)):
            return None

        amount = token_normalized_value(token_amount=amount_raw, token=token)
        prefix = f'Revoke {token.symbol} approval' if amount == ZERO else f'Approve {amount} {token.symbol}'  # noqa: E501
        notes = f'{prefix} of {owner_address} for spending by {spender_address}'
        return HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=self.base.get_sequence_index(tx_log),
            timestamp=ts_sec_to_ms(transaction.timestamp),
            location=Location.BLOCKCHAIN,
            location_label=owner_address,
            asset=token,
            balance=Balance(amount=amount),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            counterparty=spender_address,
        )

    def _maybe_decode_erc20_721_transfer(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return None

        if tx_log.address in NAUGHTY_ERC721 or len(tx_log.topics) == 4:  # typical ERC721 has 3 indexed args  # noqa: E501
            token_kind = EvmTokenKind.ERC721
        elif len(tx_log.topics) == 3:  # typical ERC20 has 2 indexed args
            token_kind = EvmTokenKind.ERC20
        else:
            log.debug(f'Failed to decode token with address {tx_log.address} due to inability to match token type')  # noqa: E501
            return None

        if token is None:
            try:
                found_token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=tx_log.address,
                    chain_id=ChainID.ETHEREUM,
                    token_kind=token_kind,
                    evm_inquirer=self.evm_inquirer,
                )
            except NotERC20Conformant:
                return None  # ignore non-ERC20 transfers for now
        else:
            found_token = token

        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
        )
        if transfer is None:
            return None

        for idx, action_item in enumerate(action_items):
            if action_item.asset == found_token and action_item.amount == transfer.balance.amount and action_item.from_event_type == transfer.event_type and action_item.from_event_subtype == transfer.event_subtype:  # noqa: E501
                if action_item.action == 'skip':
                    action_items.pop(idx)
                    return None

                # else atm only transform
                if action_item.to_event_type is not None:
                    transfer.event_type = action_item.to_event_type
                if action_item.to_event_subtype is not None:
                    transfer.event_subtype = action_item.to_event_subtype
                if action_item.to_notes is not None:
                    transfer.notes = action_item.to_notes
                if action_item.to_counterparty is not None:
                    transfer.counterparty = action_item.to_counterparty
                if action_item.extra_data is not None:
                    transfer.extra_data = action_item.extra_data

                if action_item.paired_event_data is not None:
                    # If there is a paired event to this, take care of the order
                    out_event = transfer
                    in_event = action_item.paired_event_data[0]
                    if action_item.paired_event_data[1] is True:
                        out_event = action_item.paired_event_data[0]
                        in_event = transfer
                    maybe_reshuffle_events(
                        out_event=out_event,
                        in_event=in_event,
                        events_list=decoded_events + [transfer],
                    )

                action_items.pop(idx)
                break  # found an action item and acted on it

        # Add additional information to transfers for different protocols
        self._enrich_protocol_tranfers(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
            event=transfer,
            action_items=action_items,
            all_logs=all_logs,
        )
        return transfer

    def _maybe_enrich_transfers(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] == GTC_CLAIM and tx_log.address == '0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_GTC and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} GTC from the GTC airdrop'
            return None

        if tx_log.topics[0] == ONEINCH_CLAIM and tx_log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} 1INCH from the 1INCH airdrop'  # noqa: E501
            return None

        if tx_log.topics[0] == GNOSIS_CHAIN_BRIDGE_RECEIVE and tx_log.address == '0x88ad09518695c6c3712AC10a214bE5109a655671':  # noqa: E501
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        next(iter(self.decoders.values())).notify_user(
                            event=event,
                            counterparty=CPT_GNOSIS_CHAIN,
                        )
                        continue

                    # user bridged from gnosis chain
                    event.event_type = HistoryEventType.TRANSFER
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = CPT_GNOSIS_CHAIN
                    event.notes = (
                        f'Bridge {event.balance.amount} {crypto_asset.symbol} from gnosis chain'
                    )

        return None

    def _enrich_protocol_tranfers(  # pylint: disable=no-self-use
            self,
            token: EvmToken,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> None:
        """
        Decode special transfers made by contract execution for example at the moment
        of depositing assets or withdrawing.
        It assumes that the event being decoded has been already filtered and is a
        transfer.
        """
        for enrich_call in self.token_enricher_rules:
            try:
                transfer_enriched = enrich_call(
                    token=token,
                    tx_log=tx_log,
                    transaction=transaction,
                    event=event,
                    action_items=action_items,
                    all_logs=all_logs,
                )
            except (UnknownAsset, WrongAssetType) as e:
                log.error(
                    f'Failed to enrich transfer due to unknown asset {event.asset}. {str(e)}',
                )
                # Don't try other rules since all of them will fail to resolve the asset
                break

            if transfer_enriched:
                break

    def _maybe_decode_governance(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] == GOVERNORALPHA_PROPOSE:
            if tx_log.address == '0xDbD27635A534A3d3169Ef0498beB56Fb9c937489':
                governance_name = 'Gitcoin'
            else:
                governance_name = tx_log.address

            try:
                _, decoded_data = decode_event_data_abi_str(tx_log, GOVERNORALPHA_PROPOSE_ABI)
            except DeserializationError as e:
                log.debug(f'Failed to decode governor alpha event due to {str(e)}')
                return None

            proposal_id = decoded_data[0]
            proposal_text = decoded_data[8]
            notes = f'Create {governance_name} proposal {proposal_id}. {proposal_text}'
            return HistoryBaseEntry(
                event_identifier=transaction.tx_hash,
                sequence_index=self.base.get_sequence_index(tx_log),
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.BLOCKCHAIN,
                location_label=transaction.from_address,
                # TODO: This should be null for proposals and other informational events
                asset=A_ETH,
                balance=Balance(),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.GOVERNANCE_PROPOSE,
                counterparty=governance_name,
            )

        return None
