import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.blur.constants import (
    BLUR_IDENTIFIER,
    BLUR_STAKING_CONTRACT,
    CPT_BLUR,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlurBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BLUR,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of staked blur tokens if deposit events are found."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)

        # fetch deposit events
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        staking_contract = self.evm_inquirer.contracts.contract(BLUR_STAKING_CONTRACT)
        calls_mapping = list(addresses_with_deposits)
        calls: list[tuple[ChecksumEvmAddress, str]] = [
            (
                staking_contract.address,
                staking_contract.encode(method_name='balanceOf', arguments=[user_address]),
            )
            for user_address in addresses_with_deposits
        ]
        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query BLUR balances due to {e!s}')
            return balances

        if len(results) == 0:
            return balances

        blur_price = Inquirer.find_usd_price(asset := Asset(BLUR_IDENTIFIER))
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
            balances[user_address].assets[asset][self.counterparty] += Balance(
                amount=amount,
                usd_value=amount * blur_price,
            )

        return balances
