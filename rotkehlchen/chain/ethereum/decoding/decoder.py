import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN, CPT_POLONIEX, CPT_UPHOLD
from rotkehlchen.chain.ethereum.modules.eth2.beacon import BeaconNode
from rotkehlchen.chain.ethereum.modules.eth2.utils import timestamp_to_slot
from rotkehlchen.chain.ethereum.modules.monerium.constants import V1_TO_V2_MONERIUM_MAPPINGS
from rotkehlchen.chain.evm.constants import MERKLE_CLAIM
from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderToolsWithProxy
from rotkehlchen.chain.evm.decoding.constants import CPT_ACCOUNT_DELEGATION
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoderWithDSProxy
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int_from_str
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import from_wei, ts_sec_to_ms

from .constants import (
    AIRDROP_CLAIM,
    GNOSIS_CPT_DETAILS,
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
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumTransactionDecoder(EVMTransactionDecoderWithDSProxy):

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_inquirer: 'EthereumInquirer',
            transactions: 'EthereumTransactions',
            beacon_chain: 'BeaconChain | None' = None,
            premium: 'Premium | None' = None,
    ):
        self.beacon_node: BeaconNode | None = None
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
            base_tools=BaseEvmDecoderToolsWithProxy(
                database=database,
                evm_inquirer=ethereum_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
                exceptions_mappings=V1_TO_V2_MONERIUM_MAPPINGS,
            ),
            premium=premium,
            beacon_chain=beacon_chain,
        )

    def _get_beacon_node(self) -> BeaconNode | None:
        if self.beacon_node is not None:
            return self.beacon_node

        rpc_endpoint = CachedSettings().get_entry('beacon_rpc_endpoint')
        if not isinstance(rpc_endpoint, str) or rpc_endpoint == '':
            return None

        try:
            self.beacon_node = BeaconNode(rpc_endpoint=rpc_endpoint)
        except RemoteError as e:
            log.error(f'Failed to connect to beacon node for produced block fallback due to {e!s}')
            return None

        return self.beacon_node

    def _maybe_create_produced_block_event_from_eth_receive(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """Use execution and CL nodes as a beaconcha.in-less fallback for MEV rewards."""
        if (
                len(decoded_events) == 0 or
                any(
                    event.asset != A_ETH or
                    event.event_type != HistoryEventType.RECEIVE or
                    event.event_subtype != HistoryEventSubType.NONE or
                    event.counterparty is not None
                    for event in decoded_events
                ) or
                self.beacon_chain is None or
                self.beacon_chain.has_api_key() is True
        ):
            return

        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT H.identifier, H.amount FROM eth_staking_events_info S JOIN '
                'history_events H ON H.identifier = S.identifier WHERE '
                'S.is_exit_or_blocknumber = ? AND H.subtype = ?',
                (transaction.block_number, HistoryEventSubType.MEV_REWARD.serialize()),
            )
            if (existing_mev_event := cursor.fetchone()) is not None:
                with self.database.user_write() as write_cursor:
                    write_cursor.execute(
                        'UPDATE history_events SET amount = ? WHERE identifier = ?',
                        (
                            str(FVal(existing_mev_event[1]) + sum(
                                (event.amount for event in decoded_events),
                                start=ZERO,
                            )),
                            existing_mev_event[0],
                        ),
                    )
                return

        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT EXISTS(SELECT 1 FROM eth2_validators WHERE '
                '(activation_timestamp IS NULL OR activation_timestamp <= ?) AND '
                '(exited_timestamp IS NULL OR exited_timestamp > ?))',
                (transaction.timestamp, transaction.timestamp),
            )
            if cursor.fetchone()[0] == 0:
                return

        if (beacon_node := self._get_beacon_node()) is None:
            return

        try:
            proposer_index = beacon_node.query_block_proposer(
                slot=timestamp_to_slot(transaction.timestamp),
            )
        except (ValueError, RemoteError) as e:
            log.error(f'Failed to query produced block fallback for {transaction.tx_hash!s} due to {e!s}')  # noqa: E501
            return

        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT EXISTS(SELECT 1 FROM eth2_validators WHERE validator_index = ? AND '
                '(activation_timestamp IS NULL OR activation_timestamp <= ?) AND '
                '(exited_timestamp IS NULL OR exited_timestamp > ?))',
                (proposer_index, transaction.timestamp, transaction.timestamp),
            )
            if cursor.fetchone()[0] == 0:
                return

        recipients = {event.location_label for event in decoded_events}
        if len(recipients) != 1:
            log.error(f'Failed to determine produced block fallback recipient for {transaction.tx_hash!s}')  # noqa: E501
            return

        if (fee_recipient_raw := next(iter(recipients))) is None:
            return

        try:
            fee_recipient = deserialize_evm_address(fee_recipient_raw)
        except DeserializationError as e:
            log.error(f'Failed to deserialize produced block fallback recipient for {transaction.tx_hash!s} due to {e!s}')  # noqa: E501
            return

        with self.database.conn.read_ctx() as cursor:
            ethereum_tracked_accounts = self.database.get_blockchain_accounts(cursor).get(self.evm_inquirer.blockchain)  # noqa: E501
            cursor.execute(
                'SELECT EXISTS(SELECT 1 FROM eth_staking_events_info S JOIN history_events H '
                'ON H.identifier = S.identifier WHERE S.is_exit_or_blocknumber = ? AND '
                'H.subtype = ?)',
                (transaction.block_number, HistoryEventSubType.BLOCK_PRODUCTION.serialize()),
            )
            has_block_production_event = cursor.fetchone()[0] == 1

        with self.database.user_write() as write_cursor:
            if has_block_production_event is False:
                try:
                    block_reward_data = self.evm_inquirer.etherscan.get_block_reward(
                        chain_id=self.evm_inquirer.chain_id,
                        block_number=transaction.block_number,
                    )
                    block_fee_recipient = deserialize_evm_address(block_reward_data['blockMiner'])
                    block_reward = from_wei(deserialize_int_from_str(
                        symbol=block_reward_data['blockReward'],
                        location='etherscan block reward',
                    ))
                except (KeyError, DeserializationError, RemoteError) as e:
                    log.error(f'Failed to query produced block fallback reward for {transaction.tx_hash!s} due to {e!s}')  # noqa: E501
                else:
                    self.dbevents.add_history_event(write_cursor=write_cursor, event=EthBlockEvent(
                        validator_index=proposer_index,
                        timestamp=ts_sec_to_ms(transaction.timestamp),
                        amount=block_reward,
                        fee_recipient=block_fee_recipient,
                        fee_recipient_tracked=block_fee_recipient in ethereum_tracked_accounts,
                        block_number=transaction.block_number,
                        is_mev_reward=False,
                    ))

            self.dbevents.add_history_event(write_cursor=write_cursor, event=EthBlockEvent(
                validator_index=proposer_index,
                timestamp=ts_sec_to_ms(transaction.timestamp),
                amount=sum((event.amount for event in decoded_events), start=ZERO),
                fee_recipient=fee_recipient,
                fee_recipient_tracked=fee_recipient in ethereum_tracked_accounts,
                block_number=transaction.block_number,
                is_mev_reward=True,
            ))

    def _decode_transaction(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> tuple[list['EvmEvent'], bool, set[str] | None]:
        decoded_events, refresh_balances, reload_decoders = super()._decode_transaction(
            transaction=transaction,
            tx_receipt=tx_receipt,
        )
        self._maybe_create_produced_block_event_from_eth_receive(
            transaction=transaction,
            decoded_events=decoded_events,
        )
        return decoded_events, refresh_balances, reload_decoders

    def _maybe_enrich_transfers(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        if tx_log.topics[0] == AIRDROP_CLAIM and tx_log.address == '0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_GTC and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.amount} GTC from the GTC airdrop'
                    event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'gitcoin'}
            return DEFAULT_EVM_DECODING_OUTPUT

        if tx_log.topics[0] == MERKLE_CLAIM and tx_log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.amount} 1INCH from the 1INCH airdrop'
                    event.extra_data = {AIRDROP_IDENTIFIER_KEY: '1inch'}
            return DEFAULT_EVM_DECODING_OUTPUT

        return DEFAULT_EVM_DECODING_OUTPUT

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
