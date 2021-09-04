from typing import Any, Dict, List, NamedTuple, Optional, TYPE_CHECKING

from rotkehlchen.accounting.structures import AssetBalance, Balance
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import multicall_2, token_normalized_value_decimals
from rotkehlchen.constants.assets import A_PICKLE
from rotkehlchen.constants.ethereum import PICKLE_DILL, PICKLE_DILL_REWARDS
from rotkehlchen.errors import DeserializationError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

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

    def get_dill(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, DillBalance]:
        """
        Query information for amount locked, pending rewards and time until unlock
        for Pickle's dill.
        """
        api_output = {}

        rewards_contract = EthereumContract(
            address=PICKLE_DILL_REWARDS.address,
            abi=PICKLE_DILL_REWARDS.abi,
            deployed_block=PICKLE_DILL_REWARDS.deployed_block,
        )
        dill_contract = EthereumContract(
            address=PICKLE_DILL.address,
            abi=PICKLE_DILL.abi,
            deployed_block=PICKLE_DILL.deployed_block,
        )
        rewards_calls = [
            (
                PICKLE_DILL_REWARDS.address,
                rewards_contract.encode(method_name='claim', arguments=[x]),
            )
            for x in addresses
        ]
        balance_calls = [
            (PICKLE_DILL.address, dill_contract.encode(method_name='locked', arguments=[x]))
            for x in addresses
        ]
        reward_outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=rewards_calls,
        )
        dill_outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=balance_calls,
        )

        pickle_price = Inquirer().find_usd_price(A_PICKLE)
        for idx, output in enumerate(reward_outputs):
            status_rewards, result = output
            status_dill, result_dill = dill_outputs[idx]
            address = addresses[idx]
            if all((status_rewards, status_dill)):
                try:
                    rewards = rewards_contract.decode(result, 'claim', arguments=[address])
                    dill_amounts = dill_contract.decode(
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

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
