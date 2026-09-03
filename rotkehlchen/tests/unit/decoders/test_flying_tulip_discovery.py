from typing import Final

import pytest

from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.chain.evm.decoding.flying_tulip.lend.constants import (
    FLYING_TULIP_LEND_DEPLOYMENTS,
    LAST_DEPOSIT_FOR_QUERY,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.lend.discovery import (
    CHECKPOINT_MARGIN_BLOCKS,
    _query_deposits_for_address,
    query_deposit_for_transactions,
)
from rotkehlchen.chain.evm.types import EvmIndexer, SerializableChainIndexerOrder
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tests.utils.ethereum import (
    PRUNED_AND_NOT_ARCHIVED_NODE,
    get_decoded_events_of_transaction,
)
from rotkehlchen.types import ChainID, deserialize_evm_tx_hash

DEPLOYMENT: Final = FLYING_TULIP_LEND_DEPLOYMENTS[ChainID.ETHEREUM]
BENEFICIARY: Final = '0x66613091b75e54954f77746e160c98391f99701c'
INACTIVE_ACCOUNT: Final = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'

pytestmark = [
    pytest.mark.vcr(
        filter_query_parameters=['apikey'], match_on=['match_rpc_calls'],
        before_record_response=None,
    ),
    pytest.mark.parametrize(
        'ethereum_manager_connect_at_start', [(PRUNED_AND_NOT_ARCHIVED_NODE,)],
    ),
    pytest.mark.parametrize('db_settings', [{'evm_indexers_order': SerializableChainIndexerOrder(
        order={ChainID.ETHEREUM: [EvmIndexer.BLOCKSCOUT]},
    )}]),
]


def _checkpoint(database, address, name=DBCacheDynamic.LAST_BLOCK_ID):
    with database.conn.read_ctx() as cursor:
        return database.get_dynamic_cache(
            cursor=cursor,
            name=name,
            location='ethereum',
            location_name=LAST_DEPOSIT_FOR_QUERY,
            account_id=address,
        )


def _set_checkpoint(database, address, block):
    with database.user_write() as cursor:
        database.set_dynamic_cache(
            write_cursor=cursor,
            name=DBCacheDynamic.LAST_BLOCK_ID,
            value=block,
            location='ethereum',
            location_name=LAST_DEPOSIT_FOR_QUERY,
            account_id=address,
        )


@pytest.mark.parametrize('ethereum_accounts', [[BENEFICIARY, INACTIVE_ACCOUNT]])
def test_deposit_for_discovery(eth_transactions, ethereum_accounts, database):
    """Discover and import a real third-party deposit without preloading its transaction."""
    _set_checkpoint(database, BENEFICIARY, 25366043)
    query_deposit_for_transactions(eth_transactions, ethereum_accounts)
    tx_hash = deserialize_evm_tx_hash('0x4e2d5820c340408029ddca71d46401223f6a1a935c9e193bc53303c6b92bf060')  # noqa: E501
    with database.conn.read_ctx() as cursor:
        assert eth_transactions.dbevmtx.get_receipt(cursor, tx_hash, ChainID.ETHEREUM) is not None
        assert cursor.execute(
            'SELECT M.address FROM evmtx_address_mappings M '
            'JOIN evm_transactions T ON T.identifier=M.tx_id WHERE T.tx_hash=? AND T.chain_id=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchall() == [(BENEFICIARY,)]
    assert _checkpoint(database, BENEFICIARY) > 25366044
    assert _checkpoint(database, INACTIVE_ACCOUNT) is None
    assert _checkpoint(database, 'positions', DBCacheDynamic.LAST_QUERY_TS) is not None
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=eth_transactions.evm_inquirer,
        transactions=eth_transactions,
        tx_hash=tx_hash,
    )
    assert len(events) == 1
    assert events[0].counterparty == CPT_FLYING_TULIP
    assert events[0].location_label == BENEFICIARY
    assert str(events[0].amount) == '212.851154726968618944'


@pytest.mark.parametrize('ethereum_accounts', [[
    INACTIVE_ACCOUNT, '0x3c9094Fc254371998fE115a6AA38be9955b2f694',
]])
def test_deposit_for_discovery_ignores_empty_positions(
        eth_transactions, ethereum_accounts, database,
):
    """Real empty collateral lists must not advance the accounts' history checkpoints."""
    query_deposit_for_transactions(eth_transactions, ethereum_accounts)
    assert all(_checkpoint(database, address) is None for address in ethereum_accounts)
    assert _checkpoint(database, 'positions', DBCacheDynamic.LAST_QUERY_TS) is not None
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] == 0


