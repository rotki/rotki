from typing import TYPE_CHECKING, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import decode_event_data, token_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Location
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


# keccak of Transfer(address,address,uint256)
ERC20_TRANSFER = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501
GTC_CLAIM = b'\x04g R\xdc\xb6\xb5\xb1\x9a\x9c\xc2\xec\x1b\x8fD\x7f\x1f^G\xb5\xe2L\xfa^O\xfbd\rc\xca+\xe7'  # noqa: E501
ONEINCH_CLAIM = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501
XDAI_BRIDGE_RECEIVE = b'\x9a\xfdG\x90~%\x02\x8c\xda\xca\x89\xd1\x93Q\x8c0+\xbb\x12\x86\x17\xd5\xa9\x92\xc5\xab\xd4X\x15Re\x93'  # noqa: E501
GOVERNORALPHA_PROPOSE = b"}\x84\xa6&:\xe0\xd9\x8d3)\xbd{F\xbbN\x8do\x98\xcd5\xa7\xad\xb4\\'L\x8b\x7f\xd5\xeb\xd5\xe0"  # noqa: E501
GOVERNORALPHA_PROPOSE_ABI = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":false,"internalType":"address","name":"proposer","type":"address"},{"indexed":false,"internalType":"address[]","name":"targets","type":"address[]"},{"indexed":false,"internalType":"uint256[]","name":"values","type":"uint256[]"},{"indexed":false,"internalType":"string[]","name":"signatures","type":"string[]"},{"indexed":false,"internalType":"bytes[]","name":"calldatas","type":"bytes[]"},{"indexed":false,"internalType":"uint256","name":"startBlock","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"endBlock","type":"uint256"},{"indexed":false,"internalType":"string","name":"description","type":"string"}],"name":"ProposalCreated","type":"event"}'  # noqa: E501


