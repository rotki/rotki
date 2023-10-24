from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.freeze_time('2023-10-25 22:50:45 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x0D0B3A4fB611D11b044444Ed2154cDcd7830d506', '0xdFba7a5EeE7b2Aed0E463e983CB96873DbDD25F0']])  # noqa: E501
def test_gnosischain_specific_chain_data(
        database: 'DBHandler',
        gnosis_transactions: 'GnosisTransactions',
        gnosis_accounts: list[ChecksumEvmAddress],
) -> None:
    now = ts_now()
    expected_hashes = [
        deserialize_evm_tx_hash('0xd7f2c2370d56b36ef4415d79f6f762d3c56dc28b6ca901a4caab8780b6f9d658'),
        deserialize_evm_tx_hash('0x0f31899a9c457fbc37b16fef4f9a19281989e5109fb69dc75b88b277b24adf0e'),
        deserialize_evm_tx_hash('0x3461f584d26a356fabe3f24c5dce60a5395f10924f346a4d44e22031a6d8173c'),
        deserialize_evm_tx_hash('0xc4d486ef5927973cb90aa9d18d5e8f5b768f31284d5d09d770b953f6f9b286a7'),
    ]

    def check_db() -> None:
        """Check that stuff are in the DB after onchain data query"""
        dbevmtx = DBEvmTx(database)
        with database.conn.read_ctx() as cursor:
            for tx_hash in expected_hashes:  # confirm hashes are in the DB
                assert len(dbevmtx.get_evm_transactions(
                    cursor=cursor,
                    filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=ChainID.GNOSIS),  # noqa: E501
                    has_premium=True,
                )) == 1
                assert dbevmtx.get_receipt(
                    cursor=cursor,
                    tx_hash=tx_hash,
                    chain_id=ChainID.GNOSIS,
                )

            for address in gnosis_accounts:
                # check used query ranges are set
                from_ts, to_ts = database.get_used_query_range(cursor, f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}')  # type: ignore # noqa: E501
                assert from_ts == Timestamp(0)
                assert to_ts == now

    get_logs_patch = patch.object(
        gnosis_transactions.evm_inquirer,
        '_get_logs',
        wraps=gnosis_transactions.evm_inquirer._get_logs,
    )

    with get_logs_patch as fn:
        gnosis_transactions.get_chain_specific_multiaddress_data(
            addresses=gnosis_accounts,
            from_ts=Timestamp(0),
            to_ts=now,
        )
        first_call_count = fn.call_count
        check_db()

        # call it again and make sure nothing happens and DB is unchanged
        gnosis_transactions.get_chain_specific_multiaddress_data(
            addresses=gnosis_accounts,
            from_ts=Timestamp(0),
            to_ts=now,
        )
        assert fn.call_count == first_call_count, 'no log queries should happen'
        check_db()
