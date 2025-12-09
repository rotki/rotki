from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.zksync_lite.constants import ZKL_IDENTIFIER
from rotkehlchen.chain.zksync_lite.structures import (
    ZKSyncLiteSwapData,
    ZKSyncLiteTransaction,
    ZKSyncLiteTXType,
)
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import (
    A_DAI,
    A_ETH,
    A_LINK,
    A_LRC,
    A_MANA,
    A_SNX,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_PAN, CURRENT_PRICE_MOCK
from rotkehlchen.types import Location, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-03-24 00:00:00 GMT')
def test_fetch_transactions(zksync_lite_manager):
    zksync_lite_manager.fetch_transactions(string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'))
    transactions = []
    with zksync_lite_manager.database.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT tx_hash, type, timestamp, block_number, from_address, to_address, '
            'asset, amount, fee FROM zksynclite_transactions ORDER BY timestamp ASC',
        )
        transactions = [ZKSyncLiteTransaction.deserialize_from_db(x) for x in cursor]

    assert len(transactions) == 16
    assert transactions[0] == ZKSyncLiteTransaction(
        tx_hash=b'\xb8\rF;\xbc\xf8J\x87m\xb6\xcf\x80_\x1d\x88k`\xe7\xab\r9!4\xb3t\xe2\xea\xb3\xa1\x93/\xe1',
        tx_type=ZKSyncLiteTXType.DEPOSIT,
        timestamp=Timestamp(1601574932),
        block_number=3836,
        from_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        to_address='0x957A50DA7B25Ce98B7556AfEF1d4e5F5C60fC818',
        asset=A_DAI,
        amount=FVal(23.016),
        fee=None,
    )
    assert transactions[1] == ZKSyncLiteTransaction(
        tx_hash=b'1*\xb01\xb3PL\xde\xc45G\x95\x17l\xcc\xadL\xaf8\xa1P\xd5\xd3\x10\xc9^\x93I\x9bY\xee\xd1',
        tx_type=ZKSyncLiteTXType.TRANSFER,
        timestamp=Timestamp(1638186357),
        block_number=36526,
        from_address='0x9531C059098e3d194fF87FebB587aB07B30B1306',
        to_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        asset=A_ETH,
        amount=FVal(0.4023119998),
        fee=FVal(0.000233),
    )
    assert transactions[5] == ZKSyncLiteTransaction(
        tx_hash=b'\xe8wB<\xc4\xf2F\x13H\x96\xbfZf\xcc\x922\xa8\xbeM\xc7\x1au\xd7\xeap>\x10]\xfd\x8e{\x82',
        tx_type=ZKSyncLiteTXType.TRANSFER,
        timestamp=Timestamp(1648716422),
        block_number=61452,
        from_address='0x9531C059098e3d194fF87FebB587aB07B30B1306',
        to_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        asset=A_ETH,
        amount=FVal(0.50543049),
        fee=FVal(0.0000324),
    )
    # For 1656022105 order can be random.
    tx_hash = b'\xe8"\x81\xa8\\"\xc7r\xeb5\x17p5\xd9<\xdb\x7fU\x9b\xafp\xe0,\t\x00\xf5\x08\xe7#=\x1d\x0f'  # noqa: E501
    for idx in (8, 9, 10, 11, 12):
        if transactions[idx].tx_hash == tx_hash:
            break

    assert transactions[idx] == ZKSyncLiteTransaction(
        tx_hash=tx_hash,
        tx_type=ZKSyncLiteTXType.TRANSFER,
        timestamp=Timestamp(1656022105),
        block_number=91045,
        from_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        to_address='0x4D9339dd97db55e3B9bCBE65dE39fF9c04d1C2cd',
        asset=A_ETH,
        amount=FVal(0.005),
        fee=None,
    )

    # For 1656022105 order can be random.
    tx_hash = b'\x83\x00\x1f\x1cU\x80\xd9\r4Wy\xcd\x10v/\xc7\x1cL\x90  %Q\xbcH\x031\xd7\rT|\xc7'
    for idx in (8, 9, 10, 11, 12):
        if transactions[idx].tx_hash == tx_hash:
            break
    assert transactions[idx] == ZKSyncLiteTransaction(
        tx_hash=tx_hash,
        tx_type=ZKSyncLiteTXType.CHANGEPUBKEY,
        timestamp=Timestamp(1656022105),
        block_number=91045,
        from_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        to_address=None,
        asset=A_ETH,
        amount=ZERO,
        fee=FVal(0.001513),
    )
    assert transactions[14] == ZKSyncLiteTransaction(
        tx_hash=b'3\x1f\xccI\xdc<\nw.\x0b^E\x185\x0f=\x9a\\Uv\xb4\xe8\xdb\xc7\xc5k,Y\xca\xa29\xbb',
        tx_type=ZKSyncLiteTXType.TRANSFER,
        timestamp=Timestamp(1659010582),
        block_number=96159,
        from_address='0x9531C059098e3d194fF87FebB587aB07B30B1306',
        to_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        asset=A_ETH,
        amount=FVal('0.9630671085'),
        fee=None,
    )
    assert transactions[15] == ZKSyncLiteTransaction(
        tx_hash=b'\xbdr;Z_\x87\xe4\x85\xa4x\xbc}\x1f6]\xb7\x94@\xb6\xe90[\xff;\x16\xa0\xe0\xab\x83\xe5\x19p',
        tx_type=ZKSyncLiteTXType.WITHDRAW,
        timestamp=Timestamp(1708431030),
        block_number=425869,
        from_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        to_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        asset=A_ETH,
        amount=FVal(6.626770825),
        fee=FVal(0.00367),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_balances(zksync_lite_manager, inquirer):  # pylint: disable=unused-argument
    lefty, rotki, empty = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '0x9531C059098e3d194fF87FebB587aB07B30B1306', '0xB638e104563515a917025964ee874a484A489147'  # noqa: E501
    balances = zksync_lite_manager.query_balances(addresses=[lefty, rotki, empty])
    lefty_eth_amount = FVal('0.0004100008')
    eth, mana, uni, wbtc, link, dai, frax, usdc, storj, lrc, snx, pan, usdt = FVal('0.00002036000092'), FVal('16.38'), FVal('2.1409'), FVal('0.00012076'), FVal('0.47523'), FVal('53.83503876'), FVal('2.4306'), FVal('98.233404'), FVal('2.2064'), FVal('0.95'), FVal('0.95'), FVal('9202.65'), FVal('4.1')  # noqa: E501
    assert balances == {
        lefty: BalanceSheet(assets={
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=lefty_eth_amount, value=lefty_eth_amount * CURRENT_PRICE_MOCK)},  # noqa: E501
        }),
        rotki: BalanceSheet(assets={
            A_ETH: {DEFAULT_BALANCE_LABEL: Balance(amount=eth, value=eth * CURRENT_PRICE_MOCK)},
            A_MANA: {DEFAULT_BALANCE_LABEL: Balance(amount=mana, value=mana * CURRENT_PRICE_MOCK)},
            A_UNI: {DEFAULT_BALANCE_LABEL: Balance(amount=uni, value=uni * CURRENT_PRICE_MOCK)},
            A_WBTC: {DEFAULT_BALANCE_LABEL: Balance(amount=wbtc, value=wbtc * CURRENT_PRICE_MOCK)},
            A_LINK: {DEFAULT_BALANCE_LABEL: Balance(amount=link, value=link * CURRENT_PRICE_MOCK)},
            A_DAI: {DEFAULT_BALANCE_LABEL: Balance(amount=dai, value=dai * CURRENT_PRICE_MOCK)},
            EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'): {DEFAULT_BALANCE_LABEL: Balance(amount=frax, value=frax * CURRENT_PRICE_MOCK)},  # noqa: E501  # FRAX
            A_USDC: {DEFAULT_BALANCE_LABEL: Balance(amount=usdc, value=usdc * CURRENT_PRICE_MOCK)},
            EvmToken('eip155:1/erc20:0xB64ef51C888972c908CFacf59B47C1AfBC0Ab8aC'): {DEFAULT_BALANCE_LABEL: Balance(amount=storj, value=storj * CURRENT_PRICE_MOCK)},  # noqa: E501  # STORJ
            A_LRC: {DEFAULT_BALANCE_LABEL: Balance(amount=lrc, value=lrc * CURRENT_PRICE_MOCK)},
            A_SNX: {DEFAULT_BALANCE_LABEL: Balance(amount=snx, value=snx * CURRENT_PRICE_MOCK)},
            A_PAN: {DEFAULT_BALANCE_LABEL: Balance(amount=pan, value=pan * CURRENT_PRICE_MOCK)},
            A_USDT: {DEFAULT_BALANCE_LABEL: Balance(amount=usdt, value=usdt * CURRENT_PRICE_MOCK)},
        }),
        empty: BalanceSheet(),
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.freeze_time('2024-04-02 00:00:00 GMT')
def test_decode_fullexit(zksync_lite_manager, inquirer):  # pylint: disable=unused-argument
    tx_hash = deserialize_evm_tx_hash('0xd61d5f242022a43b5a11c84b350cdf8b2923221bf4a89ef091d51a1494d36007')  # noqa: E501
    address = string_to_evm_address('0xd6dfD811E06267b25472753c4e57C0B28652bFB8')
    timestamp = Timestamp(1592248320)
    zksync_lite_manager.fetch_transactions(address)
    transactions = zksync_lite_manager.get_db_transactions(
        queryfilter=' WHERE tx_hash=?', bindings=(tx_hash,),
    )
    assert transactions == [ZKSyncLiteTransaction(
        tx_hash=tx_hash,
        tx_type=ZKSyncLiteTXType.FULLEXIT,
        timestamp=timestamp,
        block_number=2,
        from_address=address,
        to_address=address,
        asset=A_ETH,
        amount=ZERO,
        fee=None,
    )]
    zksync_lite_manager.decode_transaction(transactions[0], [address])
    dbevents = DBHistoryEvents(zksync_lite_manager.database)
    with zksync_lite_manager.database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            aggregate_by_group_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(tx_hash)),
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=address,
        notes='Full exit to Ethereum',
        address=address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.freeze_time('2024-04-05 11:00:00 GMT')
