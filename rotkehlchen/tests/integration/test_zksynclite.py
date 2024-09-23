import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.zksync_lite.constants import ZKL_IDENTIFIER
from rotkehlchen.chain.zksync_lite.structures import (
    ZKSyncLiteSwapData,
    ZKSyncLiteTransaction,
    ZKSyncLiteTXType,
)
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
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_PAN, CURRENT_PRICE_MOCK
from rotkehlchen.types import Fee, Location, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms


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
        fee=Fee(FVal(0.000233)),
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
        fee=Fee(FVal(0.0000324)),
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
        fee=Fee(FVal(0.001513)),
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
    lefty, rotki = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '0x9531C059098e3d194fF87FebB587aB07B30B1306'  # noqa: E501
    balances = zksync_lite_manager.get_balances(addresses=[lefty, rotki])
    lefty_eth_amount = FVal('6.6308508258')
    eth, mana, uni, wbtc, link, dai, frax, usdc, storj, lrc, snx, pan, usdt = FVal('0.20670353608092'), FVal('16.38'), FVal('2.1409'), FVal('0.00012076'), FVal('0.47523'), FVal('46.16024376'), FVal('2.4306'), FVal('98.233404'), FVal('4.1524'), FVal('0.95'), FVal('0.95'), FVal('9202.65'), FVal('4.1')  # noqa: E501
    assert balances == {
        lefty: {
            A_ETH: Balance(lefty_eth_amount, lefty_eth_amount * CURRENT_PRICE_MOCK),
        },
        rotki: {
            A_ETH: Balance(eth, eth * CURRENT_PRICE_MOCK),
            A_MANA: Balance(mana, mana * CURRENT_PRICE_MOCK),
            A_UNI: Balance(uni, uni * CURRENT_PRICE_MOCK),
            A_WBTC: Balance(wbtc, wbtc * CURRENT_PRICE_MOCK),
            A_LINK: Balance(link, link * CURRENT_PRICE_MOCK),
            A_DAI: Balance(dai, dai * CURRENT_PRICE_MOCK),
            EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'): Balance(frax, frax * CURRENT_PRICE_MOCK),  # noqa: E501  # FRAX
            A_USDC: Balance(usdc, usdc * CURRENT_PRICE_MOCK),
            EvmToken('eip155:1/erc20:0xB64ef51C888972c908CFacf59B47C1AfBC0Ab8aC'): Balance(storj, storj * CURRENT_PRICE_MOCK),  # noqa: E501  # STORJ
            A_LRC: Balance(lrc, lrc * CURRENT_PRICE_MOCK),
            A_SNX: Balance(snx, snx * CURRENT_PRICE_MOCK),
            A_PAN: Balance(pan, pan * CURRENT_PRICE_MOCK),
            A_USDT: Balance(usdt, usdt * CURRENT_PRICE_MOCK),
        },
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
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        event_identifier=ZKL_IDENTIFIER.format(tx_hash=tx_hash.hex()),  # pylint: disable=no-member
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        balance=Balance(),
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
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        event_identifier=ZKL_IDENTIFIER.format(tx_hash=tx_hash.hex()),  # pylint: disable=no-member
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_USDT,
        balance=Balance(),
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
        fee=Fee(FVal('0.1659')),
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
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
    assert events == [EvmEvent(
        identifier=1,
        event_identifier=ZKL_IDENTIFIER.format(tx_hash=tx_hash.hex()),  # pylint: disable=no-member
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(FVal('0.01042855223')),
        location_label=address,
        notes='Swap 0.01042855223 ETH via ZKSync Lite',
        address=address,
    ), EvmEvent(
        identifier=2,
        event_identifier=ZKL_IDENTIFIER.format(tx_hash=tx_hash.hex()),  # pylint: disable=no-member
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        balance=Balance(FVal('37.082973')),
        location_label=address,
        notes='Receive 37.082973 USDT as the result of a swap via ZKSync Lite',
        address=address,
    ), EvmEvent(
        identifier=3,
        event_identifier=ZKL_IDENTIFIER.format(tx_hash=tx_hash.hex()),  # pylint: disable=no-member
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=ts_sec_to_ms(timestamp),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DAI,
        balance=Balance(FVal('0.1659')),
        location_label=address,
        notes='Swap fee of 0.1659 DAI',
        address=address,
    )]
