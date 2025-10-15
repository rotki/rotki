import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, Literal

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_GIVETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEPOSIT_BALANCE_ABI: Final[ABI] = [{'inputs': [{'name': '', 'type': 'address'}], 'name': 'depositTokenBalance', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa:E501


class GivethCommonBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            staking_address: 'ChecksumEvmAddress',
            query_method: Literal['balanceOf', 'depositTokenBalance'],
            giv_token_id: 'str',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_GIVETH,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)},  # noqa: E501
        )
        self.staking_address = staking_address
        self.giv_token_id = giv_token_id
        self.query_method = query_method

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of staked/locked GIV"""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        address_to_deposits = self.addresses_with_deposits()
        staking_contract = EvmContract(
            address=self.staking_address,
            abi=DEPOSIT_BALANCE_ABI if self.query_method == 'depositTokenBalance' else self.evm_inquirer.contracts.abi('ERC20_TOKEN'),  # noqa: E501
            deployed_block=0,  # not used here
        )
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        arguments: list[ChecksumEvmAddress] = []
        for address in address_to_deposits:
            calls.append((
                self.staking_address,
                staking_contract.encode(
                    method_name=self.query_method,
                    arguments=[address],
                ),
            ))
            arguments.append(address)

        try:
            call_output = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query Giveth {self.evm_inquirer.chain_name} balances due to {e!s}')  # noqa: E501
            return balances

        giv_asset = Asset(self.giv_token_id)
        if (asset_price := Inquirer.find_usd_price(giv_asset)) == ZERO:
            log.error(
                f'Failed to query price of GIV while querying '
                f'{self.evm_inquirer.chain_name} staked GIV',
            )
            return balances

        for idx, result in enumerate(call_output):
            raw_amount = staking_contract.decode(
                result=result,
                method_name=self.query_method,
                arguments=[arguments[idx]],
            )[0]
            if raw_amount <= 0:
                continue

            amount = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=DEFAULT_TOKEN_DECIMALS,  # GIV has 18 decimals
            )
            balances[arguments[idx]].assets[giv_asset][self.counterparty] += Balance(
                amount=amount,
                usd_value=amount * asset_price,
            )

        return balances
