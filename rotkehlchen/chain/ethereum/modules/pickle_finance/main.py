from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import multicall_2, token_normalized_value_decimals
from rotkehlchen.constants.assets import A_PICKLE
from rotkehlchen.constants.ethereum import PICKLE_DILL, PICKLE_DILL_REWARDS
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class DillBalance(NamedTuple):
    dill_amount: AssetBalance
    pending_rewards: AssetBalance
    lock_time: Timestamp

    def serialize(self) -> Dict[str, Any]:
        return {
            "locked_amount": self.dill_amount.serialize(),
            "pending_rewards": self.pending_rewards.serialize(),
            "locked_until": self.lock_time,
        }


class PickleFinance(EthereumModule):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.rewards_contract = EthereumContract(
            address=PICKLE_DILL_REWARDS.address,
            abi=PICKLE_DILL_REWARDS.abi,
            deployed_block=PICKLE_DILL_REWARDS.deployed_block,
        )
        self.dill_contract = EthereumContract(
            address=PICKLE_DILL.address,
            abi=PICKLE_DILL.abi,
            deployed_block=PICKLE_DILL.deployed_block,
        )

    def get_dill_balances(
        self,
        addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, DillBalance]:
        """
        Query information for amount locked, pending rewards and time until unlock
        for Pickle's dill.
        """
        api_output = {}
        rewards_calls = [
            (
                PICKLE_DILL_REWARDS.address,
                self.rewards_contract.encode(method_name='claim', arguments=[x]),
            )
            for x in addresses
        ]
        balance_calls = [
            (PICKLE_DILL.address, self.dill_contract.encode(method_name='locked', arguments=[x]))
            for x in addresses
        ]
        outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=rewards_calls + balance_calls,
        )
        reward_outputs, dill_outputs = outputs[:len(addresses)], outputs[len(addresses):]

        pickle_price = Inquirer().find_usd_price(A_PICKLE)
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
                        token_amount=rewards[0],  # pylint: disable=unsubscriptable-object
                        token_decimals=A_PICKLE.decimals,
                    )
                    dill_locked = token_normalized_value_decimals(
                        token_amount=dill_amounts[0],  # pylint: disable=unsubscriptable-object
                        token_decimals=A_PICKLE.decimals,
                    )
                    balance = DillBalance(
                        dill_amount=AssetBalance(
                            asset=A_PICKLE,
                            balance=Balance(
                                amount=dill_locked,
                                usd_value=pickle_price * dill_locked,
                            ),
                        ),
                        pending_rewards=AssetBalance(
                            asset=A_PICKLE,
                            balance=Balance(
                                amount=dill_rewards,
                                usd_value=pickle_price * dill_rewards,
                            ),
                        ),
                        lock_time=deserialize_timestamp(dill_amounts[1]),  # noqa: E501 pylint: disable=unsubscriptable-object
                    )
                    api_output[address] = balance
                except (DeserializationError, IndexError) as e:
                    self.msg_aggregator.add_error(
                        f'Failed to query dill information for address {address}. {str(e)}',
                    )

        return api_output

    def balances_in_protocol(
        self,
        addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, List['AssetBalance']]:
        """Queries all the pickles deposited and available to claim in the protocol"""
        dill_balances = self.get_dill_balances(addresses)
        balances_per_address: Dict[ChecksumEvmAddress, List['AssetBalance']] = defaultdict(list)
        for address, dill_balance in dill_balances.items():
            pickles = dill_balance.dill_amount + dill_balance.pending_rewards
            if pickles.balance.amount != 0:
                balances_per_address[address] += [pickles]
        return balances_per_address

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> Optional[List['AssetBalance']]:
        return self.balances_in_protocol([address]).get(address, None)

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
