import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HopBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_HOP,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Queries and returns the balance sheet for staking events.

        This method:
        1. Retrieves deposit events for staking.
        2. Groups addresses by staking contract.
        3. For each contract, queries user balances and rewards.
        4. Converts balances and rewards to USD and updates the balance sheet.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits()) == 0:
            return balances

        # Group addresses by staking contract
        staked_contracts: dict[ChecksumEvmAddress, set[ChecksumEvmAddress]] = defaultdict(set)
        for user_address, events in addresses_with_deposits.items():
            for event in events:
                if event.address is not None:
                    staked_contracts[event.address].add(user_address)

        hop_abi = self.evm_inquirer.contracts.abi('HOP_STAKING')
        for contract_address, addresses in staked_contracts.items():
            staking_contract = EvmContract(
                address=contract_address,
                abi=hop_abi,
                deployed_block=0,  # not used here since logs are not queried
            )
            chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)

            if len(staked_lps := self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(
                        method_name='balanceOf',
                        arguments=[user],
                    ),
                ) for user in addresses],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )) == 0:
                log.warning(f'No staked balances found for {self.evm_inquirer.chain_name} Hop contract {staking_contract.address}. Skipping')  # noqa: E501
                continue

            token_data = self.evm_inquirer.multicall(
                calls=[
                    (staking_contract.address, staking_contract.encode(method_name='stakingToken')),  # noqa: E501
                    (staking_contract.address, staking_contract.encode(method_name='rewardsToken')),  # noqa: E501
                ],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )
            try:
                checksummed_staking_token, checksummed_rewards_token = deserialize_evm_address(
                    staking_contract.decode(result=token_data[0], method_name='stakingToken')[0],
                ), deserialize_evm_address(
                    staking_contract.decode(result=token_data[1], method_name='rewardsToken')[0],
                )
            except DeserializationError:
                log.error(f'Failed to deserialize staking or rewards token address for {self.evm_inquirer.chain_name} Hop contract {staking_contract.address}. Skipping')  # noqa: E501
                continue

            try:
                staking_token, rewards_token = EvmToken(evm_address_to_identifier(
                    address=checksummed_staking_token,
                    chain_id=self.evm_inquirer.chain_id,
                    token_type=TokenKind.ERC20,
                )), EvmToken(evm_address_to_identifier(
                    address=checksummed_rewards_token,
                    chain_id=self.evm_inquirer.chain_id,
                    token_type=TokenKind.ERC20,
                ))
            except (UnknownAsset, WrongAssetType):
                log.error(f'Found {self.evm_inquirer.chain_name} Hop balance for unknown token {checksummed_staking_token} or {checksummed_rewards_token}. Skipping')  # noqa: E501
                continue

            staked_rewards = self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(method_name='earned', arguments=[user]),
                ) for user in addresses],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )
            token_price = Inquirer.find_price(
                from_asset=staking_token,
                to_asset=(main_currency := CachedSettings().main_currency),
            )
            rewards_price = Inquirer.find_price(rewards_token, main_currency)
            for user, lp, reward in zip(addresses, staked_lps, staked_rewards, strict=True):
                try:
                    if (balance := staking_contract.decode(
                        result=lp,
                        method_name='balanceOf',
                        arguments=[user],
                    )[0]) != ZERO and (balance_norm := token_normalized_value(
                        token_amount=balance,
                        token=staking_token,
                    )) > ZERO:
                        balances[user].assets[staking_token][self.counterparty] += Balance(
                            amount=balance_norm,
                            value=token_price * balance_norm,
                        )
                except DeserializationError:
                    log.error(f'Failed to decode {self.evm_inquirer.chain_name} Hop staked balance for {user}. Skipping')  # noqa: E501
                    continue

                try:
                    if (rewards := staking_contract.decode(
                        result=reward,
                        method_name='earned',
                        arguments=[user],
                    )[0]) != ZERO and (reward_norm := token_normalized_value(
                        token_amount=rewards,
                        token=rewards_token,
                    )) > ZERO:
                        balances[user].assets[rewards_token][self.counterparty] += Balance(
                            amount=reward_norm,
                            value=rewards_price * reward_norm,
                        )
                except DeserializationError:
                    log.error(f'Failed to decode {self.evm_inquirer.chain_name} Hop earned rewards for {user}. Skipping')  # noqa: E501
                    continue

        return balances
