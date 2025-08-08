import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_SDAI, A_WXDAI, A_XDAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, TokenKind, deserialize_evm_tx_hash


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
        token_kind=TokenKind.ERC20,
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
        token_kind=TokenKind.ERC20,
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
            asset=(susdc_token := Asset('eip155:1/erc20:0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE')),  # noqa: E501
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Receive {received_amount} sUSDC from depositing into Spark Savings',
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ),
    ]
    assert susdc_token.resolve_to_evm_token().protocol == CPT_SPARK


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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa217BDa86b0EDb86eE7d4D6e34F493eDF1ea4F29']])
def test_withdraw_dai_from_sdai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6b2a1f836cfc7c28002e4ac60297daa6d79fcde892d9c3b9ca723dea2f21af5c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1695854591000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.001301015216220134'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_SDAI,
            amount=FVal(return_amount := '16.020774067834506624'),
            location_label=user_address,
            notes=f'Return {return_amount} sDAI to Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x83F20F44975D03b1b09e64809B757c47f942BEeA'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal(receive_amount := '16.601085935411927527'),
            location_label=user_address,
            notes=f'Remove {receive_amount} DAI from Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa217BDa86b0EDb86eE7d4D6e34F493eDF1ea4F29']])
def test_deposit_dai_to_sdai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x27bd72a2ccd999a44c2a7aaed9090572f34045d62e153362a34715a70ca7a6a7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1695089927000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.00152049387145495'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal(deposit_amount := '16.58145794'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} DAI in Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x83F20F44975D03b1b09e64809B757c47f942BEeA'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_SDAI,
            amount=FVal(receive_amount := '16.020774067834506624'),
            location_label=user_address,
            notes=f'Receive {receive_amount} sDAI from depositing into Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x83F20F44975D03b1b09e64809B757c47f942BEeA'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x78E87757861185Ec5e8C0EF6BF0C69Fa7832df6C']])
def test_deposit_xdai_to_sdai(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1342646cab122d58f0b7dfae404dad5235d42224de881099dc05e59477bb93aa')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    gas_amount, deposit_amount, receive_amount = '0.000367251244452481', '315', '303.052244055946806232'  # noqa: E501
    assert actual_events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1707169525000)),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=(user_address := gnosis_accounts[0]),
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_XDAI,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} XDAI in Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xD499b51fcFc66bd31248ef4b28d656d67E591A94'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} sDAI from depositing into Spark Savings',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_SPARK,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x4fFAD6ac852c0Af0AA301376F4C5Dea3a928b120']])
def test_withdraw_xdai_from_sdai(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe23ee1ac52b8981723c737b01781691b965c5819cccccdb98e7c8cb5894dddbb')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    gas_amount, received_amount, sent_amount = '0.0003018867380459', '36546.085557613238621948', '35168.419304792460265156'  # noqa: E501
    assert actual_events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1707070975000)),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=(user_address := gnosis_accounts[0]),
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            amount=FVal(sent_amount),
            location_label=user_address,
            notes=f'Return {sent_amount} sDAI to Spark Savings',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_SPARK,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_XDAI,
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Remove {received_amount} XDAI from Spark Savings',
            counterparty=CPT_SPARK,
            tx_hash=tx_hash,
            address=string_to_evm_address('0xD499b51fcFc66bd31248ef4b28d656d67E591A94'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x5938852FE18Ad6963322FB98D1fDDA5c24DD8a0E']])
def test_deposit_wxdai_to_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xd406f40ecd2538d41adb2e645c8fb6d32cec5485510798bfed5d991c258d4b1d')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1706794335000)
    withdraw_amount, deposit_amount, gas_amount = '319.006747127200240848', '331.313258668881367296', '0.0006162151'  # noqa: E501
    assert actual_events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WXDAI,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WXDAI in Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xD499b51fcFc66bd31248ef4b28d656d67E591A94'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Receive {withdraw_amount} sDAI from depositing into Spark Savings',
            tx_hash=tx_hash,
            counterparty=CPT_SPARK,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x23727b54163F63CffdD8B7769e0eCb13Df253b4e']])
def test_withdraw_wxdai_from_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xd7e2123adc6c8f4fd8ced74733010cf47dba2bd4e0e5c468d63d53942b9e2dd3')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1706699405000)
    gas_amount, redeem_amount, received_amount = '0.0002100203', '66725.257159368617313463', '69285.250334740811647229'  # noqa: E501
    assert actual_events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            amount=FVal(redeem_amount),
            location_label=user_address,
            notes=f'Return {redeem_amount} sDAI to Spark Savings',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_SPARK,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WXDAI,
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Remove {received_amount} WXDAI from Spark Savings',
            tx_hash=tx_hash,
            address=string_to_evm_address('0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            counterparty=CPT_SPARK,
        ),
    ]
