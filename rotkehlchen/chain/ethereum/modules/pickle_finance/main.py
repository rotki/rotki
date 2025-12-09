from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_PICKLE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


class DillBalance(NamedTuple):
    dill_amount: AssetBalance
    pending_rewards: AssetBalance
    lock_time: Timestamp

    def serialize(self) -> dict[str, Any]:
        return {
            'locked_amount': self.dill_amount.serialize(),
            'pending_rewards': self.pending_rewards.serialize(),
            'locked_until': self.lock_time,
        }


class PickleFinance(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.rewards_contract = self.ethereum.contracts.contract(string_to_evm_address('0x74C6CadE3eF61d64dcc9b97490d9FbB231e4BdCc'))  # noqa: E501
        self.dill_contract = self.ethereum.contracts.contract(string_to_evm_address('0xbBCf169eE191A1Ba7371F30A1C344bFC498b29Cf'))  # noqa: E501
        self.pickle = A_PICKLE.resolve_to_evm_token()

    def get_dill_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, DillBalance]:
        """
        Query information for amount locked, pending rewards and time until unlock
        for Pickle's dill.
        """
        api_output = {}
        rewards_calls = [
            (
                self.rewards_contract.address,
                self.rewards_contract.encode(method_name='claim', arguments=[x]),
            )
            for x in addresses
        ]
        balance_calls = [
            (self.dill_contract.address, self.dill_contract.encode(method_name='locked', arguments=[x]))  # noqa: E501
            for x in addresses
        ]
        outputs = self.ethereum.multicall_2(
            require_success=False,
            calls=rewards_calls + balance_calls,
        )
        reward_outputs, dill_outputs = outputs[:len(addresses)], outputs[len(addresses):]

        pickle_price = Inquirer.find_price(A_PICKLE, CachedSettings().main_currency)
        for idx, output in enumerate(reward_outputs):
            status_rewards, result = output
            status_dill, result_dill = dill_outputs[idx]
            address = addresses[idx]
            if all((status_rewards, status_dill)):
                try:
                    rewards = self.rewards_contract.decode(result, 'claim', arguments=[address])
                    dill_amounts = self.dill_contract.decode(
                        result_dill,
                        'locked',
                        arguments=[address],
                    )
                    dill_rewards = token_normalized_value_decimals(
                        token_amount=rewards[0],
                        token_decimals=self.pickle.decimals,
                    )
                    dill_locked = token_normalized_value_decimals(
                        token_amount=dill_amounts[0],
                        token_decimals=self.pickle.decimals,
                    )
                    balance = DillBalance(
                        dill_amount=AssetBalance(
                            asset=A_PICKLE,
                            balance=Balance(
                                amount=dill_locked,
                                value=pickle_price * dill_locked,
                            ),
                        ),
                        pending_rewards=AssetBalance(
                            asset=A_PICKLE,
                            balance=Balance(
                                amount=dill_rewards,
                                value=pickle_price * dill_rewards,
                            ),
                        ),
                        lock_time=deserialize_timestamp(dill_amounts[1]),
                    )
                    api_output[address] = balance
                except (DeserializationError, IndexError) as e:
                    self.msg_aggregator.add_error(
                        f'Failed to query dill information for address {address}. {e!s}',
                    )

        return api_output

    def balances_in_protocol(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list['AssetBalance']]:
        """Queries all the pickles deposited and available to claim in the protocol"""
        dill_balances = self.get_dill_balances(addresses)
        balances_per_address: dict[ChecksumEvmAddress, list[AssetBalance]] = defaultdict(list)
        for address, dill_balance in dill_balances.items():
            pickles = dill_balance.dill_amount + dill_balance.pending_rewards
            if pickles.balance.amount != 0:
                balances_per_address[address] += [pickles]
        return balances_per_address

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
