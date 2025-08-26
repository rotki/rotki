from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.accountant import RemoteError
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.chain.gnosis.transactions import DEPLOYED_TS
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.freeze_time('2024-11-28 10:44:55 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0x2449fE0bEA58e027f374e90b296e72Dfd7bCcBaE']])  # noqa: E501
def test_gnosischain_specific_chain_data(
        database: 'DBHandler',
        gnosis_transactions: 'GnosisTransactions',
        gnosis_accounts: list[ChecksumEvmAddress],
) -> None:
    now = ts_now()
    start_ts = Timestamp(1711618437)
    expected_hashes = [
        deserialize_evm_tx_hash('0x53ea77773da6ea732a8037a6104439d00dd480c080ff72eb43659ceb3c84a49f'),
        deserialize_evm_tx_hash('0x580ff7e66b3d248e827ac4b9ac584a7548ef2b06bb5ac465f9a6fd8b3c16c20e'),
        deserialize_evm_tx_hash('0xd120b4923082c30710a06df21324c91b1886a0f6451336a98a2d9e6c5dcf42c0'),
        deserialize_evm_tx_hash('0xde1157f4e48bd6d053af43e9193c278959bd636207d0b38fe90e5201bc0e9664'),
    ]

    def check_db() -> None:
        """Check that stuff are in the DB after onchain data query"""
        dbevmtx = DBEvmTx(database)
        with database.conn.read_ctx() as cursor:
            for tx_hash in expected_hashes:  # confirm hashes are in the DB
                assert len(dbevmtx.get_evm_transactions(
                    cursor=cursor,
                    filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=ChainID.GNOSIS),  # noqa: E501
                )) == 1
                assert dbevmtx.get_receipt(
                    cursor=cursor,
                    tx_hash=tx_hash,
                    chain_id=ChainID.GNOSIS,
                )

            for address in gnosis_accounts:
                # check used query ranges are set
                from_ts, to_ts = database.get_used_query_range(cursor, f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}')  # type: ignore # noqa: E501
                assert from_ts == start_ts
                assert to_ts == now

    with database.user_write() as write_cursor:
        for address in gnosis_accounts:
            database.update_used_query_range(
                write_cursor=write_cursor,
                name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',
                start_ts=Timestamp(0),
                end_ts=Timestamp(1711618437),
            )
    gnosis_transactions.get_chain_specific_multiaddress_data(addresses=gnosis_accounts)
    check_db()


@pytest.mark.freeze_time('2023-10-25 22:50:45 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x0D0B3A4fB611D11b044444Ed2154cDcd7830d506', '0xdFba7a5EeE7b2Aed0E463e983CB96873DbDD25F0']])  # noqa: E501
def test_gnosischain_specific_chain_data_failing_logic(
        database: 'DBHandler',
        gnosis_transactions: 'GnosisTransactions',
        gnosis_accounts: list[ChecksumEvmAddress],
) -> None:
    """Tests that in case of error while querying gnosis logs
    we correctly store the last queried timestamp.
    """
    processed_queries = 0
    real_logs = gnosis_transactions.evm_inquirer.etherscan.get_logs

    def mocked_etherscan_logs(*args, **kwargs):
        nonlocal processed_queries
        if processed_queries == 1:
            raise RemoteError('Remote error from patch')

        processed_queries += 1
        return real_logs(*args, **kwargs)

    with patch.object(
        gnosis_transactions.evm_inquirer.etherscan,
        'get_logs',
        wraps=mocked_etherscan_logs,
    ):
        gnosis_transactions.get_chain_specific_multiaddress_data(addresses=gnosis_accounts)

        with database.conn.read_ctx() as cursor:
            for address in gnosis_accounts:
                # check used query ranges are set
                from_ts, to_ts = database.get_used_query_range(cursor, f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}')  # type: ignore # noqa: E501
                assert from_ts == DEPLOYED_TS
                assert to_ts == Timestamp(1586609555)  # timestamp after processing the first subinterval  # noqa: E501


@pytest.mark.freeze_time('2024-11-28 10:44:55 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0x2449fE0bEA58e027f374e90b296e72Dfd7bCcBaE']])  # noqa: E501
def test_gnosischain_specific_chain_data_ts_logic(
        database: 'DBHandler',
        gnosis_transactions: 'GnosisTransactions',
        gnosis_accounts: list[ChecksumEvmAddress],
) -> None:
    """
    This test ensures that the query range logic for gnosis logs works as expected.
    The tests uses 2 addresses. 0xc37b40ABdB939635068d3c5f13E7faF686F03B65 gets a
    range added to the db before the query to ensure that if addresses not queried before
    are queried then we query everything again.

    Then the logic is executed twice. We break the first execution after a few queries to
    ensure that the range is saved and in the second query we start from where it was left.
    """
    with database.user_write() as write_cursor:
        database.update_used_query_range(
            write_cursor=write_cursor,
            name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{gnosis_accounts[0]}',
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )

    counter = 0

    def get_logs_first_step(
            chain_id: ChainID,
            contract_address: ChecksumEvmAddress,
            topics: list[str],
            from_block: int,
            to_block: int | str = 'latest',
    ) -> list[dict[str, Any]]:
        nonlocal counter
        counter += 1
        if counter == 5:
            raise RemoteError('Intended circuit breaker')
        return []

    gno_etherscan = gnosis_transactions.evm_inquirer.etherscan
    with patch.object(gno_etherscan, 'get_logs', new=get_logs_first_step):
        gnosis_transactions.get_chain_specific_multiaddress_data(
            addresses=gnosis_accounts,
        )

    with database.conn.read_ctx() as cursor:
        for address in gnosis_accounts:  # check that query ranges are correct
            result = database.get_used_query_range(
                cursor=cursor,
                name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',
            )
            assert result is not None
            from_ts, to_ts = result
            assert from_ts == DEPLOYED_TS
            assert to_ts == Timestamp(1591219000)

    def get_logs_second_step(
            contract_address: ChecksumEvmAddress,
            topics: list[str],
            from_block: int,
            to_block: int | str = 'latest',
    ) -> list[dict[str, Any]]:
        assert from_block == 10253328  # matching the previous timestamp to ensure that we save the progress  # noqa: E501
        raise RemoteError('Intended circuit breaker')

    with patch.object(gno_etherscan, 'get_logs', new=get_logs_second_step):
        gnosis_transactions.get_chain_specific_multiaddress_data(
            addresses=gnosis_accounts,
        )
