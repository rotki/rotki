import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GearboxCommonBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            staking_contract: 'ChecksumEvmAddress',
            gear_token: Asset,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_GEARBOX,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.gear_token = gear_token
        self.staking_contract = staking_contract

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of staked gear tokens if deposit events are found."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_deposits(products=[EvmProduct.STAKING]))) == 0:  # noqa: E501
            return balances

        staking_contract = EvmContract(
            address=self.staking_contract,
            abi=self.evm_inquirer.contracts.abi('GEARBOX_STAKING'),
            deployed_block=0,  # is not used here
        )
        calls_mapping = list(addresses_with_deposits)
        calls = [
            (
                staking_contract.address,
                staking_contract.encode(method_name='balanceOf', arguments=[user_address]),
            )
            for user_address in addresses_with_deposits
        ]
        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query {self.evm_inquirer.chain_name} Gearbox balances due to {e!s}')  # noqa: E501
            return balances

        if len(results) == 0:
            return balances

        gear_price = Inquirer.find_usd_price(self.gear_token)
        for idx, result in enumerate(results):
            staked_amount_raw = staking_contract.decode(
                result=result,
                method_name='balanceOf',
                arguments=[user_address := calls_mapping[idx]],
            )
            amount = token_normalized_value_decimals(
                token_amount=staked_amount_raw[0],
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            balances[user_address].assets[self.gear_token][self.counterparty] += Balance(
                amount=amount,
                usd_value=amount * gear_price,
            )

        return balances
