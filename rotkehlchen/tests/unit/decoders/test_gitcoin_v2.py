import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_GITCOIN
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_optimism_donation_received(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0x08685669305ee26060a5a78ae70065aec76d9e62a35f0837c291fb1232f33601')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1692176477000)
    amount_str = '0.00122'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Receive a gitcoin donation of {amount_str} ETH from 0xf0C2007aD05a8d66e98be932C698c232292eC8eA',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address='0x99906Ea77C139000681254966b397a98E4bFdE21',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethereum_donation_received(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x71fc406467f342f5801560a326aa29ac424381daf17cc04b5573960425ba605b')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    amount_str = '0.001'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=TimestampMS(1683655379000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=ethereum_accounts[0],
        notes=f'Receive a gitcoin donation of {amount_str} ETH from 0xc191a29203a83eec8e846c26340f828C68835715',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address='0xDA2F26B30e8f5aa9cbE9c5B7Ed58E1cA81D0EbF2',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x1B274eaCc333F4a904D72b576B55A108532aB379',
    # also track a grantee to see we handle donating to self fine
    '0xB352bB4E2A4f27683435f153A259f1B207218b1b',
]])
def test_ethereum_make_donation(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xd8d55b66f19a6dbf260d171fbb0c4c146f00c90919f1215cf691d7f0684771c6')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    tracked_grant = ethereum_accounts[1]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1683676595000)
    amount_str = '0.0006'
    gas_str = '0.011086829409239852'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Transfer a gitcoin donation of {amount_str} ETH to {tracked_grant}',
        counterparty=CPT_GITCOIN,
        address=tracked_grant,
    )]

    expected_events += [EvmEvent(
        tx_hash=evmhash,
        sequence_index=idx,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Make a gitcoin donation of {amount_str} ETH to {grant_address}',
        counterparty=CPT_GITCOIN,
        address=grant_address,
    ) for idx, grant_address in [
        (2, '0x713Bc00D1df5C452F172C317D39eFf71B771C163'),
        (107, '0xDEcf6615152AC768BFB688c4eF882e35DeBE08ac'),
        (109, '0x187089b65520D2208aB93FB471C4970c29eAf929'),
        (111, '0xb7081Fd06E7039D198D10A8b72B824e60C1B1E16'),
    ]]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_optimism_create_project(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0xe59f04c693e91f1659bd8bc718c993158efeb9af02c9c6337f039c44d8a822f6')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1691697693000)
    gas_str = '0.000085459641651569'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=65,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.DEPLOY,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes=f'Create gitcoin project with id 779 and owner {user_address}',
        counterparty=CPT_GITCOIN,
        address='0x8e1bD5Da87C14dd8e08F7ecc2aBf9D1d558ea174',
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=66,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.UPDATE,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes='Update gitcoin project with id 779',
        counterparty=CPT_GITCOIN,
        address='0x8e1bD5Da87C14dd8e08F7ecc2aBf9D1d558ea174',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethereum_project_apply(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3e4639d97be450c6d32ce77a146898780b75781caaf004d3c40bae083dec07c7')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1673472803000)
    gas_str = '0.000645250895735256'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=413,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPLY,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes='Apply to gitcoin round with project application id 0x755e5c4d042c1245555075b699e774c2ed0f0f1499460201fc936a0595e91683',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address='0xe575282b376E3c9886779A841A2510F1Dd8C2CE4',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethereum_project_update(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xfe00fa198eb5395e1d809e017c6b416e882b0aef16e82bf00cd60ce5576bb122')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1681330523000)
    gas_str = '0.001464795019471285'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=192,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.UPDATE,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes='Update gitcoin project with id 128',
        counterparty=CPT_GITCOIN,
        address='0x03506eD3f57892C85DB20C36846e9c808aFe9ef4',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xd034Fd34eaEe5eC2c413C51936109E12873f4DA5']])
def test_optimism_many_donations_different_strategies(database, optimism_inquirer, optimism_accounts):  # noqa: E501
    tx_hex = deserialize_evm_tx_hash('0x5d85b436f5f177de6019baa9ecebae285e0def4924546307fac40556bece4cd7')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1692300843000)
    gas_str = '0.004506208027331091'
    op_dai = Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')
    assert events[0:2] == [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=50,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=op_dai,
        balance=Balance(FVal('147.7')),
        location_label=user_address,
        notes=f'Set DAI spending approval of {user_address} by 0x15fa08599EB017F89c1712d0Fe76138899FdB9db to 147.7',  # noqa: E501
        address='0x15fa08599EB017F89c1712d0Fe76138899FdB9db',
    )]

    assert len(events) == 121  # 119 donations plus the 2 events above
    for event in events[2:]:
        assert event.location == Location.OPTIMISM
        assert event.event_type == HistoryEventType.SPEND
        assert event.event_subtype == HistoryEventSubType.DONATE
        assert event.asset == op_dai
        assert FVal(1) <= event.balance.amount <= FVal(5)
        assert event.location_label == user_address
        assert event.notes.startswith('Make a gitcoin donation')
        assert event.counterparty == CPT_GITCOIN


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_optimism_grant_payout(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0x84110136c94ceb71c72afb27ccb517eb33f77a8a419d125101644e2c43294815')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    amount_str = '1228.529999999999934464'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=73,
        timestamp=TimestampMS(1696942367000),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),  # DAI
        balance=Balance(amount=FVal(amount_str)),
        location_label=optimism_accounts[0],
        notes=f'Receive matching payout of {amount_str} DAI for a gitcoin round',
        counterparty=CPT_GITCOIN,
        address='0xEb33BB3705135e99F7975cDC931648942cB2A96f',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethereum_grant_payout(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x66ff5be7841f05cc9cb53fd0307460690f91203c52490f5bbfdeabe8462be50b')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    amount_str = '20000'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=313,
        timestamp=TimestampMS(1689038123000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_DAI,
        balance=Balance(amount=FVal(amount_str)),
        location_label=ethereum_accounts[0],
        notes=f'Receive matching payout of {amount_str} DAI for a gitcoin round',
        counterparty=CPT_GITCOIN,
        address='0xebaF311F318b5426815727101fB82f0Af3525d7b',
    )]
    assert events == expected_events
