from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import EthereumTransaction, Location
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


# keccak of Transfer(address,address,uint256)
ERC20_TRANSFER = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501


class EVMTransactionDecoder():

    def __init__(self, database: 'DBHandler'):
        self.database = database
        self.tracked_accounts = self.database.get_blockchain_accounts()
        self.event_rules = (
            self._maybe_decode_erc20_approve,
            self._maybe_decode_erc20_transfer,
        )

    def try_all_rules(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        for rule in self.event_rules:
            event = rule(token=token, log=log, transaction=transaction)
            if event:
                return event

        return None

    def decode_transaction(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes an ethereum transaction and its receipt and saves result in the DB
        """
        cursor = self.database.conn.cursor()
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor.execute('DELETE FROM history_events WHERE event_identifier=?', (tx_hex,))
        cursor.execute(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        events = []
        for tx_log in tx_receipt.logs:
            token = GlobalDBHandler.get_ethereum_token(tx_log.address)
            event = self.try_all_rules(token=token, log=tx_log, transaction=transaction)
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
            )
            return events

        # else we should decode now
        events = self.decode_transaction(transaction, tx_receipt)
        return events

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_APPROVE or token is None:
            return None

        owner_adddress = hex_or_bytes_to_address(log.topics[1])
        spender_adddress = hex_or_bytes_to_address(log.topics[2])

        if not any(x in self.tracked_accounts.eth for x in (owner_adddress, spender_adddress)):
            return None

        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Approve {amount} {token.symbol} of {owner_adddress} for spending by {spender_adddress}'  # noqa: E501
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=log.log_index,
            timestamp=transaction.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=owner_adddress,
            asset_balance=AssetBalance(asset=token, balance=Balance(amount=amount)),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            counterparty=spender_adddress,
        )

    def _maybe_decode_erc20_transfer(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_TRANSFER or token is None:
            return None

        from_adddress = hex_or_bytes_to_address(log.topics[1])
        to_adddress = hex_or_bytes_to_address(log.topics[2])

        tracked_from = from_adddress in self.tracked_accounts.eth
        tracked_to = to_adddress in self.tracked_accounts.eth
        if not tracked_from and not tracked_to:
            return None

        if tracked_from and tracked_to:
            event_type = HistoryEventType.TRANSFER
            location_label = from_adddress
            counterparty = to_adddress
        elif tracked_from:
            event_type = HistoryEventType.SPEND
            location_label = from_adddress
            counterparty = to_adddress
        else:  # can only be tracked_to
            event_type = HistoryEventType.RECEIVE
            location_label = to_adddress
            counterparty = from_adddress

        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Transfer {amount} {token.symbol} {from_adddress} -> {to_adddress}'
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
