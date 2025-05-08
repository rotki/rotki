import pytest

from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    CONSOLIDATION_REQUEST_CONTRACT,
    CPT_ETH2,
    WITHDRAWAL_REQUEST_CONTRACT,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthDepositEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Eth2PubKey, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc66962Ff943449C90b457856D448Aa19D60CB033']])
def test_deposit(database, ethereum_inquirer, ethereum_accounts):
    """Test a simple beacon chain deposit contract"""
    dbeth2 = DBEth2(database)
    validator = ValidatorDetails(validator_index=507258, public_key=Eth2PubKey('0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda'))  # noqa: E501
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(  # add validator in DB so decoder can map pubkey -> index
            write_cursor,
            validators=[validator],
        )

    evmhash = deserialize_evm_tx_hash('0xb3658f940cab23f95273bb7c199eec5c71424a8bf2f111201f5cc2a1491d3471')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674558203000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000788637337054068'),
            location_label=user_address,
            notes='Burn 0.000788637337054068 ETH for gas',
            counterparty=CPT_GAS,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=validator.validator_index,
            sequence_index=178,
            timestamp=TimestampMS(1674558203000),
            amount=FVal('32'),
            depositor=user_address,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x3e5fd0244e13d82fC230f3Fc610bcd76b3c8217C']])
def test_multiple_deposits(database, ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x819fe4a07894cf044f5d8c63e5c1e2294e068d05bf91d9cfc3e7ae3e60528ae5')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    dbeth2 = DBEth2(database)
    validators = [
        ValidatorDetails(
            validator_index=55750,
            public_key=Eth2PubKey('0x91108c07526641ad22e91b1038c640b9efce236e9aa8c1c355676a6862e4c082454ceaa599b305ceca9c15984fdbf1a8'),
        ), ValidatorDetails(
            validator_index=55751,
            public_key=Eth2PubKey('0x8e31e6d9771094182a70b75882f7d186986d726f7b4da95f542d18a1cb7fa38cd31b450a9fc62867d81dfc9ad9cbd641'),
        ), ValidatorDetails(
            validator_index=55752,
            public_key=Eth2PubKey('0xa01b86a30e5e349dccc04aee560502dd49ba87342c22ea88e462ab2c843c92eed08407150a8eaa849dc9de909c59679a'),
        ),
    ]
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(  # add validator in DB so decoder can map pubkey -> index
            write_cursor,
            validators=validators,
        )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1608594280000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.010956672'),
            location_label=user_address,
            notes='Burn 0.010956672 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55750,
            sequence_index=62,
            timestamp=TimestampMS(1608594280000),
            amount=FVal('32'),
            depositor=user_address,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55751,
            sequence_index=63,
            timestamp=TimestampMS(1608594280000),
            amount=FVal('32'),
            depositor=user_address,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55752,
            sequence_index=64,
            timestamp=TimestampMS(1608594280000),
            amount=FVal('32'),
            depositor=user_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397', '0xFbcE5F52fc21296AE42EE000dFdFdC7FecAaA2fD']])  # noqa: E501
def test_deposit_with_anonymous_event(database, ethereum_inquirer, ethereum_accounts):
    """As seen here: https://twitter.com/LefterisJP/status/1671515625397669889

    This is a beaconchain deposit via a proxy contract (who is also the depositor).
    The test was written since in 1.28 decoding broke badly due to the existence of
    an anonymous Ping() event in the same transaction.
    """
    dbeth2 = DBEth2(database)
    validator = ValidatorDetails(validator_index=482198, public_key=Eth2PubKey('0xaa9c8a2653f08b3045fdb63547bfe1ad2a66225f7402717bde9897cc163840ee190ed31c78819db372253332bba3c570'))  # noqa: E501
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(  # add validator in DB so decoder can map pubkey -> index
            write_cursor,
            validators=[validator],
        )
    evmhash = deserialize_evm_tx_hash('0xd455d892453de3c5b06a00ebedc1994b8d66eeba69e6b08bd20508281e690e80')  # noqa: E501
    user_address = ethereum_accounts[0]
    proxy_address = ethereum_accounts[1]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    timestamp = TimestampMS(1669806275000)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00071529566834925'),
            location_label=user_address,
            notes='Burn 0.00071529566834925 ETH for gas',
            counterparty=CPT_GAS,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=validator.validator_index,
            sequence_index=431,
            timestamp=timestamp,
            amount=FVal('32'),
            depositor=proxy_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5907fc323d165680fb8141681958A2FdBFA0907e']])
def test_convert_to_accumulating_request(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcc80041642ebd2f62a9d939321a1927f52d2bcb984355accefadcb20f9641d28')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746618551000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000312710325833682')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Request to convert validator 187176 into an accumulating validator',
        counterparty=CPT_ETH2,
        address=CONSOLIDATION_REQUEST_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(fee_amount := FVal('0.000000000000000001')),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as validator consolidation fee',
        counterparty=CPT_ETH2,
        address=CONSOLIDATION_REQUEST_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xcECA24BE4585ADadC8f0D95285F65ac44533094C']])
def test_consolidation_request(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x812eeeb8a786650afa1826d8e9d46aa2073e28f1ed261f0c3da4ea18b7d7cd82')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746620507000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.00041335788646901')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Request to consolidate validator 67953 into 1073521',
        counterparty=CPT_ETH2,
        address=CONSOLIDATION_REQUEST_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(fee_amount := FVal('0.000000000000000001')),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as validator consolidation fee',
        counterparty=CPT_ETH2,
        address=CONSOLIDATION_REQUEST_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x86863bC22648d8c2fb02e3fcA314B8ee9ca0A4e0']])
def test_withdraw_request(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5f038d3775fc27e16d8d5770aa1ba6f962e67ff8db0a194551566418542d60dc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746614447000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000936280934217013')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Request to withdraw 0.0001 ETH from validator 68209',
        counterparty=CPT_ETH2,
        address=WITHDRAWAL_REQUEST_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(fee_amount := FVal('0.000000000000000001')),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as withdrawal request fee',
        counterparty=CPT_ETH2,
        address=WITHDRAWAL_REQUEST_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3Fb695A1b8Bc5ea18d8A4811eb514a7E17d80695']])
def test_exit_request(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6224c1cde536d2488e29be74da6ed907bbeb885ecd38edc99820f35d8c0e136c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746707471000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.001827476471561315')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Request to exit validator 1649633',
        counterparty=CPT_ETH2,
        address=WITHDRAWAL_REQUEST_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(fee_amount := FVal('0.000000000000000001')),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as exit request fee',
        counterparty=CPT_ETH2,
        address=WITHDRAWAL_REQUEST_CONTRACT,
    )]
