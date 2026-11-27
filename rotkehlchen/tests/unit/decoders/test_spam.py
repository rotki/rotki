
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.spam_assets import check_token_impersonates_dangerous_tokens
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.globaldb.handler import GlobalDBHandler


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x929a6225A5012316aF9d36386b243911ad6df9DF', '0x223EE48E2A9A786FD061e8273D078a4451FAf76B']])  # noqa: E501
def test_receive_poison(ethereum_inquirer: EthereumInquirer):
    """Check the main currency poisoning. In this transaction there are only spam token transfers.
    There is a fake ETH transfer and a fake USDC transfer.
    """
    tx_hash = deserialize_evm_tx_hash('0xaaa20e8ab6dc3f16a0518c4f3c9fadf61264a321d65cd5af68869f5f47828934')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events[0].notes == 'Receive 2.12507748 ETH from 0x7eb7b44A10B7af2b9e79eADD813c04Ba6D422bBB to 0x223EE48E2A9A786FD061e8273D078a4451FAf76B'  # fake ETH  # noqa: E501
    assert events[1].notes == 'Receive 44794.000506 USDC from 0x8845F09D88EEFfeD9B197c8a92cDd36A9dD72c05 to 0x929a6225A5012316aF9d36386b243911ad6df9DF'  # fake USDC  # noqa: E501
    # Both fake ETH and fake USDC should be marked as spam and ignored
    assert events[0].asset.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    assert events[1].asset.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    with ethereum_inquirer.database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM multisettings WHERE name=? AND value in (?, ?)',
            ('ignored_asset', events[0].asset.identifier, events[1].asset.identifier),
        ).fetchone()[0] == 2


def test_impersonating_token_deletes_data_issues_and_notifies(
        globaldb: GlobalDBHandler,
        database: DBHandler,
) -> None:
    """Impersonation detection removes persisted issues for the fake token and notifies."""
    fake_usdc = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='USDC',
        name='Fake USDC',
    )
    globaldb.add_asset(fake_usdc)

    issues_manager = DataIssuesManager(database)
    issues_manager.write_issue(
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
        location=LOCATION_ETHEREUM,
        location_label=make_evm_address(),
        protocol=None,
        asset=fake_usdc.identifier,
        ts_start=TimestampMS(1_000),
        ts_end=TimestampMS(1_000),
        payload={
            'delta': '100',
            'derived_balance': '0',
            'latest_event_identifier': None,
            'observed_balance': '100',
            'queried_at_ts': 1,
        },
    )
    kept_issue_id = issues_manager.write_issue(
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
        location=LOCATION_ETHEREUM,
        location_label=make_evm_address(),
        protocol=None,
        asset=A_DAI.identifier,
        ts_start=TimestampMS(2_000),
        ts_end=TimestampMS(2_000),
        payload={
            'delta': '5',
            'derived_balance': '0',
            'latest_event_identifier': None,
            'observed_balance': '5',
            'queried_at_ts': 2,
        },
    )

    with patch.object(
        database.msg_aggregator,
        'add_message',
        wraps=database.msg_aggregator.add_message,
    ) as add_message:
        check_token_impersonates_dangerous_tokens(
            database=database,
            token=fake_usdc,
            native_token=A_ETH.resolve_to_crypto_asset(),
        )

    assert fake_usdc.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    with database.conn.read_ctx() as cursor:
        assert fake_usdc.identifier in database.get_ignored_asset_ids(cursor)
    assert [issue.id for issue in issues_manager.list_issues()] == [kept_issue_id]

    add_message.assert_called_once_with(
        message_type=WSMessageType.DATA_ISSUES_REMOVED,
        data={'assets': [fake_usdc.identifier]},
    )

    # Another impersonating token with no data issues must not emit DATA_ISSUES_REMOVED.
    fake_eth = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='ETH',
        name='Fake ETH',
    )
    globaldb.add_asset(fake_eth)
    with patch.object(
        database.msg_aggregator,
        'add_message',
        wraps=database.msg_aggregator.add_message,
    ) as add_message:
        check_token_impersonates_dangerous_tokens(
            database=database,
            token=fake_eth,
            native_token=A_ETH.resolve_to_crypto_asset(),
        )

    assert fake_eth.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    add_message.assert_not_called()
