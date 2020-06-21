import logging
from typing import TYPE_CHECKING, Any, List, NamedTuple, Tuple

from eth_utils.address import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.ethereum import ZERION_ADAPTER_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

log = logging.getLogger(__name__)


class DefiProtocol(NamedTuple):
    name: str
    description: str
    url: str
    icon_link: str
    version: int


class DefiBalance(NamedTuple):
    token_address: ChecksumEthAddress
    token_name: str
    token_symbol: str
    balance: Balance


class DefiProtocolBalances(NamedTuple):
    protocol: DefiProtocol
    balance_type: Literal['Asset', 'Debt']
    base_balance: DefiBalance
    underlying_balances: List[DefiBalance]


class Zerion():
    """Adapter for the Zerion DeFi SDK https://github.com/zeriontech/defi-sdk"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.msg_aggregator = msg_aggregator
        self.contract_address = self.ethereum.ens_lookup('api.zerion.eth')

    def all_balances_for_account(self, account: ChecksumEthAddress) -> None:
        """Calls the contract's getBalances() to get all protocol balances for account

        https://docs.zerion.io/smart-contracts/adapterregistry-v3#getbalances
        """
        result = self.ethereum.call_contract(
            contract_address=self.contract_address,
            abi=ZERION_ADAPTER_ABI,
            method_name='getBalances',
            arguments=[account],
        )
        protocol_balances = []
        for entry in result:
            protocol = DefiProtocol(
                name=entry[0][0],
                description=entry[0][1],
                url=entry[0][2],
                icon_link=entry[0][3],
                version=entry[0][4],
            )
            for adapter_balance in entry[1]:
                balance_type = adapter_balance[0][1]  # can be either 'Asset' or 'Debt'
                for balances in adapter_balance[1]:
                    underlying_balances = []
                    base_balance = self._get_single_balance(balances[0])
                    for balance in balances[1]:
                        defi_balance = self._get_single_balance(balance)
                        underlying_balances.append(defi_balance)

                protocol_balances.append(DefiProtocolBalances(
                    protocol=protocol,
                    balance_type=balance_type,
                    base_balance=base_balance,
                    underlying_balances=underlying_balances,
                ))

        return protocol_balances

    def _get_single_balance(self, entry: Tuple[Tuple[Any], int]) -> DefiBalance:
        metadata = entry[0]
        balance_value = entry[1]
        decimals = metadata[3]
        normalized_value = token_normalized_value(balance_value, decimals)
        token_symbol = metadata[2]
        try:
            asset = Asset(token_symbol)
            usd_price = Inquirer().find_usd_price(asset)
        except (UnknownAsset, UnsupportedAsset):
            if '+' not in token_symbol:  # ignore the curve fi "pool" combined base asset
                self.msg_aggregator.add_error(
                    f'Unsupported asset {token_symbol} encountered during DeFi protocol queries',
                )
            usd_price = ZERO

        usd_value = normalized_value * usd_price

        defi_balance = DefiBalance(
            token_address=to_checksum_address(metadata[0]),
            token_name=metadata[1],
            token_symbol=token_symbol,
            balance=Balance(amount=normalized_value, usd_value=usd_value),
        )
        return defi_balance