class EVMTransactionDecoder():

    def __init__(self, database: 'DBHandler'):
        self.database = database
        self.tracked_accounts = self.database.get_blockchain_accounts()
        self.event_rules = (  # rules for tx receipt logs decoding
            self._maybe_decode_erc20_approve,
            self._maybe_decode_erc20_transfer,
            self._maybe_enrich_transfers,
            self._maybe_decode_governance,
        )

    def try_all_rules(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: List[HistoryBaseEntry],
    ) -> Optional[HistoryBaseEntry]:
        for rule in self.event_rules:
            event = rule(token=token, log=log, transaction=transaction, decoded_events=decoded_events)  # noqa: E501
            if event:
                return event

        return None

    def decode_transaction(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes an ethereum transaction and its receipt and saves result in the DB"""
        cursor = self.database.conn.cursor()
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor.execute('DELETE FROM history_events WHERE event_identifier=?', (tx_hex,))
        cursor.execute(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        events = []
        # check if any eth transfer happened in the transaction
        event = self._maybe_decode_simple_transactions(transaction)
        if event is not None:
            events.append(event)

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            token = GlobalDBHandler.get_ethereum_token(tx_log.address)
            event = self.try_all_rules(token=token, log=tx_log, transaction=transaction, decoded_events=events)  # noqa: E501
            if event:
                events.append(event)

        self.database.add_history_events(events)
        cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_hash, blockchain, value) VALUES(?, ?, ?)',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        self.database.update_last_write()
        return events

    def decode_transaction_hashes(self, hashes: List[bytes]) -> None:
        """Runs the decoding logic for a number of transaction hashes

        Caller must make sure that:
        - The transaction hashes must exist in the DB for transactions
        - The transaction hashes must also have the corresponding receipts in the DB
        """
        # TODO: Change this if transaction filter query can accept multiple hashes
        dbethtx = DBEthTx(self.database)
        for tx_hash in hashes:
            txs = dbethtx.get_ethereum_transactions(
                filter_=ETHTransactionsFilterQuery.make(tx_hash=tx_hash),
                has_premium=True,  # ignore limiting here
            )
            tx_receipt = dbethtx.get_receipt(tx_hash)
            assert tx_receipt, 'The transaction receipt for {tx_hash.hex()} should be in the DB'
            self.decode_transaction(transaction=txs[0], tx_receipt=tx_receipt)

    def get_or_decode_transaction_events(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor = self.database.conn.cursor()
        results = cursor.execute(
            'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        if results.fetchone()[0] != 0:  # already decoded and in the DB
            events = self.database.get_history_events(
                filter_query=HistoryEventFilterQuery.make(
                    event_identifier=tx_hex,
                ),
                has_premium=True,  # for this function we don't limit anything
            )
            return events

        # else we should decode now
        events = self.decode_transaction(transaction, tx_receipt)
        return events

    def _decode_direction(
            self,
            from_address: ChecksumEthAddress,
            to_address: ChecksumEthAddress,
    ) -> Optional[Tuple[HistoryEventType, str, str]]:
        tracked_from = from_address in self.tracked_accounts.eth
        tracked_to = to_address in self.tracked_accounts.eth
        if not tracked_from and not tracked_to:
            return None

        if tracked_from and tracked_to:
            event_type = HistoryEventType.TRANSFER
            location_label = from_address
            counterparty = to_address
        elif tracked_from:
            event_type = HistoryEventType.SPEND
            location_label = from_address
            counterparty = to_address
        else:  # can only be tracked_to
            event_type = HistoryEventType.RECEIVE
            location_label = to_address
            counterparty = from_address

        return event_type, location_label, counterparty

    def _maybe_decode_simple_transactions(
            self,
            tx: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if tx.from_address not in self.tracked_accounts.eth:
                return None
            return HistoryBaseEntry(  # contract deployment
                event_identifier='0x' + tx.tx_hash.hex(),
                sequence_index=0,
                timestamp=tx.timestamp,
                location=Location.BLOCKCHAIN,
                location_label=tx.from_address,
                asset_balance=AssetBalance(asset=A_ETH, balance=Balance(amount=amount)),
                notes='Contract deployment',
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                counterparty=None,  # TODO: Find out contract address
            )

        if amount == ZERO:
            return None

        direction_result = self._decode_direction(tx.from_address, tx.to_address)
        if direction_result is None:
            return None

        event_type, location_label, counterparty = direction_result
        return HistoryBaseEntry(
            event_identifier='0x' + tx.tx_hash.hex(),
            sequence_index=0,
            timestamp=tx.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset_balance=AssetBalance(asset=A_ETH, balance=Balance(amount=amount)),
            notes=f'Transfer {amount} ETH {tx.from_address} -> {tx.to_address}',
            event_type=event_type,
            event_subtype=None,
            counterparty=counterparty,
        )

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: [HistoryBaseEntry],
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_APPROVE or token is None:
            return None

        owner_address = hex_or_bytes_to_address(log.topics[1])
        spender_address = hex_or_bytes_to_address(log.topics[2])

        if not any(x in self.tracked_accounts.eth for x in (owner_address, spender_address)):
            return None

        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Approve {amount} {token.symbol} of {owner_address} for spending by {spender_address}'  # noqa: E501
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=log.log_index,
            timestamp=transaction.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=owner_address,
            asset_balance=AssetBalance(asset=token, balance=Balance(amount=amount)),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            counterparty=spender_address,
        )

    def _maybe_decode_erc20_transfer(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: [HistoryBaseEntry],
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_TRANSFER or token is None:
            return None

        from_address = hex_or_bytes_to_address(log.topics[1])
        to_address = hex_or_bytes_to_address(log.topics[2])
        direction_result = self._decode_direction(from_address, to_address)
        if direction_result is None:
            return None

        event_type, location_label, counterparty = direction_result
        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Transfer {amount} {token.symbol} {from_address} -> {to_address}'
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=log.log_index,
            timestamp=transaction.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset_balance=AssetBalance(asset=token, balance=Balance(amount=amount)),
            notes=notes,
            event_type=event_type,
            event_subtype=None,
            counterparty=counterparty,
        )

    def _maybe_enrich_transfers(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: [HistoryBaseEntry],
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] == GTC_CLAIM and log.address == '0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E':  # noqa: E501
            for event in decoded_events:
                if event.asset_balance.asset == A_GTC and event.event_type == HistoryEventType.RECEIVE:  # noqa: E501
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.asset_balance.balance.amount} GTC from the GTC airdrop'  # noqa: E501
            return None
        elif log.topics[0] == ONEINCH_CLAIM and log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset_balance.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:  # noqa: E501
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.asset_balance.balance.amount} 1INCH from the 1INCH airdrop'  # noqa: E501
            return None
        elif log.topics[0] == XDAI_BRIDGE_RECEIVE and log.address == '0x88ad09518695c6c3712AC10a214bE5109a655671':  # noqa: E501
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE:
                    # user bridged from xdai
                    event.event_type = HistoryEventType.TRANSFER
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = 'XDAI'
                    event.notes = (
                        f'Bridge {event.asset_balance.balance.amount} '
                        f'{event.asset_balance.asset.symbol} from XDAI'
                    )

        return None

    def _maybe_decode_governance(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: [HistoryBaseEntry],
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] == GOVERNORALPHA_PROPOSE:
            if log.address == '0xDbD27635A534A3d3169Ef0498beB56Fb9c937489':
                governance_name = 'Gitcoin'
            else:
                governance_name = log.address

            try:
                _, decoded_data = decode_event_data(log, GOVERNORALPHA_PROPOSE_ABI)
            except DeserializationError as e:
                log.debug(f'Failed to decode governor alpha event due to {e}')
                return None

            proposal_id = decoded_data[0]
            proposal_text = decoded_data[8]
            notes = f'Created {governance_name} proposal {proposal_id}. {proposal_text}'
            return HistoryBaseEntry(
                event_identifier='0x' + transaction.tx_hash.hex(),
                sequence_index=log.log_index,
                timestamp=transaction.timestamp,
                location=Location.BLOCKCHAIN,
                location_label=transaction.from_address,
                # TODO: This should be null for proposals when possible
                asset_balance=AssetBalance(asset=A_ETH, balance=Balance()),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.GOVERNANCE_PROPOSE,
                counterparty=governance_name,
            )

        return None
