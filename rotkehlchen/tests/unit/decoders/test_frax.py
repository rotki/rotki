import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.frax.constants import CPT_FRAX
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import GeneralCacheType, Location, TimestampMS, deserialize_evm_tx_hash

TEST_FRAX_PAIRS = [
    '0x794F6B13FBd7EB7ef10d1ED205c9a416910207Ff',
]


def _populate_frax_pairs(evm_tx_decoder) -> None:
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.FRAXLEND_PAIRS],
            values=TEST_FRAX_PAIRS,
        )

    frax_decoder = evm_tx_decoder.decoders['Frax']
    new_mappings = frax_decoder.reload_data()
    evm_tx_decoder.rules.address_mappings.update(new_mappings)


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x0f2CD0C6474594b2D3830E1076F40D6828641a0f']])  # noqa: E501
def test_frax_deposit(database, ethereum_inquirer, ethereum_transaction_decoder):
    """Data taken from
    https://etherscan.io/tx/0xb8ddd076f29aa8182a373499f314360582c92b4ceece2775f51979301473bf7d
    tests that adding collateral for the WETH-FRAX pair in frax works correctly
    """
    _populate_frax_pairs(ethereum_transaction_decoder)
    tx_hash = deserialize_evm_tx_hash(
        '0xb8ddd076f29aa8182a373499f314360582c92b4ceece2775f51979301473bf7d',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )

    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1674225647000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(0.002161301427906534)),
            location_label='0x0f2CD0C6474594b2D3830E1076F40D6828641a0f',
            notes='Burned 0.002161301427906534 ETH for gas',
            counterparty=CPT_GAS,
        ),
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=287,
            timestamp=TimestampMS(1674225647000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(FVal(1)),
            location_label='0x0f2CD0C6474594b2D3830E1076F40D6828641a0f',
            notes='Deposit 1 WETH in Fraxlend pair 0x794F6B13FBd7EB7ef10d1ED205c9a416910207Ff',
            counterparty=CPT_FRAX,
        ),
    ]
    assert events == expected_events
