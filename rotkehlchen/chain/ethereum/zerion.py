import logging
from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils.address import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.defi import handle_defi_price_query
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.assets import A_DAI, A_USDC
from rotkehlchen.constants.ethereum import ZERION_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer, get_underlying_asset_price
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

log = logging.getLogger(__name__)


def _is_token_non_standard(symbol: str, address: ChecksumEthAddress) -> bool:
    """ignore some assets we do not yet support and don't want to spam warnings with"""
    if symbol in ('UNI-V2', 'swUSD', 'crCRV'):
        return True

    if address in ('0xCb2286d9471cc185281c4f763d34A962ED212962',):  # Sushi LP token
        return True

    return False


class DefiProtocol(NamedTuple):
    name: str
    description: str
    url: str
    icon_link: str
    version: int

    def serialize(self) -> Dict[str, str]:
        return {'name': self.name, 'icon': self.icon_link}


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


# Type of the argument given to functions that need the defi balances
GIVEN_DEFI_BALANCES = Union[
    Dict[ChecksumEthAddress, List[DefiProtocolBalances]],
    Callable[[], Dict[ChecksumEthAddress, List[DefiProtocolBalances]]],
]


def _handle_pooltogether(normalized_balance: FVal, token_name: str) -> Optional[DefiBalance]:
    """Special handling for pooltogether

    https://github.com/rotki/rotki/issues/1429
    """
    if 'DAI' in token_name:
        dai_price = Inquirer.find_usd_price(A_DAI)
        return DefiBalance(
            token_address=to_checksum_address('0x49d716DFe60b37379010A75329ae09428f17118d'),
            token_name='Pool Together DAI token',
            token_symbol='plDAI',
            balance=Balance(
                amount=normalized_balance,
                usd_value=normalized_balance * dai_price,
            ),
        )
    elif 'USDC' in token_name:
        usdc_price = Inquirer.find_usd_price(A_USDC)
        return DefiBalance(
            token_address=to_checksum_address('0xBD87447F48ad729C5c4b8bcb503e1395F62e8B98'),
            token_name='Pool Together USDC token',
            token_symbol='plUSDC',
            balance=Balance(
                amount=normalized_balance,
                usd_value=normalized_balance * usdc_price,
            ),
        )

    return None


# last known zerion adapter address
ZERION_ADAPTER_ADDRESS = deserialize_ethereum_address('0x06FE76B2f432fdfEcAEf1a7d4f6C3d41B5861672')


def query_zerion_address(
        ethereum: 'EthereumManager',
        msg_aggregator: MessagesAggregator,
) -> ChecksumEthAddress:
    """Queries the zerion contract address. If query fails, then last known
    address is used"""
    result = ethereum.ens_lookup('api.zerion.eth')
    if result is None:
        msg_aggregator.add_error(
            'Could not query api.zerion.eth address. Using last known address',
        )
        contract_address = ZERION_ADAPTER_ADDRESS
    else:
        contract_address = result

    return contract_address


class Zerion():
    """Adapter for the Zerion DeFi SDK https://github.com/zeriontech/defi-sdk"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
            contract_address: Optional[ChecksumEthAddress] = None,
    ) -> None:
        self.ethereum = ethereum_manager
        self.msg_aggregator = msg_aggregator

        if contract_address:
            self.contract_address = contract_address
            return

        # else
        self.contract_address = query_zerion_address(ethereum_manager, msg_aggregator)

    def all_balances_for_account(self, account: ChecksumEthAddress) -> List[DefiProtocolBalances]:
        """Calls the contract's getBalances() to get all protocol balances for account

        https://docs.zerion.io/smart-contracts/adapterregistry-v3#getbalances
        """
        result = self.ethereum.call_contract(
            contract_address=self.contract_address,
            abi=ZERION_ABI,
            method_name='getBalances',
            arguments=[account],
        )
        log.info("result: {}".format(result))
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
                    base_balance = self._get_single_balance(protocol.name, balances[0])
                    for balance in balances[1]:
                        defi_balance = self._get_single_balance(protocol.name, balance)
                        underlying_balances.append(defi_balance)

                    if base_balance.balance.usd_value == ZERO:
                        # This can happen. We can't find a price for some assets
                        # such as combined pool assets. But we can instead use
                        # the sum of the usd_value of the underlying_balances
                        usd_sum = sum(x.balance.usd_value for x in underlying_balances)
                        base_balance.balance.usd_value = usd_sum  # type: ignore

                    protocol_balances.append(DefiProtocolBalances(
                        protocol=protocol,
                        balance_type=balance_type,
                        base_balance=base_balance,
                        underlying_balances=underlying_balances,
                    ))

        return protocol_balances

    def _get_single_balance(
            self,
            protocol_name: str,
            entry: Tuple[Tuple[str, str, str, int], int],
    ) -> DefiBalance:
        metadata = entry[0]
        balance_value = entry[1]
        decimals = metadata[3]
        normalized_value = token_normalized_value(balance_value, decimals)
        token_symbol = metadata[2]
        token_address = to_checksum_address(metadata[0])
        token_name = metadata[1]

        special_handling = self.handle_protocols(
            protocol_name=protocol_name,
            token_symbol=token_symbol,
            normalized_balance=normalized_value,
            token_address=token_address,
            token_name=token_name,
        )
        if special_handling:
            return special_handling

        try:
            asset = Asset(token_symbol)
            usd_price = Inquirer().find_usd_price(asset)
        except (UnknownAsset, UnsupportedAsset):
            if not _is_token_non_standard(token_symbol, token_address):
                self.msg_aggregator.add_warning(
                    f'Unsupported asset {token_symbol} encountered during DeFi protocol queries',
                )
            usd_price = Price(ZERO)

        usd_value = normalized_value * usd_price
        defi_balance = DefiBalance(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            balance=Balance(amount=normalized_value, usd_value=usd_value),
        )
        return defi_balance

    def handle_protocols(
            self,
            protocol_name: str,
            token_symbol: str,
            normalized_balance: FVal,
            token_address: str,
            token_name: str,
    ) -> Optional[DefiBalance]:
        """Special handling for price for token/protocols which are easier to do onchain
        or need some kind of special treatment.
        """
        if protocol_name == 'PoolTogether':
            result = _handle_pooltogether(normalized_balance, token_name)
            if result is not None:
                return result

        underlying_asset_price = get_underlying_asset_price(token_symbol)
        usd_price = handle_defi_price_query(self.ethereum, token_symbol, underlying_asset_price)
        if usd_price is None:
            return None

        return DefiBalance(
            token_address=to_checksum_address(token_address),
            token_name=token_name,
            token_symbol=token_symbol,
            balance=Balance(amount=normalized_balance, usd_value=normalized_balance * usd_price),
        )
