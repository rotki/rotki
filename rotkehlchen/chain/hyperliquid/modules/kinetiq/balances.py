import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

from .constants import CPT_KINETIQ, KINETIQ_EARN_QUEUE, KINETIQ_STAKING_MANAGER

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
GET_REQUEST_IDS_ABI: Final[ABI] = [{
    'inputs': [],
    'name': 'getRequestIds',
    'outputs': [{'name': '', 'type': 'bytes32[]'}],
    'stateMutability': 'view',
    'type': 'function',
}]


class KinetiqBalances(ProtocolWithBalance):
    """Query the value of Kinetiq withdrawal requests that are queued but not yet
    executed. This covers both the staking manager queues (queued HYPE unstakes) and
    the Kinetiq Earn vault's on-chain withdraw queue (queued vkHYPE withdrawals). The
    LST/shares for these have already left the user's wallet, so without this the
    value in transit would be invisible until the withdrawal is executed."""

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

    def _query_staking_withdrawals(
            self,
            staking_requests: list[tuple['ChecksumEvmAddress', 'ChecksumEvmAddress', int]],
    ) -> list[tuple['ChecksumEvmAddress', Asset, FVal]]:
        """Query the HYPE amounts of the given still-queued staking manager withdrawals"""
        staking_manager = EvmContract(  # only used for encoding/decoding. The call targets are the events' staking managers.  # noqa: E501
            address=KINETIQ_STAKING_MANAGER,
            abi=WITHDRAWAL_REQUESTS_ABI,
            deployed_block=0,
        )
        try:
            results = self.evm_inquirer.multicall(calls=[(
                manager_address,
                staking_manager.encode(
                    method_name='withdrawalRequests',
                    arguments=[user_address, withdrawal_id],
                ),
            ) for user_address, manager_address, withdrawal_id in staking_requests])
        except RemoteError as e:
            log.error('Failed to query Kinetiq withdrawal requests', error=str(e))
            return []

        amounts = []
        for (user_address, _, withdrawal_id), result in zip(staking_requests, results, strict=True):  # noqa: E501
            withdrawal_request = staking_manager.decode(
                result=result,
                method_name='withdrawalRequests',
                arguments=[user_address, withdrawal_id],
            )
            if (hype_amount_raw := withdrawal_request[0][0]) == 0:
                continue  # the withdrawal request has already been confirmed

            amounts.append((user_address, A_HYPE, from_wei(FVal(hype_amount_raw))))

        return amounts

    def _query_earn_withdrawals(
            self,
            earn_requests: list[tuple['ChecksumEvmAddress', str, str, str]],
    ) -> list[tuple['ChecksumEvmAddress', Asset, FVal]]:
        """Filter the given Kinetiq Earn withdrawal requests to the ones still pending
        in the on-chain withdraw queue and return their asset amounts."""
        try:
            pending_ids = {'0x' + request_id.hex() for request_id in EvmContract(
                address=KINETIQ_EARN_QUEUE,
                abi=GET_REQUEST_IDS_ABI,
                deployed_block=0,
            ).call(node_inquirer=self.evm_inquirer, method_name='getRequestIds')}
        except RemoteError as e:
            log.error('Failed to query Kinetiq Earn withdrawal request ids', error=str(e))
            return []

        return [
            (user_address, Asset(asset_identifier), FVal(amount))
            for user_address, request_id, asset_identifier, amount in earn_requests
            if request_id in pending_ids
        ]

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        staking_requests, earn_requests = [], []
        for user_address, events in self.addresses_with_deposits().items():
            for event in events:
                if event.extra_data is None or event.address is None:
                    continue  # instant unstakes share the type/subtype combo but have no extra data  # noqa: E501

                if (withdrawal_id := event.extra_data.get('withdrawal_id')) is not None:
                    staking_requests.append((user_address, event.address, withdrawal_id))
                elif (
                        (request_id := event.extra_data.get('request_id')) is not None and
                        (asset_out := event.extra_data.get('asset_out')) is not None and
                        (amount_of_assets := event.extra_data.get('amount_of_assets')) is not None
                ):
                    earn_requests.append((user_address, request_id, asset_out, amount_of_assets))

        amounts = []
        if len(staking_requests) != 0:
            amounts.extend(self._query_staking_withdrawals(staking_requests))
        if len(earn_requests) != 0:
            amounts.extend(self._query_earn_withdrawals(earn_requests))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
