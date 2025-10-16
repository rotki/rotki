import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.liquity.constants import (
    ACTIVE_POOL,
    BORROWER_OPERATIONS,
    CPT_LIQUITY,
    LIQUITY_STAKING,
    STABILITY_POOL,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import LIQUITY_STAKING_DETAILS, EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x9ba961989Dd6609Ed091f512bE947118c40F2291']])
def test_deposit_eth_borrow_lusd(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdb9a541a4af7d5d46d7ea5fe4a2a752dcb731d64d052f86f630e97362063602c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_str, fee_str, debt_str, timestamp, user_address = '0.013622314246080246', '23.795404790091371686', '4774.957410610241615030', TimestampMS(1650878514000), ethereum_accounts[0]  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_ETH,
        amount=FVal('2.1'),
        location_label=user_address,
        notes='Deposit 2.1 ETH as collateral for liquity',
        counterparty=CPT_LIQUITY,
        address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_LUSD,
        amount=FVal(debt_str),
        location_label=user_address,
        notes=f'Generate {debt_str} LUSD from liquity',
        counterparty=CPT_LIQUITY,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_LUSD,
        amount=FVal(fee_str),
        location_label=user_address,
        notes=f'Paid {fee_str} LUSD as a borrowing fee',
        counterparty=CPT_LIQUITY,
        address=BORROWER_OPERATIONS,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])
def test_payback_lusd(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x40bb08427a3b99fb9896cf14858d82d361a6e7a8fb7dd6d2000511ac3dca5707')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1650746429000)
    gas_str, amount_str = '0.006264200693494173', '118184.07'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=208,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYBACK_DEBT,
        asset=A_LUSD,
        amount=FVal(amount_str),
        location_label=user_address,
        notes=f'Pay back {amount_str} LUSD debt to liquity',
        counterparty=CPT_LIQUITY,
        address=ZERO_ADDRESS,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])
def test_remove_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6be5312c21855c3cc324b5b6ce9f9f65dbd488e270e84ac5e6fb96c74d83fe4e')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1650998125000)
    gas_str, amount_str = '0.016981969690997082', '32'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_ETH,
        amount=FVal(amount_str),
        location_label=user_address,
        notes=f'Withdraw {amount_str} ETH collateral from liquity',
        counterparty=CPT_LIQUITY,
        address=ACTIVE_POOL,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF04E6f2D27ED324917AD2098F96f5d4ac52e1684']])
