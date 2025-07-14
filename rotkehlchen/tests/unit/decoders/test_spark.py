import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_XDAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import EvmTokenKind, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x19e4057A38a730be37c4DA690b103267AAE1d75d']])
def test_deposit_usdc_into_savings(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc63747c31bc5ac9d62e9217a44681463724bd36c74ea2b6ffe90cbeafbcf91a8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = base_accounts[0], TimestampMS(1736935243000), '0.000003809323980083', '18.364226', '17.867188'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=327,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Deposit {out_amount} USDC in Spark Savings',
            address=string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E'),
            counterparty=CPT_SPARK,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=328,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x5875eEE11Cf8398102FdAd704C9E96607675467a'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} sUSDS from depositing into Spark Savings',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x19e4057A38a730be37c4DA690b103267AAE1d75d']])
def test_withdraw_usdc_from_savings(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x46d434c03ff6721fff43cbc1b1570ee3739dbd32f84d4531c5ca0a556a0dc433')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = base_accounts[0], TimestampMS(1736937043000), '0.000003506413757861', '16.539774682836928356', '17'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=283,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x5875eEE11Cf8398102FdAd704C9E96607675467a'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Return {out_amount} sUSDS into Spark Savings',
            address=string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E'),
            counterparty=CPT_SPARK,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=284,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x820C137fa70C8691f0e44Dc420a5e53c168921Dc'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Remove {in_amount} USDS from Spark Savings',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x81EBde24453B8E40454616579EA79C79A197699D']])
def test_deposit_to_spark(ethereum_inquirer, ethereum_accounts):
    get_or_create_evm_token(
        evm_inquirer=ethereum_inquirer,
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0x6715bc100A183cc65502F05845b589c1919ca3d3'),
        chain_id=ethereum_inquirer.chain_id,
        protocol=CPT_SPARK,
        token_kind=EvmTokenKind.ERC20,
    )
    tx_hash = deserialize_evm_tx_hash('0xe7ae42aa6b3815b135c5dfe62222421e43013d30ec132f18d52b396229ce5c6a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1737005627000), '0.000511374451566069', '5839855.131490784645058218', '5839855.131490784645058218'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=413,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
            amount=ZERO,
            location_label=user_address,
            notes='Enable sUSDS as collateral on Spark',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xC13e21B648A5Ee794902342038FF3aDAB66BE987'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=414,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Deposit {out_amount} sUSDS into Spark',
            address=string_to_evm_address('0x6715bc100A183cc65502F05845b589c1919ca3d3'),
            counterparty=CPT_SPARK,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=415,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x6715bc100A183cc65502F05845b589c1919ca3d3'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} spsUSDS from Spark',
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x9a921f8edEC50423831aE33c1062113DBB80061f']])
def test_withdraw_from_spark(gnosis_inquirer, gnosis_accounts):
    get_or_create_evm_token(
        evm_inquirer=gnosis_inquirer,
        userdb=gnosis_inquirer.database,
        evm_address=string_to_evm_address('0x629D562E92fED431122e865Cc650Bc6bdE6B96b0'),
        chain_id=gnosis_inquirer.chain_id,
        protocol=CPT_SPARK,
        token_kind=EvmTokenKind.ERC20,
    )
    tx_hash = deserialize_evm_tx_hash('0x783c3199d405cbf9a9f95ac31e6aeeb0c092d405d4abd56ec2cd3c62b760b3e8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount, interest_amount = gnosis_accounts[0], TimestampMS(1737008645000), '0.0002680834', '0.73523915024913116', '0.73523915024913116', '0.002274206849231879'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),
            amount=ZERO,
            location_label=user_address,
            notes='Disable WETH as collateral on Spark',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x2Dae5307c5E3FD1CF5A72Cb6F698f915860607e0'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0x629D562E92fED431122e865Cc650Bc6bdE6B96b0'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Return {out_amount} spWETH to Spark',
            address=ZERO_ADDRESS,
            counterparty=CPT_SPARK,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Withdraw {in_amount} WETH from Spark',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x629D562E92fED431122e865Cc650Bc6bdE6B96b0'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=Asset('eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),
            amount=FVal(interest_amount),
            location_label=user_address,
            notes=f'Receive {interest_amount} WETH as interest earned from Spark',
            counterparty=CPT_SPARK,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2e2aB1C1383c7Be56ffb8c9039E2d85681C936FD']])
def test_susdc_ethereum_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf6cbd0040b8ba30e9eea85358c1d99e2e7105aac919e2f5964786129d508f6f9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, deposited_amount, received_amount = ethereum_accounts[0], TimestampMS(1752351551000), '0.000783837589583992', '1010', '953.822804925212844028'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(deposited_amount),
            location_label=user_address,
            notes=f'Deposit {deposited_amount} USDC in Spark Savings',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE'),
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Receive {received_amount} sUSDC from depositing into Spark Savings',
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2154B08eb8E5f9980094Af08E9A3C1d99a4FE2d2']])
def test_susdc_ethereum_redeem(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2e5773d502170ff3040181fe70fd482f15c31204dda48e428e191e73dc828e44')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, returned_amount, withdrawn_amount = ethereum_accounts[0], TimestampMS(1752577619000), '0.000926886160514529', '47613.475754046774802545', '50433.672545'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE'),
            amount=FVal(returned_amount),
            location_label=user_address,
            notes=f'Return {returned_amount} sUSDC to Spark Savings',
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(withdrawn_amount),
            location_label=user_address,
            notes=f'Remove {withdrawn_amount} USDC from Spark Savings',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xaE6396d2fB733e124f9b1C3BF922cF17fE1CC75A']])
def test_redeem_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2e5bac2cb234a4388d45754656bad35cc03c7dde7745de10b5b605ff28187d52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726736615000)
    gas_amount, returned_amount, withdrawn_amount = '0.002553705360907168', '76400.28490997120343213', '76424.11'  # noqa: E501
    assert events == [EvmEvent(
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
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
        amount=FVal(returned_amount),
        location_label=ethereum_accounts[0],
        notes=f'Return {returned_amount} sUSDS to Spark Savings',
        counterparty=CPT_SPARK,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:1/erc20:0xdC035D45d973E3EC169d2276DDab16f1e407384F'),
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Remove {withdrawn_amount} USDS from Spark Savings',
        counterparty=CPT_SPARK,
        address=string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2618d8078253b4765fd4ea56b3840c212830E9a3']])
def test_deposit_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe9ca86a0ce9c0226d65203805b77d13697ad5e579989505562638095dc45cac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726754135000)
    gas_amount, deposited_amount, withdrawn_amount = '0.003750084090503928', '5114.68', '5112.913299374006156278'  # noqa: E501
    assert events == [EvmEvent(
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
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0xdC035D45d973E3EC169d2276DDab16f1e407384F'),
        amount=FVal(deposited_amount),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposited_amount} USDS in Spark Savings',
        counterparty=CPT_SPARK,
        address=string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {withdrawn_amount} sUSDS from depositing into Spark Savings',
        counterparty=CPT_SPARK,
        address=ZERO_ADDRESS,
    )]