def test_decode_forcedexit(zksync_lite_manager, inquirer):  # pylint: disable=unused-argument
    tx_hash = deserialize_evm_tx_hash('0xfa3d59c21b709f4ffd9b0e6c7e2dfe4579d7dd5e85325575d381ad88e50a64f1')  # noqa: E501
    address = string_to_evm_address('0x4676b83307A2A4A1556cdfC4d0c21097B584f3cF')
    timestamp = Timestamp(1712296398)
    zksync_lite_manager.fetch_transactions(address)
    transactions = zksync_lite_manager.get_db_transactions(
        queryfilter=' WHERE tx_hash=?', bindings=(tx_hash,),
    )
    assert transactions == [ZKSyncLiteTransaction(
        tx_hash=tx_hash,
        tx_type=ZKSyncLiteTXType.FORCEDEXIT,
        timestamp=timestamp,
        block_number=436967,
        from_address=address,
        to_address=address,
        asset=A_USDT,
        amount=ZERO,
        fee=None,
    )]
    zksync_lite_manager.decode_transaction(transactions[0], [address])
    dbevents = DBHistoryEvents(zksync_lite_manager.database)
    with zksync_lite_manager.database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            aggregate_by_group_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(tx_hash)),
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_USDT,
        amount=ZERO,
        location_label=address,
        notes='Forced exit to Ethereum',
        address=address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.freeze_time('2024-04-11 10:00:00 GMT')
