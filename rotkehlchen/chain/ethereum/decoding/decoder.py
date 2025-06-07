import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN, CPT_POLONIEX, CPT_UPHOLD
from rotkehlchen.chain.ethereum.modules.monerium.constants import V1_TO_V2_MONERIUM_MAPPINGS
from rotkehlchen.chain.evm.constants import MERKLE_CLAIM
from rotkehlchen.chain.evm.decoding.base import BaseDecoderToolsWithDSProxy
from rotkehlchen.chain.evm.decoding.constants import CPT_ACCOUNT_DELEGATION
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoderWithDSProxy
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

from .constants import (
    GNOSIS_CPT_DETAILS,
    GTC_CLAIM,
    KRAKEN_ADDRESSES,
    POLONIEX_ADDRESS,
    UPHOLD_ADDRESS,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumTransactionDecoder(EVMTransactionDecoderWithDSProxy):

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_inquirer: 'EthereumInquirer',
            transactions: 'EthereumTransactions',
            beacon_chain: 'BeaconChain | None' = None,
    ):
        super().__init__(
            database=database,
            evm_inquirer=ethereum_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[  # rules to try for all tx receipt logs decoding
                self._maybe_enrich_transfers,
            ],
            misc_counterparties=[
                GNOSIS_CPT_DETAILS,
                CounterpartyDetails(
                    identifier=CPT_KRAKEN,
                    label='Kraken',
                    image='kraken.svg',
                ), CounterpartyDetails(
                    identifier=CPT_POLONIEX,
                    label='Poloniex',
                    image='poloniex.svg',
                ), CounterpartyDetails(
                    identifier=CPT_UPHOLD,
                    label='Uphold.com',
                    image='uphold.svg',
                ), CounterpartyDetails(
                    identifier=CPT_ACCOUNT_DELEGATION,
                    label='Account delegation',
                    image='account_delegation.svg',
                ),
            ],
            base_tools=BaseDecoderToolsWithDSProxy(
                database=database,
                evm_inquirer=ethereum_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
                exceptions_mappings=V1_TO_V2_MONERIUM_MAPPINGS,
            ),
            beacon_chain=beacon_chain,
        )

    def _maybe_enrich_transfers(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
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
                    event.notes = f'Claim {event.amount} GTC from the GTC airdrop'
                    event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'gitcoin'}
            return DEFAULT_DECODING_OUTPUT

        if tx_log.topics[0] == MERKLE_CLAIM and tx_log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.amount} 1INCH from the 1INCH airdrop'
                    event.extra_data = {AIRDROP_IDENTIFIER_KEY: '1inch'}
            return DEFAULT_DECODING_OUTPUT

        return DEFAULT_DECODING_OUTPUT

    # -- methods that need to be implemented by child classes --

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:
        return address == string_to_evm_address('0x4243a8413A77Eb559c6f8eAFfA63F46019056d08')

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:
        if address in KRAKEN_ADDRESSES:
            return CPT_KRAKEN
        elif address == UPHOLD_ADDRESS:
            return CPT_UPHOLD
        elif address == POLONIEX_ADDRESS:
            return CPT_POLONIEX

        return None
