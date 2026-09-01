from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithGauges
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_CACHE_TYPE_MAPPING,
    BALANCER_VERSION_MAPPING,
    CPT_BEETS_V2,
    CPT_BEETS_V3,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


class BeetsBalances(ProtocolWithGauges):
    """Query Beets (Balancer v2/v3 on Sonic) gauge balances.

    BalanceScanner is not deployed on Sonic, so gauge balances are queried
    via multicall balanceOf calls on each gauge contract instead of the
    usual tokens_balance call on BalanceScanner.
    """

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
            counterparty: Literal['beets-v2', 'beets-v3'],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=counterparty,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            },
            gauge_deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            },
        )
        version = BALANCER_VERSION_MAPPING[counterparty]
        cache_type = BALANCER_CACHE_TYPE_MAPPING[counterparty]
        self.pools, self.gauges = read_balancer_pools_and_gauges_from_cache(
            chain_id=evm_inquirer.chain_id,
            version=version,
            cache_type=cache_type,
        )

    def get_gauge_address(self, event: EvmEvent) -> ChecksumEvmAddress | None:
        """Return the gauge address if the event is a gauge deposit, None for pool joins.

        Both gauge deposits and pool joins produce (DEPOSIT, DEPOSIT_FOR_WRAPPED) events.
        We distinguish them by checking whether the event address is a known gauge.
        """
        if event.address in self.gauges:
            return event.address
        return None

    def _get_staking_contract_balances(
            self,
            address: ChecksumEvmAddress,
            staking_addresses: list[ChecksumEvmAddress],
            tokens: list[EvmToken],
            call_order: Sequence[WeightedNode] | None,
    ) -> dict[EvmToken, FVal]:
        """Query gauge balances via multicall balanceOf calls.

        BalanceScanner is not deployed on Sonic, so we use multicall with
        ERC20 balanceOf on each gauge contract instead.
        """
        erc20_contract = EvmContract(
            address=ZERO_ADDRESS,
            abi=self.evm_inquirer.contracts.erc20_abi,
        )
        calls = [
            (gauge_addr, erc20_contract.encode(method_name='balanceOf', arguments=[address]))
            for gauge_addr in staking_addresses
        ]
        results = self.evm_inquirer.multicall(calls=calls, call_order=call_order)

        balances: dict[EvmToken, FVal] = defaultdict(FVal)
        for token, result in zip(tokens, results, strict=True):
            balance = erc20_contract.decode(
                result=result,
                method_name='balanceOf',
                arguments=[address],
            )[0]
            if balance == 0:
                continue
            balances[token] += token_normalized_value(balance, token)

        return balances


class BeetsV2Balances(BeetsBalances):
    def __init__(self, evm_inquirer: EvmNodeInquirer, tx_decoder: EVMTransactionDecoder) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BEETS_V2,
        )


class BeetsV3Balances(BeetsBalances):
    def __init__(self, evm_inquirer: EvmNodeInquirer, tx_decoder: EVMTransactionDecoder) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BEETS_V3,
        )
