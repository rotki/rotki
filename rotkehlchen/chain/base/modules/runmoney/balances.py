import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.runmoney.constants import (
    CPT_RUNMONEY,
    RUNMONEY_CONTRACT_ABI,
    RUNMONEY_CONTRACT_ADDRESS,
)
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RunmoneyBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            tx_decoder: 'BaseTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_RUNMONEY,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.runmoney_contract = EvmContract(
            address=RUNMONEY_CONTRACT_ADDRESS,
            abi=RUNMONEY_CONTRACT_ABI,
            deployed_block=21942754,
        )
        self.usdc_asset = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        try:
            results = self.evm_inquirer.multicall(
                require_success=False,
                calls=[
                    (self.runmoney_contract.address, self.runmoney_contract.encode('athletes', arguments=[address]))  # noqa: E501
                    for address in addresses_with_deposits
                ],
            )
        except RemoteError as e:
            log.error(f'Failed to query runmoney balances for addresses {addresses_with_deposits}: {e!s}')  # noqa: E501
            return balances

        for idx, result in enumerate(results):
            _, staked_amount_raw, _ = self.runmoney_contract.decode(
                result=result,
                method_name='athletes',
                arguments=[address := addresses_with_deposits[idx]],
            )
            if staked_amount_raw == 0:
                continue

            staked_amount = token_normalized_value_decimals(
                token_amount=staked_amount_raw,
                token_decimals=6,  # usdc decimals is 6
            )
            price = Inquirer().find_usd_price(self.usdc_asset)
            balances[address].assets[self.usdc_asset][self.counterparty] += Balance(
                amount=staked_amount,
                usd_value=staked_amount * price,
            )

        return balances
