import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x6DF95c1F5AdD9cE98a013AD9809782d10272c6b8']])
def test_aura_finance_deposit_arb(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9c3b996891eb0ffb5261486ff77c69c20a332499b9cf4196df7fab2c2123ea5f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_str, deposit_amount, receive_amount, approve_amount = arbitrum_one_accounts[0], TimestampMS(1732504225000), '0.00000372964', '2.862546191448752712', '2.054508357973208982', '115792089237316195423570985008687907853269984665640564039448.345378216051229581'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x223738a747383d6F9f827d95964e4d8E8AC754cE'),
            amount=FVal(approve_amount),
            location_label=user_address,
            address=string_to_evm_address('0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9'),
            notes=f'Set auraBAL spending approval of {user_address} by 0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9 to {approve_amount}',  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x223738a747383d6F9f827d95964e4d8E8AC754cE'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} auraBAL into auraBAL vault',
            address=string_to_evm_address('0x4B5D2848678Db574Fbc2d2f629143d969a4f41Cb'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} stkauraBAL from auraBAL vault',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x4936f33b7B060c7336fD0e4c61316EA248DA6827']])
def test_aura_finance_claim_rewards_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xffbc4716efdb4dbd7671c969599827313166fc507e2564ff1222a317d47e7a70')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, claim_amount_1, claim_amount_2 = base_accounts[0], TimestampMS(1721018721000), '0.000001321340972471', '8.383663297617516524', '6.566591452101315364'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x4158734D47Fc9692176B5085E0F52ee0Da5d47F1'),
            amount=FVal(claim_amount_1),
            location_label=user_address,
            notes=f'Claim {claim_amount_1} BAL from Aura Finance',
            address=string_to_evm_address('0xEe374580BFf150be6b955954aC3b9899D890cB57'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(claim_amount_2),
            location_label=user_address,
            notes=f'Claim {claim_amount_2} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x8b2970c237656d3895588B99a8bFe977D5618201'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x19e4057A38a730be37c4DA690b103267AAE1d75d']])
def test_aura_finance_lock_aura_from_base_to_ethereum(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe0a6fd1bd40451d4b42c520b41a39ab569bf4aae43b741efbe228da40fed91ad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, bridge_fee_amount, locked_amount = base_accounts[0], TimestampMS(1732631175000), '0.000007432156846576', '0.011914017676630994', '90'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(bridge_fee_amount),
            location_label=user_address,
            notes=f'Pay {bridge_fee_amount} ETH as bridge fee (to Ethereum)',
            address=string_to_evm_address('0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=132,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(locked_amount),
            location_label=user_address,
            notes=f'Lock {locked_amount} AURA in Aura Finance (bridged)',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xDbE0c28c273bbB10a632B1aaf65AC2B877bb2b92']])
def test_aura_finance_lock_aura_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x69a2c2e3e7c80f7ca3207041f09bb2799b760b937ba985af65fd69faa7487336')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, approval_amount, locked_amount = ethereum_accounts[0], TimestampMS(1732623719000), '0.002081603016233576', '115792089237316195423570985008687907853269984665640563943628.250490697661436953', '4675.24673564105539589'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
            sequence_index=200,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(locked_amount),
            location_label=user_address,
            notes=f'Lock {locked_amount} AURA in auraLocker (vlAURA)',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=201,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set AURA spending approval of {user_address} by 0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB3af0E54426e48D230c97aE837F34345167BE1C6']])
def test_aura_finance_booster_deposit_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4ed0d517c29bfd7d202efb50e7f98fdf1acc78c7f6977b55b56c354efd8275d2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, approval_amount, deposit_amount, receive_amount = ethereum_accounts[0], TimestampMS(1732603247000), '0.004522784347764904', '3046599999999999952014.290938920480356746', '17520.54161498940427181', '17520.54161498940427181'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
            sequence_index=159,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xfbfaD5fa9E99081da6461F36f229B5cC88A64c63'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set ECLP-GYD-USDT spending approval of {user_address} by 0xA57b8d98dAE62B26Ec3bcC4a365338157060B234 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0xA57b8d98dAE62B26Ec3bcC4a365338157060B234'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=160,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xfbfaD5fa9E99081da6461F36f229B5cC88A64c63'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ECLP-GYD-USDT into an Aura gauge',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xaF52695E1bB01A16D33D7194C28C42b10e0Dbec2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x4313428170c09ca81117a95f0418aefE3446d935'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} auraECLP-GYD-USDT-vault from an Aura gauge',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_aura_finance_claim_rewards_arb(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3ee95df7dfb12a183ef7ccb408e320a6a909561fe8da5408b3897ebd336b5420')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_str, claim_amount_1, claim_amount_2, claim_amount_3 = arbitrum_one_accounts[0], TimestampMS(1735459868000), '0.00000266091', '0.096740702346661316', '0.097900452506457258', '0.14964073351979476'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x040d1EdC9569d4Bab2D15287Dc5A4F10F56a56B8'),
            amount=FVal(claim_amount_1),
            location_label=user_address,
            notes=f'Claim {claim_amount_1} BAL from Aura Finance',
            address=string_to_evm_address('0xAc7025Dec5E216025C76414f6ac1976227c20Ff0'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(claim_amount_2),
            location_label=user_address,
            notes=f'Claim {claim_amount_2} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xeC1c780A275438916E7CEb174D80878f29580606'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(claim_amount_3),
            location_label=user_address,
            notes=f'Claim {claim_amount_3} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xE26200262c84444F7fFf83443B3Cf956Ec680325'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x19e4057A38a730be37c4DA690b103267AAE1d75d']])
def test_aura_finance_get_rewards_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc54f5bc1b45b151dd7e106a45fea82a0bbb0dd1a48b5e71be2d8b9f36fbcb704')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, claim_amount_1, claim_amount_2, claim_amount_3 = base_accounts[0], TimestampMS(1733666205000), '0.000003758872604736', '0.016918933596764049', '0.018407669504926201', '0.018747704109670571'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1063,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x4158734D47Fc9692176B5085E0F52ee0Da5d47F1'),
            amount=FVal(claim_amount_1),
            location_label=user_address,
            notes=f'Claim {claim_amount_1} BAL from Aura Finance',
            address=string_to_evm_address('0x636fCa3ADC5D614E15F5C5a574fFd2CAEE578126'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1064,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(claim_amount_2),
            location_label=user_address,
            notes=f'Claim {claim_amount_2} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x8b2970c237656d3895588B99a8bFe977D5618201'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1066,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(claim_amount_3),
            location_label=user_address,
            notes=f'Claim {claim_amount_3} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xB8d8674a6a7BaA9D2aEE2dfE4b50Da5095Ee1ed4'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbA3C494F3b3937d1C8101ffBe1588023ad5Ea0A2']])
def test_aura_finance_claim_rewards_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xefc4dac1c3cf3b7058ae35427edeb984286ade8097717479294999992c508aee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, claim_amount_1, claim_amount_2, claim_amount_3, claim_amount_4, claim_amount_5, claim_amount_6, claim_amount_7, claim_amount_8 = ethereum_accounts[0], TimestampMS(1735498547000), '0.002203275422715936', '112.627896656336279713', '114.159636050862453116', '77.020600939024296766', '8.274820603749552408', '184.126157708212142242', '186.630273453043827374', '170.528893362154769237', '216.7944203094842023'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
            sequence_index=175,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D'),
            amount=FVal(claim_amount_1),
            location_label=user_address,
            notes=f'Claim {claim_amount_1} BAL from Aura Finance',
            address=string_to_evm_address('0xDd1fE5AD401D4777cE89959b7fa587e569Bf125D'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=176,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(claim_amount_2),
            location_label=user_address,
            notes=f'Claim {claim_amount_2} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=178,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(claim_amount_3),
            location_label=user_address,
            notes=f'Claim {claim_amount_3} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xc6065734B898eEdCf450b28Ec2fC5a45a7DCdb2b'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=180,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xD33526068D116cE69F19A9ee46F0bd304F21A51f'),
            amount=FVal(claim_amount_4),
            location_label=user_address,
            notes=f'Claim {claim_amount_4} RPL from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xcaB7Ee4EFae2D27add6f5EBB64cdef9d74Beba21'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=182,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D'),
            amount=FVal(claim_amount_5),
            location_label=user_address,
            notes=f'Claim {claim_amount_5} BAL from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x2a14dB8D09dB0542f6A371c0cB308A768227D67D'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=183,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(claim_amount_6),
            location_label=user_address,
            notes=f'Claim {claim_amount_6} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=185,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(claim_amount_7),
            location_label=user_address,
            notes=f'Claim {claim_amount_7} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xBA45e6500c49570C3C3e3a83C000e47ae1D4C095'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=187,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            amount=FVal(claim_amount_8),
            location_label=user_address,
            notes=f'Claim {claim_amount_8} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xAc16927429c5c7Af63dD75BC9d8a58c63FfD0147'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x1A02715cf60f0544dEfDB676A3ffeeE710b04115']])
def test_claim_and_withdraw(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfd54629dda6c8a533a0a8019ccdd9dded867cba1bc623d91a75527b571c66ac9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1738262008000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.00000802845'),
            location_label=(user_address := arbitrum_one_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x17F061160A167d4303d5a6D32C2AC693AC87375b'),
            amount=FVal(lp_amount := '7.993230950234068615'),
            location_label=user_address,
            notes=f'Return {lp_amount} aurarETH/wETH BPT-vault to Aura',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xd0EC47c54cA5e20aaAe4616c25C825c7f48D4069'),
            amount=FVal(lp_amount),
            location_label=user_address,
            notes=f'Withdraw {lp_amount} rETH/wETH BPT from an Aura gauge',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x040d1EdC9569d4Bab2D15287Dc5A4F10F56a56B8'),
            amount=FVal(amount := '137.462256109241289895'),
            location_label=user_address,
            notes=f'Claim {amount} BAL from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x17F061160A167d4303d5a6D32C2AC693AC87375b'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(amount := '121.33328055412751574'),
            location_label=user_address,
            notes=f'Claim {amount} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xeC1c780A275438916E7CEb174D80878f29580606'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            amount=FVal(amount := '169.472543006561768123'),
            location_label=user_address,
            notes=f'Claim {amount} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x35fe1130F5934fc04c432989823E8E1fb26d3E2e'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=22,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            amount=FVal(amount := '268.985898008824453673'),
            location_label=user_address,
            notes=f'Claim {amount} ARB from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x5474Bf4a9d823dBb3DB475679d0D611c2e9d9761'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=25,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(amount := '21.084001'),
            location_label=user_address,
            notes=f'Claim {amount} USDC from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xecE4ffB6CBD1d7d3F3130Af9a24069D84376a322'),
        ),
    ]
