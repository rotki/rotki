import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.balances.manual import ManuallyTrackedBalance, add_manually_tracked_balances
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.utils import read_hash
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.serialization import rlk_jsondumps

TEST_DATA = {
    'a': FVal('5.4'),
    'b': 'foo',
    'c': FVal('32.1'),
    'd': 5,
    'e': [1, 'a', FVal('5.1')],
    'f': A_ETH,
    A_BTC: 'test_with_asset_key',
}


def test_rlk_jsondumps():
    result = rlk_jsondumps(TEST_DATA)
    assert result == (
        '{"a": "5.4", "b": "foo", "c": "32.1", "d": 5, '
        '"e": [1, "a", "5.1"], "f": "ETH", "BTC": "test_with_asset_key"}'
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_deserialize_location(database):
    balances = []
    for idx, data in enumerate(Location):
        assert Location.deserialize(str(data)) == data
        balances.append(ManuallyTrackedBalance(
            identifier=-1,
            asset=A_BTC,
            label='Test' + str(idx),
            amount=ONE,
            location=data,
            tags=None,
            balance_type=BalanceType.ASSET,
        ))

    with pytest.raises(DeserializationError):
        Location.deserialize('dsadsad')

    with pytest.raises(DeserializationError):
        Location.deserialize(15)

    # Also write and read each location to DB to make sure that
    # location.serialize_for_db() and deserialize_location_from_db work fine
    add_manually_tracked_balances(database, balances)
    with database.conn.read_ctx() as cursor:
        balances = database.get_manually_tracked_balances(cursor)
    for data in Location:
        assert data in (x.location for x in balances)


def test_deserialize_int_from_hex_or_int():
    # Etherscan can return logIndex 0x if it's the 0th log in the hash
    # https://etherscan.io/tx/0x6f1370cd9fa19d550031a30290b062dd3b56f44caf6344c05545ef15428de7ef
    assert deserialize_int_from_hex_or_int('0x', 'whatever') == 0
    assert deserialize_int_from_hex_or_int('0x1', 'whatever') == 1
    assert deserialize_int_from_hex_or_int('0x33', 'whatever') == 51
    assert deserialize_int_from_hex_or_int(66, 'whatever') == 66


def test_deserialize_deployment_ethereum_transaction():
    data = {
        'timeStamp': 0,
        'blockNumber': 1,
        'hash': '0xc5be14f87be25174846ed53ed239517e4c45c1fe024b184559c17d4f1fefa736',
        'from': '0x568Ab4b8834646f97827bB966b13d60246157B8E',
        'to': None,
        'value': 0,
        'gas': 1,
        'gasPrice': 1,
        'gasUsed': 1,
        'input': '',
        'nonce': 1,
    }
    tx, _ = deserialize_evm_transaction(
        data=data,
        internal=False,
        chain_id=ChainID.ETHEREUM,
        evm_inquirer=None,
    )
    expected = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
        block_number=1,
        tx_hash=deserialize_evm_tx_hash(data['hash']),
        from_address=deserialize_evm_address(data['from']),
        to_address=None,
        value=data['value'],
        gas=data['gas'],
        gas_price=data['gasPrice'],
        gas_used=data['gasUsed'],
        input_data=read_hash(data, 'input'),
        nonce=data['nonce'],
    )
    assert tx == expected
