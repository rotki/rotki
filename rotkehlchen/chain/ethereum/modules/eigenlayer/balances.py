import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_EIGENLAYER

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.interfaces.balances import BalancesType
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal


UNDERLYING_BALANCES_ABI: Final = [{'inputs': [], 'name': 'underlyingToken', 'outputs': [{'internalType': 'contract IERC20', 'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'internalType': 'address', 'name': 'user', 'type': 'address'}], 'name': 'userUnderlyingView', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _read_underlying_assets(
        evm_inquirer: 'EthereumInquirer',
        strategy_address: ChecksumEvmAddress,
        depositor: ChecksumEvmAddress,
) -> tuple['FVal', 'EvmToken']:
    """
    Query the amount deposited in an eigenlayer strategy and the token of the strategy
    May raise:
    - RemoteError
    - NotERC20Conformant
    """
    contract = EvmContract(
        address=strategy_address,
        abi=UNDERLYING_BALANCES_ABI,
        deployed_block=0,
    )
    deposited_amount_raw = contract.call(
        node_inquirer=evm_inquirer,
        method_name='userUnderlyingView',
        arguments=[depositor],
    )
    underlying_token_address = contract.call(
        node_inquirer=evm_inquirer,
        method_name='underlyingToken',
    )
    token = get_or_create_evm_token(
        userdb=evm_inquirer.database,
        evm_address=underlying_token_address,
        chain_id=evm_inquirer.chain_id,
    )
    amount = asset_normalized_value(
        amount=deposited_amount_raw,
        asset=token,
    )
    return amount, token


class EigenlayerBalances(ProtocolWithBalance):
    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'EthereumInquirer',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            counterparty=CPT_EIGENLAYER,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.evm_inquirer: 'EthereumInquirer'

    def query_balances(self) -> 'BalancesType':
        """
        Query underlying balances for deposits in eigenlayer
        May raise:
        - RemoteError: Querying price of the deposited token
        """
        balances: BalancesType = defaultdict(lambda: defaultdict(Balance))
        # fetch deposit events
        addresses_with_deposits = self.addresses_with_deposits(products=[EvmProduct.STAKING])
        # remap all events into a list that will contain all pairs (depositor, strategy)
        deposits = set()
        for depositor, event_list in addresses_with_deposits.items():
            for event in event_list:
                if event.extra_data is None:
                    continue
                if (strategy := event.extra_data.get('strategy')) is not None:
                    deposits.add((depositor, strategy))

        if len(deposits) == 0:  # user had no related events
            return balances

        for depositor, strategy in deposits:
            try:
                amount, token = _read_underlying_assets(
                    evm_inquirer=self.evm_inquirer,
                    strategy_address=strategy,
                    depositor=depositor,
                )
            except (RemoteError, NotERC20Conformant) as e:
                log.error(
                    f'Failed to query eigenlayer balances for {depositor} due to {e}. Skipping',
                )
                continue

            token_price = Inquirer.find_usd_price(token)
            balances[depositor][token] += Balance(
                amount=amount,
                usd_value=token_price * amount,
            )

        return balances
