import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants.assets import A_ETH_EURE, A_GNOSIS_EURE, A_POLYGON_EURE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da']])
def test_minting_monerium_on_eth(database, ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '1500'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=113,
            timestamp=TimestampMS(1701773255000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=ethereum_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x99a0618B846D43E29C15ac468Eae06d03C9243C7']])
def test_burning_monerium_on_eth(database, ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '1161210.84'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=171,
            timestamp=TimestampMS(1701765059000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=ethereum_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('polygon_pos_accounts', [['0x762e5f511c219823eeC73C743C8245807A53E123']])
def test_minting_monerium_on_matic(database, polygon_pos_inquirer, polygon_pos_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xb240acc158fb2cdcdebc7321ca4a96f71b371379e2a78a9a7f27d0718a2e3735')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '95'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=176,
            timestamp=TimestampMS(1701800519000),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=polygon_pos_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('polygon_pos_accounts', [['0x0A251dF99A88A20a93876205Fb7f5Faf2E85A481']])
def test_burning_monerium_on_matic(database, polygon_pos_inquirer, polygon_pos_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xeaed8e3e862a9b41189e9039c825ee57fb80385801b8ac5c3ed70339baf243e5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '208.93'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=418,
            timestamp=TimestampMS(1701794990000),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('gnosis_accounts', [['0x9566E3e6F55D4378243E55DE8e037Ee8E6e4de7E']])
def test_minting_monerium_on_gnosis(database, gnosis_inquirer, gnosis_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x31183d757f530f799872600e6fe8644e3c20a1f90d02de9e89d0463454b400fa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '66'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=371,
            timestamp=TimestampMS(1701802945000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GNOSIS_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=gnosis_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('gnosis_accounts', [['0xAf31992307AcBb6Ad8795261EeA31494e62A8e40']])
def test_burning_monerium_on_gnosis(database, gnosis_inquirer, gnosis_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xae087f309231e4dc1fa84927888deb6c56b9980e63f9cc049cbe2d7d2bc503e6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    amount_str = '1'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=500,
            timestamp=TimestampMS(1701801200000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GNOSIS_EURE,
            balance=Balance(amount=FVal(amount_str)),
            location_label=gnosis_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events
