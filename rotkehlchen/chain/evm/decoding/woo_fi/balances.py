import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import asset_normalized_value, token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.woo_fi.constants import (
    CPT_WOO_FI,
    CPT_WOO_FI_LABEL,
    WOO_REWARD_MASTER_CHEF,
    WOO_REWARD_MASTER_CHEF_ABI,
    WOO_STAKE_V2_ABI,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WoofiBalances(ProtocolWithBalance):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_WOO_FI,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query WOO and vault token staked balances."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(address_to_deposits := self.addresses_with_deposits()) == 0:
            return balances

        addresses_with_staked_woo_tokens = set()
        addresses_with_staked_vault_tokens = defaultdict(set)
        woo_staking_event = None
        for address, events in address_to_deposits.items():
            for event in events:
                if event.event_type == HistoryEventType.STAKING:
                    if (
                        event.extra_data is not None and
                        (pool_id := event.extra_data.get('woo_fi_pool_id')) is not None
                    ):
                        addresses_with_staked_vault_tokens[address].add((pool_id, event.asset))
                    else:
                        addresses_with_staked_woo_tokens.add(address)
                        if woo_staking_event is None:
                            woo_staking_event = event

        if len(addresses_with_staked_woo_tokens) > 0 and woo_staking_event is not None:
            # Get the woo token and stake_v2 address for this chain from one of the deposit events
            woo_token = woo_staking_event.asset
            if (stake_v2_address := woo_staking_event.address) is None:
                # Handle a missing address on the event. In theory this should never happen since
                # the address is part of what is checked in the decoder for these deposit events.
                log.error(
                    f'Failed to query {CPT_WOO_FI_LABEL} v2 staking balances '
                    f'due to missing address on the staking deposit event',
                )
                return balances

            balances = self._query_staked_woo_balances(
                balances=balances,
                addresses=list(address_to_deposits),
                woo_token=woo_token,
                stake_v2_address=stake_v2_address,
            )

        if len(addresses_with_staked_vault_tokens) > 0:
            balances = self._query_staked_vault_token_balances(
                balances=balances,
                addresses_with_staked_vault_tokens=addresses_with_staked_vault_tokens,
            )

        return balances

    def _query_staked_woo_balances(
            self,
            balances: BalancesSheetType,
            addresses: list['ChecksumEvmAddress'],
            woo_token: 'Asset',
            stake_v2_address: 'ChecksumEvmAddress',
    ) -> BalancesSheetType:
        """Query balances of WOO staked in the v2 staking contract.
        Note that v1 uses a wrapped xWOO token so we don't need special balances logic for that.
        """
        staking_contract = EvmContract(
            address=stake_v2_address,
            abi=WOO_STAKE_V2_ABI,
            deployed_block=0,  # is not used here
        )
        try:
            if not (results := self.evm_inquirer.multicall(calls=[
                (
                    staking_contract.address,
                    staking_contract.encode(method_name='balances', arguments=[user_address]),
                ) for user_address in addresses
            ])):
                log.error(
                    f'Empty response from {CPT_WOO_FI_LABEL} v2 staking contract '
                    f'{stake_v2_address} on {self.evm_inquirer.chain_name}',
                )
                return balances
        except RemoteError as e:
            log.error(
                f'Failed to query {CPT_WOO_FI_LABEL} v2 staking balances on '
                f'{self.evm_inquirer.chain_name} due to {e!s}',
            )
            return balances

        woo_price = Inquirer.find_main_currency_price(woo_token)
        for address, result in zip(addresses, results, strict=False):
            if (raw_balance := staking_contract.decode(
                result=result,
                method_name='balances',
                arguments=[address],
            )[0]) == 0:
                continue

            balances[address].assets[woo_token][self.counterparty] += Balance(
                amount=(balance := token_normalized_value_decimals(
                    token_amount=raw_balance,
                    token_decimals=DEFAULT_TOKEN_DECIMALS,  # WOO has 18 decimals
                )),
                value=balance * woo_price,
            )

        return balances

    def _query_staked_vault_token_balances(
            self,
            balances: BalancesSheetType,
            addresses_with_staked_vault_tokens: defaultdict['ChecksumEvmAddress', set[tuple[int, 'Asset']]],  # noqa: E501
    ) -> BalancesSheetType:
        """Query balances of vault tokens staked in the reward master chef contract."""
        master_chef_contract = EvmContract(
            address=WOO_REWARD_MASTER_CHEF,
            abi=WOO_REWARD_MASTER_CHEF_ABI,
            deployed_block=0,  # is not used here
        )
        for address, pool_info in addresses_with_staked_vault_tokens.items():
            pool_info_list = list(pool_info)
            try:
                if not (results := self.evm_inquirer.multicall(calls=[
                    (master_chef_contract.address, master_chef_contract.encode(
                        method_name='userInfo',
                        arguments=[pool_id, address],
                    )) for pool_id, _ in pool_info_list
                ])):
                    log.error(
                        f'Empty response from {CPT_WOO_FI_LABEL} v2 reward master chef contract '
                        f'{WOO_REWARD_MASTER_CHEF} on {self.evm_inquirer.chain_name}',
                    )
                    return balances
            except RemoteError as e:
                log.error(
                    f'Failed to query {CPT_WOO_FI_LABEL} v2 staked vault token balances on '
                    f'{self.evm_inquirer.chain_name} due to {e!s}',
                )
                return balances

            for (pool_id, vault_token), result in zip(pool_info_list, results, strict=False):
                raw_balance, _ = master_chef_contract.decode(
                    result=result,
                    method_name='userInfo',
                    arguments=[pool_id, address],
                )
                if raw_balance == 0:
                    continue

                balances[address].assets[vault_token][self.counterparty] += Balance(
                    amount=(balance := asset_normalized_value(
                        amount=raw_balance,
                        asset=vault_token.resolve_to_crypto_asset(),
                    )),
                    value=balance * Inquirer.find_main_currency_price(vault_token),
                )

        return balances
