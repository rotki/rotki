from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.structures import AaveEvent, YearnVaultEvent
from rotkehlchen.chain.ethereum.yearn.vaults import YEARN_VAULTS
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator


def test_add_and_get_aave_events(data_dir, username):
    """Test that get aave events works fine and returns only events for what we need"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    addr1 = make_ethereum_address()
    addr1_events = [AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(amount=FVal(1), usd_value=FVal(1)),
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash='0x01653e88600a6492ad6e9ae2af415c990e623479057e4e93b163e65cfb2d4436',
        log_index=1,
    ), AaveEvent(
        event_type='withdrawal',
        asset=A_DAI,
        value=Balance(amount=FVal(1), usd_value=FVal(1)),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash='0x4147da3e5d3c0565a99192ce0b32182ab30b8e1067921d9b2a8ef3bd60b7e2ce',
        log_index=2,
    )]
    addr2 = make_ethereum_address()
    data.db.add_aave_events(address=addr1, events=addr1_events)
    addr2_events = [AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(amount=FVal(1), usd_value=FVal(1)),
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash='0x8c094d58f33e8dedcd348cb33b58f3bd447602f1fecb99e51b1c2868029eab55',
        log_index=1,
    ), AaveEvent(
        event_type='withdrawal',
        asset=A_DAI,
        value=Balance(amount=FVal(1), usd_value=FVal(1)),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash='0x58c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
        log_index=2,
    )]
    data.db.add_aave_events(address=addr2, events=addr2_events)

    events = data.db.get_aave_events(address=addr1, atoken=EthereumToken('aDAI'))
    assert events == addr1_events
    events = data.db.get_aave_events(address=addr2, atoken=EthereumToken('aDAI'))
    assert events == addr2_events


def test_add_and_get_yearn_vault_events(data_dir, username):
    """Test that get yearn vault events works fine and returns only events for what we need"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    addr1 = make_ethereum_address()
    addr1_events = [YearnVaultEvent(
        event_type='deposit',
        from_asset=A_DAI,
        from_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        to_asset=Asset('yDAI'),
        to_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        realized_pnl=None,
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash='0x01653e88600a6492ad6e9ae2af415c990e623479057e4e93b163e65cfb2d4436',
        log_index=1,
    ), YearnVaultEvent(
        event_type='withdraw',
        from_asset=Asset('yDAI'),
        from_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        to_asset=A_DAI,
        to_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        realized_pnl=Balance(amount=FVal('0.01'), usd_value=FVal('0.01')),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash='0x4147da3e5d3c0565a99192ce0b32182ab30b8e1067921d9b2a8ef3bd60b7e2ce',
        log_index=2,
    )]
    data.db.add_yearn_vaults_events(address=addr1, events=addr1_events)
    addr2 = make_ethereum_address()
    addr2_events = [YearnVaultEvent(
        event_type='deposit',
        from_asset=A_DAI,
        from_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        to_asset=Asset('yDAI'),
        to_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        realized_pnl=None,
        block_number=1,
        timestamp=Timestamp(1),
        tx_hash='0x8c094d58f33e8dedcd348cb33b58f3bd447602f1fecb99e51b1c2868029eab55',
        log_index=1,
    ), YearnVaultEvent(
        event_type='withdraw',
        from_asset=Asset('yDAI'),
        from_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        to_asset=A_DAI,
        to_value=Balance(amount=FVal(1), usd_value=FVal(1)),
        realized_pnl=Balance(amount=FVal('0.01'), usd_value=FVal('0.01')),
        block_number=2,
        timestamp=Timestamp(2),
        tx_hash='0x58c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
        log_index=2,
    )]
    data.db.add_yearn_vaults_events(address=addr2, events=addr2_events)

    events = data.db.get_yearn_vaults_events(address=addr1, vault=YEARN_VAULTS['yDAI'])
    assert events == addr1_events
    events = data.db.get_yearn_vaults_events(address=addr2, vault=YEARN_VAULTS['yDAI'])
    assert events == addr2_events
