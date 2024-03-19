import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.l2.zksync import (
    ZksyncLite,
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
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_PAN, CURRENT_PRICE_MOCK
from rotkehlchen.types import Fee, Timestamp
from rotkehlchen.utils.misc import ts_now


@pytest.fixture(name='zksync_lite')
def fixture_zksync_lite(ethereum_inquirer, database):
    return ZksyncLite(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=None,  # not used atm
        msg_aggregator=None,  # not used atm
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_transactions(zksync_lite):
    transactions = zksync_lite.get_transactions(
        address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        start_ts=0,
        end_ts=ts_now(),
    )
    assert len(transactions) == 16
    assert transactions[15] == ZKSyncLiteTransaction(
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
    assert transactions[14] == ZKSyncLiteTransaction(
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
    assert transactions[10] == ZKSyncLiteTransaction(
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
    for idx in (3, 4, 5, 6, 7):
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
    for idx in (3, 4, 5, 6, 7):
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
    assert transactions[1] == ZKSyncLiteTransaction(
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
    assert transactions[0] == ZKSyncLiteTransaction(
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
def test_balances(zksync_lite, inquirer):  # pylint: disable=unused-argument
    lefty, rotki = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '0x9531C059098e3d194fF87FebB587aB07B30B1306'  # noqa: E501
    balances = zksync_lite.get_balances(addresses=[lefty, rotki])
    assert balances == {
        lefty: {
            A_ETH: Balance(FVal('6.6308508258'), CURRENT_PRICE_MOCK),
        },
        rotki: {
            A_ETH: Balance(FVal('0.20670353608092'), CURRENT_PRICE_MOCK),
            A_MANA: Balance(FVal('16.38'), CURRENT_PRICE_MOCK),
            A_UNI: Balance(FVal('2.1409'), CURRENT_PRICE_MOCK),
            A_WBTC: Balance(FVal('0.00012076'), CURRENT_PRICE_MOCK),
            A_LINK: Balance(FVal('0.47523'), CURRENT_PRICE_MOCK),
            A_DAI: Balance(FVal('46.16024376'), CURRENT_PRICE_MOCK),
            EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'): Balance(FVal('2.4306'), CURRENT_PRICE_MOCK),  # noqa: E501  # FRAX
            A_USDC: Balance(FVal('98.233404'), CURRENT_PRICE_MOCK),
            EvmToken('eip155:1/erc20:0xB64ef51C888972c908CFacf59B47C1AfBC0Ab8aC'): Balance(FVal('4.1524'), CURRENT_PRICE_MOCK),  # noqa: E501  # STORJ
            A_LRC: Balance(FVal('0.95'), CURRENT_PRICE_MOCK),
            A_SNX: Balance(FVal('0.95'), CURRENT_PRICE_MOCK),
            A_PAN: Balance(FVal('9202.65'), CURRENT_PRICE_MOCK),
            A_USDT: Balance(FVal('4.1'), CURRENT_PRICE_MOCK),
        },
    }
