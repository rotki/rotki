import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_GIVETH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.giveth.constants import GNOSIS_GIVPOWERSTAKING_WRAPPER
from rotkehlchen.chain.polygon_pos.modules.giveth.constants import GIVETH_DONATION_CONTRACT_ADDRESS
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xB9573982875b83aaDc1296726E2ae77D13D9B98F']])
def test_optimism_stake_deposit(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x875d69d471b2c31c5175848b11f68815e197fd609509cee420075685d21feccb')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1733231821000), optimism_accounts[0], '0.00000045219580173', '416.766115409070747461'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=37,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(ZERO),
            location_label=user,
            notes=f'Revoke GIV spending approval of {user} by {decoder.decoders["Giveth"].givpower_staking_address}',  # noqa: E501
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=38,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Deposit {amount} GIV for staking',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Receive {amount} POW after depositing GIV',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xB9573982875b83aaDc1296726E2ae77D13D9B98F']])
def test_optimism_lock(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x160a78b4ce5001b407db9f5fca3e64fcc0619995d8888c66605f69525eed0270')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, giv_amount, pow_amount = TimestampMS(1733231841000), optimism_accounts[0], '0.000000453377609571', '416.766115409070747461', '172.630177184494281415'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(giv_amount),
            location_label=user,
            notes=f'Lock {giv_amount} GIV for 1 round/s',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(pow_amount),
            location_label=user,
            notes=f'Receive {pow_amount} POW after locking GIV',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xAca2F322d69E07993E073C8730180FB139cA4446']])
def test_optimism_withdraw(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd687dcd65be8a2a9aea83123a9bdae775232af23e5846f01ade70f3f5280d392')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1732744801000), optimism_accounts[0], '0.000000258591448555', '798.24369413782804452'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Return {amount} POW to Giveth staking',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Withdraw {amount} GIV from staking',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x8a0F0a09e622bc0677a404343129FB5dDA1E2d33']])
def test_optimism_claim(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2144b2417404977fe2b4b4064b58cdaafc90e416e68a5ad16c04989cc025f3b1')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1732520935000), optimism_accounts[0], '0.000001950934408636', '55.906071953178772758'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=41,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Claim {amount} GIV',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].distro_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_gnosis_claim(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8a7edd5f0008f8838664404a2b2aab593b705149044865cbdeb75d2126130949')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1733756450000), gnosis_accounts[0], '0.000142777694803742', '66405.135269385928501434'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Claim {amount} GIV',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].distro_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xBe784DB8CB6909a6ff24AAD9a39dAd7E87642902']])
def test_gnosis_lock(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9a79d704dd637460a17bb3897df522c56deb4848d9d3b5630424c545e47172b5')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, giv_amount, pow_amount = TimestampMS(1733685985000), gnosis_accounts[0], '0.00026284575126455', '2617.351674315678177796', '10982.806567405488178331'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(giv_amount),
            location_label=user,
            notes=f'Lock {giv_amount} GIV for 26 round/s',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(pow_amount),
            location_label=user,
            notes=f'Receive {pow_amount} POW after locking GIV',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x5D28FE1e9F895464aab52287d85Ebff32B351674']])
def test_gnosis_stake_deposit(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xaee26eb3b311b318292d4c29c2ad9b050fc339bfaef6da2f329a43cdb89dcd9b')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1733536070000), gnosis_accounts[0], '0.000391221856613286', '100913.342801097979277274'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=27,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(ZERO),
            location_label=user,
            notes=f'Revoke GIV spending approval of {user} by {GNOSIS_GIVPOWERSTAKING_WRAPPER}',
            address=GNOSIS_GIVPOWERSTAKING_WRAPPER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=28,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Deposit {amount} GIV for staking',
            counterparty=CPT_GIVETH,
            address=GNOSIS_GIVPOWERSTAKING_WRAPPER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Receive {amount} POW after depositing GIV',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ),
    ]
    assert events == expected_events  # ignore the last receival of gGiv in Gnosis


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x5918D889E913c53288C17265280DAD439FEc8275']])
def test_gnosis_withdraw(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x277949402fb601446f5b8c7e751e72df0f4687b38612935211542b3f4b3f2cf4')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user, gas, amount = TimestampMS(1733322280000), gnosis_accounts[0], '0.00046583297133306', '4927.159556510935243873'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].pow_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Return {amount} POW to Giveth staking',
            counterparty=CPT_GIVETH,
            address=decoder.decoders['Giveth'].givpower_staking_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken(decoder.decoders['Giveth'].giv_token_id),
            amount=FVal(amount),
            location_label=user,
            notes=f'Withdraw {amount} GIV from staking',
            counterparty=CPT_GIVETH,
            address=GNOSIS_GIVPOWERSTAKING_WRAPPER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x2345678901234567890123456789012345678901']])
def test_giveth_donation_pol(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2f39809f4cab0e97ee12eb5a70fd76a28c2855ccc2b840f2030844c7e81b2e43')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1754368465000),
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0x0000000000000000000000000000000000001010'),
        amount=(donation_amount := FVal('0.01')),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive a giveth donation of {donation_amount} POL from 0x47498b788942a74DB601B117bd406a8C5369a32F',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=GIVETH_DONATION_CONTRACT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x29EE09Bd0f7f41EcD083Ad2708Df17691065790B']])