def test_decode_swap(zksync_lite_manager, inquirer):  # pylint: disable=unused-argument
    tx_hash = deserialize_evm_tx_hash('0x62819dad5d0d99dc5de633ecb95629c1073bcb80a8af15464ca4b0bc95b394b9')  # noqa: E501
    address = string_to_evm_address('0x721AF5c931BAA2415428064e5F71A251F30152B1')
    timestamp = Timestamp(1710752106)
    zksync_lite_manager.fetch_transactions(address)
    transactions = zksync_lite_manager.get_db_transactions(
        queryfilter=' WHERE tx_hash=?', bindings=(tx_hash,),
    )
    assert transactions == [ZKSyncLiteTransaction(
        tx_hash=tx_hash,
        tx_type=ZKSyncLiteTXType.SWAP,
        timestamp=timestamp,
        block_number=433594,
        from_address=address,
        to_address=address,
        asset=A_DAI,
        amount=FVal('0.1659'),
        fee=FVal('0.1659'),
        swap_data=ZKSyncLiteSwapData(
            from_asset=A_ETH,
            from_amount=FVal('0.01042855223'),
            to_asset=A_USDT,
            to_amount=FVal('37.082973'),
        ),
    )]
    zksync_lite_manager.decode_transaction(transactions[0], [address])
    dbevents = DBHistoryEvents(zksync_lite_manager.database)
    with zksync_lite_manager.database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            aggregate_by_group_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(tx_hash)),
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('0.01042855223'),
        location_label=address,
        notes='Swap 0.01042855223 ETH via ZKSync Lite',
        address=address,
    ), EvmEvent(
        identifier=2,
        group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(tx_hash)),
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('37.082973'),
        location_label=address,
        notes='Receive 37.082973 USDT as the result of a swap via ZKSync Lite',
        address=address,
    ), EvmEvent(
        identifier=3,
        group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(tx_hash)),
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DAI,
        amount=FVal('0.1659'),
        location_label=address,
        notes='Swap fee of 0.1659 DAI',
        address=address,
    )]


