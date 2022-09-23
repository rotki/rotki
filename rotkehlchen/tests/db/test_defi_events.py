from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.aave.structures import (
    AaveBorrowEvent,
    AaveDepositWithdrawalEvent,
    AaveInterestEvent,
    AaveLiquidationEvent,
    AaveRepayEvent,
)
from rotkehlchen.chain.ethereum.modules.yearn.db import (
    add_yearn_vaults_events,
    get_yearn_vaults_events,
)
from rotkehlchen.chain.ethereum.modules.yearn.structures import YearnVault, YearnVaultEvent
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_MANA, A_WBTC, A_YV1_DAI
from rotkehlchen.constants.ethereum import YEARN_DAI_VAULT
from rotkehlchen.constants.misc import ONE
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.aave import A_ADAI_V1
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator


def test_add_and_get_aave_events(data_dir, username, sql_vm_instructions_cb):
    """Test that get aave events works fine and returns only events for what we need"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)

    addr1 = make_ethereum_address()
    addr1_events = [AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(amount=ONE, usd_value=ONE),
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash=deserialize_evm_tx_hash(
            '0x01653e88600a6492ad6e9ae2af415c990e623479057e4e93b163e65cfb2d4436',
        ),
        log_index=1,
    ), AaveDepositWithdrawalEvent(
        event_type='withdrawal',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(amount=ONE, usd_value=ONE),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash=deserialize_evm_tx_hash(
            '0x4147da3e5d3c0565a99192ce0b32182ab30b8e1067921d9b2a8ef3bd60b7e2ce',
        ),
        log_index=2,
    )]
    with data.db.user_write() as cursor:
        data.db.add_aave_events(cursor, address=addr1, events=addr1_events)

        addr2 = make_ethereum_address()
        addr2_events = [AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI,
            atoken=A_ADAI_V1,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=1,
            timestamp=Timestamp(1),
            tx_hash=deserialize_evm_tx_hash(
                '0x8c094d58f33e8dedcd348cb33b58f3bd447602f1fecb99e51b1c2868029eab55',
            ),
            log_index=1,
        ), AaveDepositWithdrawalEvent(
            event_type='withdrawal',
            asset=A_DAI,
            atoken=A_ADAI_V1,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=2,
            timestamp=Timestamp(2),
            tx_hash=deserialize_evm_tx_hash(
                '0x58c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=2,
        )]
        data.db.add_aave_events(cursor, address=addr2, events=addr2_events)

        # addr3 has all types of aave events so we test serialization/deserialization
        addr3 = make_ethereum_address()
        addr3_events = [AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI,
            atoken=A_ADAI_V1,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=1,
            timestamp=Timestamp(1),
            tx_hash=deserialize_evm_tx_hash(
                '0x9e394d58f33e8dedcd348cb33b58f3bd447602f1fecb99e51b1c2868029eab55',
            ),
            log_index=1,
        ), AaveDepositWithdrawalEvent(
            event_type='withdrawal',
            asset=A_DAI,
            atoken=A_ADAI_V1,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=2,
            timestamp=Timestamp(2),
            tx_hash=deserialize_evm_tx_hash(
                '0x4c167445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=2,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_WBTC,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=4,
            timestamp=Timestamp(4),
            tx_hash=deserialize_evm_tx_hash(
                '0x49c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=4,
        ), AaveBorrowEvent(
            event_type='borrow',
            asset=A_ETH,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=5,
            timestamp=Timestamp(5),
            tx_hash=deserialize_evm_tx_hash(
                '0x19c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=5,
            borrow_rate_mode='stable',
            borrow_rate=FVal('0.05233232323423432'),
            accrued_borrow_interest=FVal('5.112234'),
        ), AaveRepayEvent(
            event_type='repay',
            asset=A_MANA,
            value=Balance(amount=ONE, usd_value=ONE),
            block_number=6,
            timestamp=Timestamp(6),
            tx_hash=deserialize_evm_tx_hash(
                '0x29c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=6,
            fee=Balance(amount=FVal('0.1'), usd_value=FVal('0.1')),
        ), AaveLiquidationEvent(
            event_type='liquidation',
            collateral_asset=A_ETH,
            collateral_balance=Balance(amount=ONE, usd_value=ONE),
            principal_asset=A_ETH,
            principal_balance=Balance(amount=ONE, usd_value=ONE),
            block_number=7,
            log_index=7,
            timestamp=Timestamp(7),
            tx_hash=deserialize_evm_tx_hash(
                '0x39c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
        )]
        data.db.add_aave_events(cursor, address=addr3, events=addr3_events)

        events = data.db.get_aave_events(
            cursor=cursor,
            address=addr1,
            atoken=A_ADAI_V1.resolve_to_evm_token(),
        )
        assert events == addr1_events
        events = data.db.get_aave_events(
            cursor=cursor,
            address=addr2,
            atoken=A_ADAI_V1.resolve_to_evm_token(),
        )
        assert events == addr2_events
        events = data.db.get_aave_events(cursor=cursor, address=addr3)
        assert events == addr3_events

    # check that all aave events are properly hashable (aka can go in a set)
    test_set = set()
    for event in addr3_events:
        test_set.add(event)
    assert len(test_set) == len(addr3_events)


def test_add_and_get_yearn_vault_events(data_dir, username, sql_vm_instructions_cb):
    """Test that get yearn vault events works fine and returns only events for what we need"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)

    addr1 = make_ethereum_address()
    addr1_events = [YearnVaultEvent(
        event_type='deposit',
        from_asset=A_DAI,
        from_value=Balance(amount=ONE, usd_value=ONE),
        to_asset=A_YV1_DAI,
        to_value=Balance(amount=ONE, usd_value=ONE),
        realized_pnl=None,
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash=deserialize_evm_tx_hash(
            '0x01653e88600a6492ad6e9ae2af415c990e623479057e4e93b163e65cfb2d4436',
        ),
        log_index=1,
        version=1,
    ), YearnVaultEvent(
        event_type='withdraw',
        from_asset=A_YV1_DAI,
        from_value=Balance(amount=ONE, usd_value=ONE),
        to_asset=A_DAI,
        to_value=Balance(amount=ONE, usd_value=ONE),
        realized_pnl=Balance(amount=FVal('0.01'), usd_value=FVal('0.01')),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash=deserialize_evm_tx_hash(
            '0x4147da3e5d3c0565a99192ce0b32182ab30b8e1067921d9b2a8ef3bd60b7e2ce',
        ),
        log_index=2,
        version=1,
    )]
    with data.db.user_write() as cursor:
        add_yearn_vaults_events(write_cursor=cursor, address=addr1, events=addr1_events)
        addr2 = make_ethereum_address()
        addr2_events = [YearnVaultEvent(
            event_type='deposit',
            from_asset=A_DAI,
            from_value=Balance(amount=ONE, usd_value=ONE),
            to_asset=A_YV1_DAI,
            to_value=Balance(amount=ONE, usd_value=ONE),
            realized_pnl=None,
            block_number=1,
            timestamp=Timestamp(1),
            tx_hash=deserialize_evm_tx_hash(
                '0x8c094d58f33e8dedcd348cb33b58f3bd447602f1fecb99e51b1c2868029eab55',
            ),
            log_index=1,
            version=1,
        ), YearnVaultEvent(
            event_type='withdraw',
            from_asset=A_YV1_DAI,
            from_value=Balance(amount=ONE, usd_value=ONE),
            to_asset=A_DAI,
            to_value=Balance(amount=ONE, usd_value=ONE),
            realized_pnl=Balance(amount=FVal('0.01'), usd_value=FVal('0.01')),
            block_number=2,
            timestamp=Timestamp(2),
            tx_hash=deserialize_evm_tx_hash(
                '0x58c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            ),
            log_index=2,
            version=1,
        )]
        add_yearn_vaults_events(write_cursor=cursor, address=addr2, events=addr2_events)

        ydai_vault = YearnVault(
            name='YDAI Vault',
            contract=YEARN_DAI_VAULT,
            underlying_token=A_DAI,
            token=A_YV1_DAI,
        )
        events = get_yearn_vaults_events(cursor=cursor, address=addr1, vault=ydai_vault, msg_aggregator=data.msg_aggregator)  # noqa: E501
        assert events == addr1_events
        events = get_yearn_vaults_events(cursor=cursor, address=addr2, vault=ydai_vault, msg_aggregator=data.msg_aggregator)  # noqa: E501
        assert events == addr2_events