def test_giveth_donation_erc20(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0b7bbafb80a494ab65eaf8b8f38f3afca1bd4f8979dc6c72b090bb609dd6d329')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1213,
        timestamp=TimestampMS(1756375213000),
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('28.894081')),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive a giveth donation of {donation_amount} TPOL from 0xEA2dB4736F6D8Cacb3532eDf37D15a29466Daaa7',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xEA2dB4736F6D8Cacb3532eDf37D15a29466Daaa7'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xB5Ab1C37ac3d89A48f32307C4DfCc96F79BeAd27']])
def test_giveth_donation_sender(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9150c5c1dfc5a587b43f5dc39c585af2c6e16cd62396f6d2feb6bafd77e9edac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1756386087000)),
        sequence_index=0,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:137/erc20:0x0000000000000000000000000000000000001010'),
        amount=(gas_amount := FVal('0.002843750017390625')),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=363,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('2.673594')),
        location_label=user_address,
        notes=f'Make a giveth donation of {donation_amount} TPOL to 0xcd192b61a8Dd586A97592555c1f5709e032F2505',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xcd192b61a8Dd586A97592555c1f5709e032F2505'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=365,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('4.455991')),
        location_label=user_address,
        notes=f'Make a giveth donation of {donation_amount} TPOL to 0xd10BAC02a02747cB293972f99981F4Faf78E1626',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xd10BAC02a02747cB293972f99981F4Faf78E1626'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=367,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('46.363509')),
        location_label=user_address,
        notes=f'Make a giveth donation of {donation_amount} TPOL to 0xBBdA03b2f234E57e0cf7eC85F493aa4162762A1a',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xBBdA03b2f234E57e0cf7eC85F493aa4162762A1a'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=369,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('24.401905')),
        location_label=user_address,
        notes=f'Make a giveth donation of {donation_amount} TPOL to 0xCd144358cC53c01909166A8412FcfaACa689e4c3',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xCd144358cC53c01909166A8412FcfaACa689e4c3'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=371,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=Asset('eip155:137/erc20:0xc20CAf8deE81059ec0c8E5971b2AF7347eC131f4'),
        amount=(donation_amount := FVal('11.224832')),
        location_label=user_address,
        notes=f'Make a giveth donation of {donation_amount} TPOL to 0xc5319dbdcC2930778c1473Ddc8E8F1606252e675',  # noqa: E501
        counterparty=CPT_GIVETH,
        address=string_to_evm_address('0xc5319dbdcC2930778c1473Ddc8E8F1606252e675'),
    )]
