import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.chain.evm.decoding.flying_tulip.ftusd.constants import (
    FLYING_TULIP_FTUSD_DEPLOYMENTS,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash

A_FTUSD = Asset('eip155:1/erc20:0xF7D85EC4E7710f71992752eac2111312e73E9C9C')
A_SFTUSD = Asset('eip155:1/erc20:0xeb48218a4c35C814C7678cBcae88C6Ee037F7625')
A_FT = Asset('eip155:1/erc20:0x5DD1A7A369e8273371d2DBf9d83356057088082c')
A_ETH_USDT = Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7')
A_ETH_USDC = Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
DEPLOYMENT = FLYING_TULIP_FTUSD_DEPLOYMENTS[ChainID.ETHEREUM]


@pytest.mark.parametrize('ethereum_accounts', [['0x3c9094Fc254371998fE115a6AA38be9955b2f694']])
def test_ftusd_mint(ethereum_inquirer, ethereum_accounts):
    """Mint is relayer-submitted, so the user pays no gas in this transaction."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x247ae3bca7dcb6c4d5d295135f32a976aff124089e9f1554980ac7a69fbcd740')),  # noqa: E501
    )
    assert events == [
        EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782585407000)),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH_USDT,
            amount=FVal(out_amount := '106.004476'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Swap {out_amount} USDT in Flying Tulip',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.mint_and_redeem,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_FTUSD,
            amount=FVal(in_amount := '105.556274'),
            location_label=user_address,
            notes=f'Receive {in_amount} ftUSD as the result of a swap in Flying Tulip',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.mint_and_redeem,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x3c9094Fc254371998fE115a6AA38be9955b2f694']])
def test_ftusd_redeem(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x28b438630c1c4be29208af5b1bcf8627916d309a7f9e2a45d42c13411b4d734c')),  # noqa: E501
    )
    assert events == [
        EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783094447000)),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_FTUSD,
            amount=FVal(out_amount := '105.152836'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Swap {out_amount} ftUSD in Flying Tulip',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.mint_and_redeem,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH_USDC,
            amount=FVal(in_amount := '104.628923'),
            location_label=user_address,
            notes=f'Receive {in_amount} USDC as the result of a swap in Flying Tulip',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.mint_and_redeem,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x3c9094Fc254371998fE115a6AA38be9955b2f694']])
def test_sftusd_stake(ethereum_inquirer, ethereum_accounts):
    """The relayer fee is carved out of the user's gross transfer into the vault."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xda81303cc65040a0fbd75b97cae82f61d068d32d61e52f0e836f664d9858cfcd')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=156,
            timestamp=(timestamp := TimestampMS(1782585431000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_FTUSD,
            amount=FVal(fee_amount := '0.101158'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Spend {fee_amount} ftUSD as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=157,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_FTUSD,
            amount=FVal(amount := '105.455116'),
            location_label=user_address,
            notes=f'Deposit {amount} ftUSD in the Flying Tulip sftUSD vault',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=158,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_SFTUSD,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Receive {amount} sftUSD from depositing in the Flying Tulip sftUSD vault',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x3c9094Fc254371998fE115a6AA38be9955b2f694']])
def test_sftusd_unstake(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x26ca866cc3313a7c1ea250dfef154f634bc0b341e9ba4ac47821cf4f8b097e39')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783094399000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_SFTUSD,
            amount=FVal(shares_amount := '105.455116'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Return {shares_amount} sftUSD to the Flying Tulip sftUSD vault',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_FTUSD,
            amount=FVal(assets_amount := '105.455116'),  # 105.152836 received plus the relayer fee
            location_label=user_address,
            notes=f'Withdraw {assets_amount} ftUSD from the Flying Tulip sftUSD vault',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_FTUSD,
            amount=FVal(fee_amount := '0.30228'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ftUSD as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x966bD381BbA921B6728C5548F0BCD01CE3381974']])
def test_sftusd_claim_rewards(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe458f8a6b981007009eff7bc466692a0c8e64fa0f9423a5d4a3908193f745e3c')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=314,
            timestamp=(timestamp := TimestampMS(1786644743000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_FT,
            amount=FVal(reward_amount := '89.319855370556996261'),  # 89.230209… received plus the relayer fee  # noqa: E501
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Claim {reward_amount} FT from Flying Tulip ftUSD staking',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=317,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_FT,
            amount=FVal(fee_amount := '0.089646000000000003'),
            location_label=user_address,
            notes=f'Spend {fee_amount} FT as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.staking_vault,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x3FfEBdC5130f6072A582f79f3FB61581D3D846ee']])
def test_sftusd_unstake_queued(ethereum_inquirer, ethereum_accounts):
    """A rate-limited unstake: the shares burn now while the circuit breaker
    queues the ftUSD payout for a later transaction."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x52b1c85f91e1247bc6af0cc1e17b129ec5fc0aa1d6b62e2ee825c1c852d96d99')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1781743715000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000264618530553404'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=133,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_SFTUSD,
            amount=FVal(shares_amount := '200000'),
            location_label=user_address,
            notes=f'Return {shares_amount} sftUSD to the Flying Tulip sftUSD vault with the payout of 200000 ftUSD queued by the circuit breaker',  # noqa: E501
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x3FfEBdC5130f6072A582f79f3FB61581D3D846ee']])
def test_circuit_breaker_release_unstake(ethereum_inquirer, ethereum_accounts):
    """The later transaction paying out the queued unstake from the circuit breaker."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x53369bc39fc906041640e4d62e2e2310ed1a6789534af7f59737b116068c035f')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1781778467000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000069128536608282'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=421,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_FTUSD,
            amount=FVal(amount := '200000'),
            location_label=user_address,
            notes=f'Receive {amount} ftUSD released from the Flying Tulip circuit breaker queue',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.circuit_breaker,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x072ab8B22c7C7b4DD2b3367C6E7445d6c9e3cB2F']])
def test_ftusd_redeem_queued(ethereum_inquirer, ethereum_accounts):
    """A rate-limited redemption: the ftUSD is spent now while the circuit
    breaker queues the collateral payout for a later transaction."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xa58bad57aeec3377b47fc47b474386d3afc17d73be7b8ef232d3c26aa06b9296')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1773803615000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000069450523131154'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=675,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_FTUSD,
            amount=FVal(amount := '25030.217528'),
            location_label=user_address,
            notes=f'Swap {amount} ftUSD in Flying Tulip for 24999.429441 USDT queued by the circuit breaker',  # noqa: E501
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.mint_and_redeem,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x072ab8B22c7C7b4DD2b3367C6E7445d6c9e3cB2F']])
def test_circuit_breaker_release_redeem(ethereum_inquirer, ethereum_accounts):
    """The later transaction paying out the queued redemption collateral."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xaed560582dca59c7453340c7f92af729e8af989cfcf24c076dcf04ac0282a083')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1773825263000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.00001493588304054'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=449,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH_USDT,
            amount=FVal(amount := '24999.429441'),
            location_label=user_address,
            notes=f'Receive {amount} USDT released from the Flying Tulip circuit breaker queue',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.circuit_breaker,
        ),
    ]