def test_stability_pool_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1277cb6c2c8e151fe90118cdd738e46f894e18de04ab6af33d567e91597f322b')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1665994475000)
    gas_str, amount_str, fee_str = '0.003626058925730277', '120', '4.970574827214596312'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=903,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_LQTY,
        amount=FVal(fee_str),
        location_label=user_address,
        notes=f'Paid {fee_str} LQTY as a frontend fee to 0x30E5D10DC30a0CE2545a4dbe8DE4fCbA590062c5',  # noqa: E501
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=908,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_LUSD,
        amount=FVal(amount_str),
        location_label=user_address,
        notes=f"Deposit {amount_str} LUSD in liquity's stability pool",
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF03639047f75204d00c9314611C2b24570db4405']])
def test_stability_pool_collect_rewards(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xad077faf7976504615561ac7fd9fdddc934180f3237f216851136d2327d71196')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_str, eth_str, got_lqty_str, fee_lqty_str = TimestampMS(1665913919000), ethereum_accounts[0], '0.00249609940900398', '0.0211265398269', '1308.878062778294406909', '13.810598430718930388'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=134,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_LQTY,
        amount=FVal(fee_lqty_str),
        location_label=user_address,
        notes=f'Paid {fee_lqty_str} LQTY as a frontend fee to 0x03Cd116CABE0747F31A71B3565877717097fc06C',  # noqa: E501
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=135,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_ETH,
        amount=FVal(eth_str),
        location_label=user_address,
        notes=f"Collect {eth_str} ETH from liquity's stability pool",
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=136,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LQTY,
        amount=FVal(got_lqty_str),
        location_label=user_address,
        notes=f"Collect {got_lqty_str} LQTY from liquity's stability pool",
        counterparty=CPT_LIQUITY,
        address=string_to_evm_address('0xD8c9D9071123a059C6E0A945cF0e0c82b508d816'),
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x1b63708eafa610DFa81c6DB4A257570D78a6dF1c']])
def test_increase_lqty_staking(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4e2bbc53a75fbbc954fc305f7adf68be1fa3b1416c941b0350719cc484c9d8fb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, eth_str, lqty_str, lusd_str = ethereum_accounts[0], TimestampMS(1667784263000), '0.001329619874685459', '0.000047566872899089', '89.99999999999997', '1.134976028981709316'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_LQTY,
        amount=FVal(lqty_str),
        location_label=user_address,
        notes=f'Stake {lqty_str} LQTY in the Liquity protocol',
        counterparty=CPT_LIQUITY,
        address=LIQUITY_STAKING,
        extra_data={LIQUITY_STAKING_DETAILS: {'staked_amount': '171.95999999999998', 'asset': A_LQTY}},  # noqa: E501
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_ETH,
        amount=FVal(eth_str),
        location_label=user_address,
        notes=f"Receive reward of {eth_str} ETH from Liquity's staking",
        counterparty=CPT_LIQUITY,
        address=LIQUITY_STAKING,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LUSD,
        amount=FVal(lusd_str),
        location_label=user_address,
        notes=f"Receive reward of {lusd_str} LUSD from Liquity's staking",
        counterparty=CPT_LIQUITY,
        address=LIQUITY_STAKING,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x58D9A499AC82D74b08b3Cb76E69d8f32e1395746']])
def test_remove_liquity_staking(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x028397f0409042da26890ec27eb36d617e326c3ce476d823f181419bdd0ad860')  # noqa: E501
    user_address = string_to_evm_address('0x58D9A499AC82D74b08b3Cb76E69d8f32e1395746')
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, eth_str, lqty_str, lusd_str = ethereum_accounts[0], TimestampMS(1667817419000), '0.001768189006455498', '0.000215197741630696', '372.883717436930835121', '2.476877599503048728'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_LQTY,
        amount=FVal(lqty_str),
        location_label=user_address,
        notes=f'Unstake {lqty_str} LQTY from the Liquity protocol',
        counterparty=CPT_LIQUITY,
        address=LIQUITY_STAKING,
        extra_data={LIQUITY_STAKING_DETAILS: {'staked_amount': '0', 'asset': A_LQTY}},
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_ETH,
        amount=FVal(eth_str),
        location_label=user_address,
        notes=f"Receive reward of {eth_str} ETH from Liquity's staking",
        address=LIQUITY_STAKING,
        counterparty=CPT_LIQUITY,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LUSD,
        amount=FVal(lusd_str),
        location_label=user_address,
        notes=f"Receive reward of {lusd_str} LUSD from Liquity's staking",
        counterparty=CPT_LIQUITY,
        address=LIQUITY_STAKING,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5DD596C901987A2b28C38A9C1DfBf86fFFc15d77']])
def test_stability_pool_withdrawal(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xca9acc377ba5eb020dd5f113961016ac1c652617b0e5c71f31a7fb32e188858d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    user_address, timestamp, gas_str, lqty_fee_str, lqty_amount_str, withdraw_str = ethereum_accounts[0], TimestampMS(1677402143000), '0.00719440411023624', '1.028279761898401648', '1.3168840890645', '500000'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=190,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_LQTY,
        amount=FVal(lqty_fee_str),
        location_label=user_address,
        notes=f'Paid {lqty_fee_str} LQTY as a frontend fee to 0x30E5D10DC30a0CE2545a4dbe8DE4fCbA590062c5',  # noqa: E501
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=191,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_LUSD,
        amount=FVal(withdraw_str),
        location_label=user_address,
        notes=f"Withdraw {withdraw_str} LUSD from liquity's stability pool",
        counterparty=CPT_LIQUITY,
        address=STABILITY_POOL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=192,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LQTY,
        amount=FVal(lqty_amount_str),
        location_label=user_address,
        notes=f"Collect {lqty_amount_str} LQTY from liquity's stability pool",
        counterparty=CPT_LIQUITY,
        address=string_to_evm_address('0xD8c9D9071123a059C6E0A945cF0e0c82b508d816'),
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c3ce74FCB2B93F9244544919572818Dc2AC0641']])
def test_ds_proxy_liquity_deposit(ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x83e9930bee6a993204ade072ac6753249f9773b0da243b7efdb6cbba1e0bff6c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002962168608405875'),
            location_label=user_address,
            notes='Burn 0.002962168608405875 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=291,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            amount=FVal('87.49718915849563905'),
            location_label=user_address,
            notes="Deposit 87.49718915849563905 LUSD in liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=292,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LUSD,
            amount=FVal('115792089237316195423570985008687907853269984665640564039370.086818754634000885'),
            location_label=user_address,
            notes='Set LUSD spending approval of 0x0c3ce74FCB2B93F9244544919572818Dc2AC0641 by 0x7815beb98a927565eA43b5854644392F21dA0021 to 115792089237316195423570985008687907853269984665640564039370.086818754634000885',  # noqa: E501
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x67faB33a151F8d1e57e2aF0E021B11526B71A0f1']])
def test_ds_proxy_liquity_deposit_and_borrow(ethereum_inquirer, ethereum_accounts):
    """This test via DSProxy deposit and borrow is to test that the fee comes after borrowing
    in those cases as we had to add logic to handle it. Otherwise it's a missing acquisition if fee
    comes before borrowing"""
    tx_hash = deserialize_evm_tx_hash('0x48c93d086f9927f0e2aaadf39fa3bfdcf7f5ac80b11024a7055415c6bac5c829')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1736007179000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.009018175299183188'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal(eth_amount := '40'),
            location_label=user_address,
            notes=f'Deposit {eth_amount} ETH as collateral for liquity',
            counterparty=CPT_LIQUITY,
            address=(dsproxy_195537 := string_to_evm_address('0x6CD9bD4103437aFaE97b8947ED92e40a92775321')),  # noqa: E501
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=149,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_LUSD,
            amount=FVal(lusd_debt := '40000'),
            location_label=user_address,
            notes=f'Generate {lusd_debt} LUSD from liquity',
            counterparty=CPT_LIQUITY,
            address=dsproxy_195537,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=150,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_LUSD,
            amount=FVal(lusd_fee := '201.07208093721936'),
            location_label=user_address,
            notes=f'Paid {lusd_fee} LUSD as a borrowing fee',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c3ce74FCB2B93F9244544919572818Dc2AC0641']])
def test_ds_proxy_liquity_withdraw(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdac8d9273a17b00fb81e89839d0c974e393db406a641552051419646b902c4b3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002590429704686116'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.002590429704686116 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LUSD,
            amount=FVal('87.456384085561687234'),
            location_label=ethereum_accounts[0],
            notes="Withdraw 87.456384085561687234 LUSD from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            amount=FVal('0.000033225735796413'),
            location_label=ethereum_accounts[0],
            notes="Collect 0.000033225735796413 ETH from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            amount=FVal('0.233230483618895237'),
            location_label=ethereum_accounts[0],
            notes="Collect 0.233230483618895237 LQTY from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xEa00FC641a817e5F3eded4743aac7AB08dbf74b0']])
def test_ds_proxy_liquity_staking(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x48aa71f1af847d93601f03777ba960281bc9405bbdcc2fdb8c64f2a3350f354a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.009100878613428384'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.009100878613428384 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=197,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LQTY,
            amount=FVal('0'),
            location_label=ethereum_accounts[0],
            notes='Revoke LQTY spending approval of 0xEa00FC641a817e5F3eded4743aac7AB08dbf74b0 by 0x31E45D87D9549DCc5cc28925238b7e329719C8fB',  # noqa: E501
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=198,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LQTY,
            amount=FVal('4584.01'),
            location_label=ethereum_accounts[0],
            notes='Stake 4584.01 LQTY in the Liquity protocol',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
            extra_data={
                'liquity_staking': {
                    'staked_amount': '11325.738578026449094146',
                    'asset': 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D',
                },
            },
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=199,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            amount=FVal('0.000000820336735695'),
            location_label=ethereum_accounts[0],
            notes="Receive reward of 0.000000820336735695 ETH from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=200,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LUSD,
            amount=FVal('6.17725146534640172'),
            location_label=ethereum_accounts[0],
            notes="Receive reward of 6.17725146534640172 LUSD from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF35da7a42d92c7919172195aA7BC7a0d43eC866c']])
def test_ds_proxy_borrow_lusd(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa7404dc759fdef08fde6dbb227d6c55276861853d274c9a739236488a123f794')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_str, debt_str, fee_str = TimestampMS(1704486503000), ethereum_accounts[0], '0.006847541539452045', '50300.21680310311845', '300.21680310311845'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_str),
        location_label=user_address,
        notes=f'Burn {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_LUSD,
        amount=FVal(debt_str),
        location_label=user_address,
        notes=f'Generate {debt_str} LUSD from liquity',
        counterparty=CPT_LIQUITY,
        address=string_to_evm_address('0x76eb7232943AAe8546440A945C2D6bDd146C0299'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_LUSD,
        amount=FVal(fee_str),
        location_label=user_address,
        notes=f'Paid {fee_str} LUSD as a borrowing fee',
        counterparty=CPT_LIQUITY,
        address=BORROWER_OPERATIONS,
    )]
    assert events == expected_events
