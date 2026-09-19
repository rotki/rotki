import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import A_AZTEC, AZTEC_STAKING_DATA, AZTEC_TOKEN, CPT_AZTEC, GSE

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

AZTEC_BALANCES_ABI: Final[ABI] = [
    {'inputs': [{'name': '_instance', 'type': 'address'}, {'name': '_attester', 'type': 'address'}], 'name': 'effectiveBalanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': 'account', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
]


class AztecBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_AZTEC,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.aztec_token = A_AZTEC.resolve_to_evm_token()

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits(
            location_labels=addresses,
        )) == 0:
            return balances

        contract = EvmContract(address=GSE, abi=AZTEC_BALANCES_ABI)
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        call_data: list[tuple[
            ChecksumEvmAddress,
            int,
            int,
            ChecksumEvmAddress,
            ChecksumEvmAddress,
            ChecksumEvmAddress,
        ]] = []
        seen_attesters: set[ChecksumEvmAddress] = set()
        for user_address, events in addresses_with_deposits.items():
            for event in events:
                if event.extra_data is None or (data := event.extra_data.get(AZTEC_STAKING_DATA)) is None:  # noqa: E501
                    continue
                try:
                    attester = string_to_evm_address(data['attester'])
                    rollup = string_to_evm_address(data['rollup'])
                    split = string_to_evm_address(data['split'])
                    allocation = int(data['allocation'])
                    total_allocation = int(data['total_allocation'])
                except (DeserializationError, KeyError, TypeError, ValueError) as e:
                    log.error('Failed to read Aztec staking metadata from event %s due to %s', event, e)  # noqa: E501
                    continue
                if attester in seen_attesters:
                    continue

                seen_attesters.add(attester)
                calls.extend((
                    (GSE, contract.encode('effectiveBalanceOf', [rollup, attester])),
                    (AZTEC_TOKEN, contract.encode('balanceOf', [split])),
                ))
                call_data.append((
                    user_address,
                    allocation,
                    total_allocation,
                    rollup,
                    attester,
                    split,
                ))

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error('Failed to query Aztec staking balances due to %s', e)
            return balances

        amounts = []
        for idx, (
                user_address,
                allocation,
                total_allocation,
                rollup,
                attester,
                split,
        ) in enumerate(call_data):
            staked_raw = contract.decode(
                result=results[idx * 2],
                method_name='effectiveBalanceOf',
                arguments=[rollup, attester],
            )[0]
            rewards_raw = contract.decode(
                result=results[idx * 2 + 1],
                method_name='balanceOf',
                arguments=[split],
            )[0]
            amount_raw = staked_raw + rewards_raw * allocation // total_allocation
            if amount_raw != 0:
                amounts.append((
                    user_address,
                    self.aztec_token,
                    token_normalized_value(amount_raw, self.aztec_token),
                ))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
