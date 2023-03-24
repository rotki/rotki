import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

from .constants import (
    CPT_GNOSIS_CHAIN,
    ETHADDRESS_TO_KNOWN_NAME,
    GNOSIS_CHAIN_BRIDGE_RECEIVE,
    GOVERNORALPHA_PROPOSE,
    GOVERNORALPHA_PROPOSE_ABI,
    GTC_CLAIM,
    ONEINCH_CLAIM,
)

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
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
                self._maybe_decode_governance,
                self._maybe_enrich_transfers,
            ],
            misc_counterparties=[CPT_GNOSIS_CHAIN],
        )

    def _maybe_enrich_transfers(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] == GTC_CLAIM and tx_log.address == '0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_GTC and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} GTC from the GTC airdrop'
            return DEFAULT_DECODING_OUTPUT

        if tx_log.topics[0] == ONEINCH_CLAIM and tx_log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} 1INCH from the 1INCH airdrop'  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

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
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = CPT_GNOSIS_CHAIN
                    event.notes = (
                        f'Bridge {event.balance.amount} {crypto_asset.symbol} from gnosis chain'
                    )

        return DEFAULT_DECODING_OUTPUT

    def _maybe_decode_governance(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] == GOVERNORALPHA_PROPOSE:
            if tx_log.address == '0xDbD27635A534A3d3169Ef0498beB56Fb9c937489':
                governance_name = 'Gitcoin'
            else:
                governance_name = tx_log.address

            try:
                _, decoded_data = decode_event_data_abi_str(tx_log, GOVERNORALPHA_PROPOSE_ABI)
            except DeserializationError as e:
                log.debug(f'Failed to decode governor alpha event due to {str(e)}')
                return DEFAULT_DECODING_OUTPUT

            proposal_id = decoded_data[0]
            proposal_text = decoded_data[8]
            notes = f'Create {governance_name} proposal {proposal_id}. {proposal_text}'
            event = self.base.make_event_from_transaction(
                transaction=transaction,
                tx_log=tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.GOVERNANCE,
                asset=A_ETH,
                balance=Balance(),
                location_label=transaction.from_address,
                notes=notes,
                address=tx_log.address,
                counterparty=governance_name,
            )
            return DecodingOutput(event=event)

        return DEFAULT_DECODING_OUTPUT

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: EnricherContext) -> Optional[str]:
        for enrich_call in self.rules.token_enricher_rules:
            try:
                transfer_enrich: TransferEnrichmentOutput = enrich_call(context)
            except (UnknownAsset, WrongAssetType) as e:
                log.error(
                    f'Failed to enrich transfer due to unknown asset '
                    f'{context.event.asset}. {str(e)}',
                )
                # Don't try other rules since all of them will fail to resolve the asset
                return None

            if transfer_enrich.matched_counterparty is not None:
                return transfer_enrich.matched_counterparty

        return None

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:
        return address in (
            # Cryptovoxels
            string_to_evm_address('0x4243a8413A77Eb559c6f8eAFfA63F46019056d08'),
        )

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:
        name = ETHADDRESS_TO_KNOWN_NAME.get(address)
        if name and 'Kraken' in name:
            return CPT_KRAKEN
        return None
