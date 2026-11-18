import logging
from collections import defaultdict
from itertools import islice
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_LINK
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import (
    CHAINLINK_STAKING_ABI,
    COMMUNITY_POOL,
    CPT_CHAINLINK,
    OPERATOR_POOL,
    REWARD_VAULT,
    STAKING_V01,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# (contract, method) calls that query LINK of an address in Chainlink staking
type StakingCalls = tuple[tuple[ChecksumEvmAddress, str], ...]

# the LINK an address has staked and the rewards it can claim in v0.2
STAKING_V02_CALLS: Final[StakingCalls] = (
    (COMMUNITY_POOL, 'getStakerPrincipal'),
    (OPERATOR_POOL, 'getStakerPrincipal'),
    (REWARD_VAULT, 'getReward'),
)
# the LINK and the rewards still in the concluded v0.1, which are only queried for the
# addresses that staked there
STAKING_V01_CALLS: Final[StakingCalls] = (
    (STAKING_V01, 'getStake'),
    (STAKING_V01, 'getBaseReward'),
    (STAKING_V01, 'getDelegationReward'),
)


class ChainlinkBalances(ProtocolWithBalance):
    """Query the LINK staked in Chainlink staking and its claimable rewards.

    Staking gives no token in return, so the staked LINK and the rewards are queried from the
    staking contracts for every address that has staked.
    """

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_CHAINLINK,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        # only encodes and decodes the calls, since all the staking contracts share the ABI
        self.contract = EvmContract(address=COMMUNITY_POOL, abi=CHAINLINK_STAKING_ABI)

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        # v0.2 is queried for every address that has staked, since a stake migrated from v0.1
        # without rewards has no v0.2 deposit event of its own
        address_calls: list[tuple[ChecksumEvmAddress, StakingCalls]] = []
        for address, events in self.addresses_with_deposits(location_labels=addresses).items():
            calls = STAKING_V02_CALLS
            if any(event.address == STAKING_V01 for event in events):
                calls += STAKING_V01_CALLS
            address_calls.append((address, calls))

        if len(address_calls) == 0:
            return balances

        try:
            results = iter(self.evm_inquirer.multicall(calls=[
                (contract_address, self.contract.encode(method_name=method, arguments=[address]))
                for address, calls in address_calls
                for contract_address, method in calls
            ]))
        except RemoteError as e:
            log.error('Failed to query Chainlink staking balances: %s', e)
            return balances

        amounts: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for address, calls in address_calls:
            address_results = list(islice(results, len(calls)))
            try:
                raw_amount = sum(
                    self.contract.decode(result=result, method_name=method, arguments=[address])[0]
                    for (_, method), result in zip(calls, address_results, strict=True)
                )
            except DeserializationError as e:
                log.error('Failed to decode Chainlink staking balances of %s: %s', address, e)
                continue

            if raw_amount != 0:
                amounts.append((address, A_LINK, token_normalized_value_decimals(
                    token_amount=raw_amount,
                    token_decimals=DEFAULT_TOKEN_DECIMALS,
                )))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
