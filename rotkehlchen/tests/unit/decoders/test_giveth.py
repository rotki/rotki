import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_GIVETH
from rotkehlchen.chain.gnosis.modules.giveth.constants import GNOSIS_GIVPOWERSTAKING_WRAPPER
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