def test_get_db_transactions(zksync_lite_manager: 'ZksyncLiteManager'):
    """Test that all zksync lite transactions are loaded from the database
    when a swap transaction is present.

    Regression test for https://github.com/rotki/rotki/issues/8777
    """
    address = string_to_evm_address('0xc10fcf82f3b870cbb2b0136a0c891f6b410497c8')
    with zksync_lite_manager.database.conn.write_ctx() as write_cursor:
        zksync_lite_manager._add_zksynctxs_db(
            write_cursor=write_cursor,
            transactions=[
                ZKSyncLiteTransaction(
                    tx_hash=deserialize_evm_tx_hash('0x9922304b069ed8405edcc3c7c4a8c8cc9c8f1edb6a67809f57543e8fe0fa9875'),
                    tx_type=ZKSyncLiteTXType.TRANSFER,
                    timestamp=Timestamp(1663539042),
                    block_number=105088,
                    from_address=address,
                    to_address=string_to_evm_address('0x10E87b05fe0EDE0BbB0a52aFa96c08618A3E02F0'),
                    asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                    amount=ONE,
                    fee=None,
                ),
                ZKSyncLiteTransaction(
                    tx_hash=deserialize_evm_tx_hash('0xca2192731809a75b76680d708eb992fe3f176bef8134414ff8bd5cf0a106bfcd'),
                    tx_type=ZKSyncLiteTXType.SWAP,
                    timestamp=Timestamp(1647648071),
                    block_number=58134,
                    from_address=address,
                    to_address=address,
                    asset=A_ETH,
                    amount=FVal(0.0000982),
                    fee=None,
                    swap_data=ZKSyncLiteSwapData(
                        from_asset=A_ETH,
                        from_amount=FVal(10.177475971),
                        to_asset=Asset('eip155:1/erc20:0xdCD90C7f6324cfa40d7169ef80b12031770B4325'),
                        to_amount=FVal(9.091938315),
                    ),
                ),
                ZKSyncLiteTransaction(
                    tx_hash=deserialize_evm_tx_hash('0x34f4c91b42657bddd4698a7c61152f2a35613c4096f48f554945c4301e08464e'),
                    tx_type=ZKSyncLiteTXType.TRANSFER,
                    timestamp=Timestamp(1673340336),
                    block_number=147251,
                    from_address=address,
                    to_address=address,
                    asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                    amount=ZERO,
                    fee=None,
                ),
            ],
        )

    transactions = zksync_lite_manager.get_db_transactions(
        queryfilter=' WHERE is_decoded=?',
        bindings=(0,),
    )
    assert len(transactions) == 3
