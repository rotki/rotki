from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.yearn.db import (
    add_yearn_vaults_events,
    get_yearn_vaults_events,
)
from rotkehlchen.chain.ethereum.modules.yearn.structures import YearnVault, YearnVaultEvent
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_YV1_DAI
from rotkehlchen.constants.misc import ONE
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator


def test_add_and_get_yearn_vault_events(
        data_dir,
        username,
        sql_vm_instructions_cb,
        ethereum_contracts,
):
    """Test that get yearn vault events works fine and returns only events for what we need"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    addr1 = make_evm_address()
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
        addr2 = make_evm_address()
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
            contract=ethereum_contracts.contract(string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952')),  # noqa: E501
            underlying_token=A_DAI,
            token=A_YV1_DAI,
        )
        events = get_yearn_vaults_events(cursor=cursor, address=addr1, vault=ydai_vault, msg_aggregator=data.msg_aggregator)  # noqa: E501
        assert events == addr1_events
        events = get_yearn_vaults_events(cursor=cursor, address=addr2, vault=ydai_vault, msg_aggregator=data.msg_aggregator)  # noqa: E501
        assert events == addr2_events
