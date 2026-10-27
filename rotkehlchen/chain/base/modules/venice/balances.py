import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, ClaimEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.base.modules.venice.constants import (
    CPT_VENICE,
    VENICE_STAKING_CONTRACT,
    VVV_TOKEN_ID,
)
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# initiateUnstake burns sVVV and stores the underlying VVV in cooldownAmount until unstake.
VENICE_STAKING_ABI: Final[ABI] = [{
    'inputs': [{'name': '', 'type': 'address'}],
    'name': 'stakes',
    'outputs': [
        {'name': 'rewardDebt', 'type': 'uint256'},
        {'name': 'cooldownEnd', 'type': 'uint256'},
        {'name': 'cooldownAmount', 'type': 'uint256'},
    ],
    'stateMutability': 'view',
    'type': 'function',
}]


class VeniceBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: BaseInquirer,
            tx_decoder: BaseTransactionDecoder,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_VENICE,
            deposit_event_types=set(),
        )

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        """Count only unclaimed withdrawals; active sVVV is already a wallet balance."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if not addresses:
            return balances

        contract = EvmContract(
            address=VENICE_STAKING_CONTRACT,
            abi=VENICE_STAKING_ABI,
            deployed_block=25430182,
        )
        try:
            results = self.evm_inquirer.multicall(calls=[
                (contract.address, contract.encode(method_name='stakes', arguments=[address]))
                for address in addresses
            ])
        except RemoteError as e:
            log.error('Failed to query Venice pending withdrawals: %s', e)
            return balances

        asset = Asset(VVV_TOKEN_ID)
        price = None
        for address, result in zip(addresses, results, strict=True):
            try:
                _, cooldown_end, raw_amount = contract.decode(
                    result=result,
                    method_name='stakes',
                    arguments=[address],
                )
            except DeserializationError as e:
                log.error('Failed to decode Venice pending withdrawal for %s: %s', address, e)
                continue
            if raw_amount == 0:
                continue

            amount = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            if price is None:
                price = Inquirer.find_main_currency_price(asset)
            balances[address].assets[asset][self.counterparty] += Balance(
                amount=amount,
                value=amount * price,
                awaiting_claim=amount,
                claims=(ClaimEntry(
                    amount=amount,
                    available_at=Timestamp(cooldown_end) if cooldown_end != 0 else None,
                ),),
            )

        return balances