@pytest.mark.parametrize('ethereum_accounts', [[BENEFICIARY]])
@pytest.mark.parametrize('start_after_deposit', [False, True])
def test_deposit_for_discovery_checkpoint_boundaries(
        eth_transactions, database, start_after_deposit,
):
    """The exact block of a real deposit is included once and excluded after its checkpoint."""
    assert _query_deposits_for_address(
        transactions=eth_transactions,
        beneficiary=BENEFICIARY,
        contract_address=DEPLOYMENT.positions_manager,
        from_block=25366044 + start_after_deposit,
        target_block=25366044 + CHECKPOINT_MARGIN_BLOCKS,
    ) is True
    with database.conn.read_ctx() as cursor:
        receipt = eth_transactions.dbevmtx.get_receipt(
            cursor,
            deserialize_evm_tx_hash('0x4e2d5820c340408029ddca71d46401223f6a1a935c9e193bc53303c6b92bf060'),
            ChainID.ETHEREUM,
        )
    assert (receipt is None) is start_after_deposit


@pytest.mark.parametrize('ethereum_accounts', [[
    BENEFICIARY, '0xD28b633345340334782521Eb769DfBdb23178308',
]])
def test_deposit_for_discovery_backfills_new_account(
        eth_transactions, ethereum_accounts, database,
):
    """Adding an account must not clear the decoded state of previously imported deposits."""
    _set_checkpoint(database, BENEFICIARY, 25366043)
    query_deposit_for_transactions(eth_transactions, [BENEFICIARY])
    tx_hash = deserialize_evm_tx_hash('0x4e2d5820c340408029ddca71d46401223f6a1a935c9e193bc53303c6b92bf060')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=eth_transactions.evm_inquirer,
        transactions=eth_transactions,
        tx_hash=tx_hash,
    )
    previous_checkpoint = _checkpoint(database, BENEFICIARY)
    assert previous_checkpoint > 25366044
    query_deposit_for_transactions(eth_transactions, ethereum_accounts)
    assert _checkpoint(database, BENEFICIARY) >= previous_checkpoint
    assert _checkpoint(database, ethereum_accounts[1]) is not None
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT 1 FROM evm_tx_mappings M JOIN evm_transactions T ON T.identifier=M.tx_id '
            'WHERE T.tx_hash=? AND T.chain_id=? AND M.value=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db(), TX_DECODED),
        ).fetchone() == (1,)


@pytest.mark.parametrize('ethereum_accounts', [['0x3c42749709BF354B3aE0Db29Fd2dd88089b21B4E']])
def test_deposit_for_discovery_skips_self_funded_deposit(
        eth_transactions, ethereum_accounts, database,
):
    """A real self-funded deposit is left to ordinary per-address transaction discovery."""
    assert _query_deposits_for_address(
        transactions=eth_transactions,
        beneficiary=ethereum_accounts[0],
        contract_address=DEPLOYMENT.positions_manager,
        from_block=25731237,
        target_block=25731237 + CHECKPOINT_MARGIN_BLOCKS,
    ) is True
    assert _checkpoint(database, ethereum_accounts[0]) == 25731237
    with database.conn.read_ctx() as cursor:
        assert eth_transactions.dbevmtx.get_receipt(
            cursor,
            deserialize_evm_tx_hash('0x295b8dae0b18ae6738d7f3bd47a4174e436a8887780f84edc5145beb76c2c15e'),
            ChainID.ETHEREUM,
        ) is None


@pytest.mark.parametrize('ethereum_accounts', [['0x268c0342c0151830c6963FE095cec630b3Ac3854']])
def test_deposit_for_discovery_backfills_closed_positions(
        eth_transactions, ethereum_accounts, database,
):
    """A real withdrawal must trigger deposit backfill even when live collateral is empty."""
    query_deposit_for_transactions(eth_transactions, ethereum_accounts)
    assert _checkpoint(database, ethereum_accounts[0]) is None
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] == 0

    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=eth_transactions.evm_inquirer,
        transactions=eth_transactions,
        tx_hash=deserialize_evm_tx_hash('0xc3d7b7d8ab109cbfdc9649d82093f1df0c35edef1df79c2378de43c2e2d8d153'),
    )
    assert any(
        event.counterparty == CPT_FLYING_TULIP and
        event.event_subtype == HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
        for event in events
    )
    _set_checkpoint(database, ethereum_accounts[0], 25402015)
    query_deposit_for_transactions(eth_transactions, ethereum_accounts)
    assert _checkpoint(database, ethereum_accounts[0]) > 25402016
    with database.conn.read_ctx() as cursor:
        assert eth_transactions.dbevmtx.get_receipt(
            cursor,
            deserialize_evm_tx_hash('0x6d6eb8ffe4db09d1dce0b19dc4efccca0d39d6207e6bdac4fec3646df0dad8db'),
            ChainID.ETHEREUM,
        ) is not None
