import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

from .constants import CPT_KINETIQ, KINETIQ_STAKING_MANAGER

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

WITHDRAWAL_REQUESTS_ABI: Final[ABI] = [{
    'inputs': [
        {'name': 'user', 'type': 'address'},
        {'name': 'withdrawalId', 'type': 'uint256'},
    ],
    'name': 'withdrawalRequests',
    'outputs': [{
        'components': [
            {'name': 'hypeAmount', 'type': 'uint256'},
            {'name': 'kHYPEAmount', 'type': 'uint256'},
            {'name': 'kHYPEFee', 'type': 'uint256'},
            {'name': 'timestamp', 'type': 'uint256'},
        ],
        'name': '',
        'type': 'tuple',
    }],
    'stateMutability': 'view',
    'type': 'function',
}]


class KinetiqBalances(ProtocolWithBalance):
    """Query HYPE amounts of Kinetiq withdrawal requests that are queued but not yet
    confirmed. The kHYPE for these has already left the user's wallet, so without this
    the value in transit would be invisible until the withdrawal is confirmed."""

    def __init__(
            self,
            evm_inquirer: 'HyperliquidInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_KINETIQ,
            deposit_event_types={(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        staking_manager = EvmContract(  # only used for encoding/decoding. The call targets are the events' staking managers.  # noqa: E501
            address=KINETIQ_STAKING_MANAGER,
            abi=WITHDRAWAL_REQUESTS_ABI,
            deployed_block=0,
        )
        calls, calls_arguments = [], []
        for user_address, events in self.addresses_with_deposits().items():
            for event in events:
                if (
                        event.address is None or
                        event.extra_data is None or
                        (withdrawal_id := event.extra_data.get('withdrawal_id')) is None
                ):  # instant unstakes share the type/subtype combo but have no withdrawal id
                    continue

                calls.append((
                    event.address,  # the staking manager (kHYPE or a partner deployment)
                    staking_manager.encode(
                        method_name='withdrawalRequests',
                        arguments=(arguments := [user_address, withdrawal_id]),
                    ),
                ))
                calls_arguments.append(arguments)

        if len(calls) == 0:
            return balances

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error('Failed to query Kinetiq withdrawal requests', error=str(e))
            return balances

        amounts: list[tuple[ChecksumEvmAddress, FVal]] = []
        for arguments, result in zip(calls_arguments, results, strict=True):
            withdrawal_request = staking_manager.decode(
                result=result,
                method_name='withdrawalRequests',
                arguments=arguments,
            )
            if (hype_amount_raw := withdrawal_request[0][0]) == 0:
                continue  # the withdrawal request has already been confirmed

            amounts.append((arguments[0], from_wei(FVal(hype_amount_raw))))

        self._add_priced_balances(
            balances=balances,
            amounts=[(address, A_HYPE, amount) for address, amount in amounts],
        )
        return balances
