import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.makerdao.constants import MKR_ADDRESS
from rotkehlchen.chain.ethereum.modules.sky.constants import (
    CPT_SKY,
    DAI_TO_USDS_CONTRACT,
    MIGRATION_ACTIONS_CONTRACT,
    SKY_ASSET,
    SUSDS_ASSET,
    SUSDS_CONTRACT,
    USDS_ASSET,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_MKR, A_SDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfb10EFE8d84E73061ABDfa5F87f26aFC1f0a98f5']])
def test_migrate_dai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xda915701a7634628d8301d44a4e122599f05a1281286ab416f5101c79a24e408')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726732211000)
    gas_amount, migrated_amount = '0.001933756075256005', '10086.448037727051859359'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=115,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Migrate {migrated_amount} DAI to USDS',
        counterparty=CPT_SKY,
        address=DAI_TO_USDS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=120,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=USDS_ASSET,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {migrated_amount} USDS from DAI to USDS migration',
        counterparty=CPT_SKY,
        address=DAI_TO_USDS_CONTRACT,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xAe289D2618CcFA247645Dd8e89326c91acEF62e0']])
def test_migrate_sdai_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5d4d8d4c9480ad603c91cd7a7e90fdf6faa2327728602e10b55620b18e642a91')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746824531000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00044435901000267'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=780,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SDAI,
        amount=FVal(from_amount := '114937.403727239587040651'),
        location_label=user,
        notes=f'Migrate {from_amount} sDAI ({(underlying_dai := "133037.184652873382652036")} DAI) to sUSDS',  # noqa: E501
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
        extra_data={'underlying_amount': underlying_dai},
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=790,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),  # sUSDS
        amount=FVal(to_amount := '126610.495160713536806542'),
        location_label=user,
        notes=f'Receive {to_amount} sUSDS ({(underlying_usds := "133037.184652873382652036")} USDS) from sDAI to sUSDS migration',  # noqa: E501
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
        extra_data={'underlying_amount': underlying_usds},
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x11365778D2cC21aD47286073e6f764d862CA0cb1']])
def test_migrate_dai_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd29f7d1aa194dae5fa2dcccaeef0acf37390bc847f51a6eb2e8bdcf4df32dc45')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746775787000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.001458066094125402'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=378,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal(from_amount := '6145.584263394667728636'),
        location_label=user,
        notes=f'Migrate {from_amount} DAI to sUSDS',
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=392,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),  # sUSDS
        amount=FVal(to_amount := '5849.104582127060478762'),
        location_label=user,
        notes=f'Receive {to_amount} sUSDS ({(underlying_usds := "6145.584263394667728636")} USDS) from DAI to sUSDS migration',  # noqa: E501
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
        extra_data={'underlying_amount': underlying_usds},
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xaE6396d2fB733e124f9b1C3BF922cF17fE1CC75A']])
def test_redeem_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2e5bac2cb234a4388d45754656bad35cc03c7dde7745de10b5b605ff28187d52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726736615000)
    gas_amount, returned_amount, withdrawn_amount = '0.002553705360907168', '76400.28490997120343213', '76424.11'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=SUSDS_ASSET,
        amount=FVal(returned_amount),
        location_label=ethereum_accounts[0],
        notes=f'Return {returned_amount} sUSDS to sUSDS contract',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=USDS_ASSET,
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Withdraw {withdrawn_amount} USDS from sUSDS contract',
        counterparty=CPT_SKY,
        address=SUSDS_CONTRACT,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2618d8078253b4765fd4ea56b3840c212830E9a3']])
def test_deposit_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe9ca86a0ce9c0226d65203805b77d13697ad5e579989505562638095dc45cac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726754135000)
    gas_amount, deposited_amount, withdrawn_amount = '0.003750084090503928', '5114.68', '5112.913299374006156278'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=309,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=USDS_ASSET,
        amount=FVal(deposited_amount),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposited_amount} USDS to sUSDS contract',
        counterparty=CPT_SKY,
        address=SUSDS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=311,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=SUSDS_ASSET,
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Withdraw {withdrawn_amount} sUSDS from sUSDS contract',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4Bb80Ba800f39b9237ce6e05a338962885d5F474']])
def test_migrate_maker(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbfa0b5489a1f4b28c416d0ef8cbcbbc9d7d4fea8c3f1d53830b2cd5f78252b79')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726760855000)
    gas_amount, migrated_amount, received_amount = '0.00127609766341068', '0.75001216', '18000.29184'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_MKR,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Migrate {migrated_amount} MKR to SKY',
        counterparty=CPT_SKY,
        address=MKR_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=SKY_ASSET,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} SKY from MKR to SKY migration',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x66AE6A0591c6Fb84Fe1fD27F4976dDEC6430d805']])
def test_downgrade_usds_dai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2cf64d3e95e39e77dd3e02c458ddb1e22b5aea38f8d93f64cf79174f601ddc20')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746660575000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00011343597080725'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=USDS_ASSET,
        amount=FVal(amount := '540310.221137197108444258'),
        location_label=user,
        notes=f'Downgrade {amount} USDS to DAI',
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=17,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DAI,
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} DAI from USDS to DAI downgrade',
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1170313034adD8c24389550711E86c902cacfB33']])
def test_migrate_dai_usds(ethereum_inquirer, ethereum_accounts):
    """Migrate DAI to USDS through the migration actions contract"""
    tx_hash = deserialize_evm_tx_hash('0xeafdd9789b99498466d9afffdb2087adaaba419b62c0adbcda17ff4c2e239a85')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1747020191000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000237343245854033'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=60,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal(amount := '200'),
        location_label=user,
        notes=f'Migrate {amount} DAI to USDS',
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=65,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=USDS_ASSET,
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} USDS from DAI to USDS migration',
        counterparty=CPT_SKY,
        address=MIGRATION_ACTIONS_CONTRACT,
    )]
    assert expected_events == events
