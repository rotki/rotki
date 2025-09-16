import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, cast

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance, BalanceSheet
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.proxies_inquirer import ProxyType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress, Price
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import from_wei

from .constants import CPT_LIQUITY

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.contracts import EvmContract
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

MIN_COLL_RATE = '1.1'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Trove(NamedTuple):
    collateral: AssetBalance
    debt: AssetBalance
    collateralization_ratio: FVal | None
    liquidation_price: FVal | None
    active: bool
    trove_id: int

    def serialize(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        result['collateral'] = self.collateral.serialize()
        result['debt'] = self.debt.serialize()
        result['collateralization_ratio'] = self.collateralization_ratio
        result['liquidation_price'] = self.liquidation_price
        result['active'] = self.active
        result['trove_id'] = self.trove_id
        return result


class LiquityBalanceWithProxy(TypedDict):
    proxies: dict[ChecksumEvmAddress, dict[str, AssetBalance]] | None
    balances: dict[str, AssetBalance] | None


class GetPositionsResult (TypedDict):
    balances: dict[ChecksumEvmAddress, Trove]
    total_collateral_ratio: FVal | None


def default_balance_with_proxy_factory() -> LiquityBalanceWithProxy:
    return cast('LiquityBalanceWithProxy', {'proxies': None, 'balances': None})


class Liquity(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.msg_aggregator = msg_aggregator
        self.trove_manager_contract = self.ethereum.contracts.contract(string_to_evm_address('0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2'))  # noqa: E501
        self.stability_pool_contract = self.ethereum.contracts.contract(string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'))  # noqa: E501
        self.staking_contract = self.ethereum.contracts.contract(string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'))  # noqa: E501

    def _calculate_total_collateral_ratio(self, eth_price: Price) -> FVal | None:
        """Query Liquity smart contract for Total Collateral Ratio (TCR).
        If the TCR of the system falls below 150% the system enters recovery Mode"""
        try:
            total_collateral_ratio = self.trove_manager_contract.call(
                node_inquirer=self.ethereum,
                method_name='getTCR',
                arguments=[FVal(eth_price * 10**18).to_int(exact=False)],
            )

        except RemoteError as e:
            log.error(f'Failed to query liquity contract for protocol collateral ratio: {e}')
            return None

        return from_wei(FVal(total_collateral_ratio) * 100)

    def get_positions(
            self,
            given_addresses: Sequence[ChecksumEvmAddress],
    ) -> GetPositionsResult:
        """Query liquity contract to detect open troves and
        query total collateral ratio of the protocol"""
        addresses = list(given_addresses)  # turn to a mutable list copy to add proxies
        proxy_mapping = self.ethereum.proxies_inquirer.get_accounts_having_proxy(proxy_type=ProxyType.DS)  # At least v1 had only DS proxy # noqa: E501
        proxies_to_address = {}
        for user_address, proxy_addresses in proxy_mapping.items():
            addresses.extend(proxy_addresses)
            for proxy_address in proxy_addresses:
                proxies_to_address[proxy_address] = user_address

        calls = [
            (self.trove_manager_contract.address, self.trove_manager_contract.encode(method_name='Troves', arguments=[x]))  # noqa: E501
            for x in addresses
        ]
        outputs = self.ethereum.multicall_2(
            require_success=False,
            calls=calls,
        )

        data: dict[ChecksumEvmAddress, Trove] = {}
        eth_price = Inquirer.find_usd_price(A_ETH)
        lusd_price = Inquirer.find_usd_price(A_LUSD)
        for idx, output in enumerate(outputs):
            status, result = output
            if status is True:
                try:
                    trove_info = self.trove_manager_contract.decode(result, 'Troves', arguments=[addresses[idx]])  # noqa: E501
                    trove_is_active = bool(trove_info[3])
                    if not trove_is_active:
                        continue
                    collateral = deserialize_fval(
                        token_normalized_value_decimals(trove_info[1], 18),
                    )
                    debt = deserialize_fval(
                        token_normalized_value_decimals(trove_info[0], 18),
                    )
                    collateral_balance = AssetBalance(
                        asset=A_ETH,
                        balance=Balance(
                            amount=collateral,
                            usd_value=eth_price * collateral,
                        ),
                    )
                    debt_balance = AssetBalance(
                        asset=A_LUSD,
                        balance=Balance(
                            amount=debt,
                            usd_value=lusd_price * debt,
                        ),
                    )
                    # Avoid division errors
                    collateralization_ratio: FVal | None
                    liquidation_price: FVal | None
                    if debt > 0:
                        collateralization_ratio = eth_price * collateral / debt * 100
                    else:
                        collateralization_ratio = None
                    if collateral > 0:
                        liquidation_price = debt * lusd_price * FVal(MIN_COLL_RATE) / collateral
                    else:
                        liquidation_price = None

                    account_address = addresses[idx]
                    if account_address in proxies_to_address:
                        account_address = proxies_to_address[account_address]
                    data[account_address] = Trove(
                        collateral=collateral_balance,
                        debt=debt_balance,
                        collateralization_ratio=collateralization_ratio,
                        liquidation_price=liquidation_price,
                        active=trove_is_active,
                        trove_id=trove_info[4],
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'Ignoring Liquity trove information. '
                        f'Failed to decode contract information. {e!s}.',
                    )
        return GetPositionsResult(
            balances=data,
            total_collateral_ratio=self._calculate_total_collateral_ratio(eth_price),
        )

    def _query_deposits_and_rewards(
            self,
            contract: 'EvmContract',
            given_addresses: Sequence[ChecksumEvmAddress],
            methods: tuple[str, str, str],
            keys: tuple[str, str, str],
            assets: tuple['Asset', 'Asset', 'Asset'],
    ) -> dict[ChecksumEvmAddress, LiquityBalanceWithProxy]:
        """
        For Liquity staking contracts there is always one asset that we stake and two other assets
        for rewards. This method abstracts the logic of querying the staked amount and the
        rewards for both the stability pool and the LQTY staking.

        - given_addresses: The addresses that will be queried
        - methods: the methods that need to be queried to get the staked amount and rewards
        - keys: the keys used in the dict response to map each method
        - assets: the asset associated with each method called
        """
        addresses = list(given_addresses)  # turn to a mutable list copy to add proxies
        for proxy_mappings in self.ethereum.proxies_inquirer.get_accounts_having_proxy().values():
            for proxy_addresses in proxy_mappings.values():
                addresses.extend(proxy_addresses)

        # Build the calls that need to be made in order to get the status in the SP
        calls = [
            (contract.address, contract.encode(method_name=method, arguments=[address]))
            for address in addresses for method in methods
        ]
        try:
            outputs = self.ethereum.multicall_2(
                require_success=False,
                calls=calls,
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(
                f'Failed to query information about liquity stability pool. {e!s}',
            )
            return {}

        # the structure of the queried data is:
        # staked address 1, reward 1 of address 1, reward 2 of address 1, staked address 2, reward 1 of address 2, ...  # noqa: E501
        data: defaultdict[ChecksumEvmAddress, LiquityBalanceWithProxy] = defaultdict(default_balance_with_proxy_factory)  # noqa: E501
        for idx, output in enumerate(outputs):
            # depending on the output index get the address we are tracking
            current_address = addresses[idx // 3]
            status, result = output
            if status is False:
                continue

            # make sure that variables always have a value set. It is guaranteed that the response
            # will have the desired format because we include and process failed queries.
            key, asset, gain_info = keys[0], assets[0], 0
            for method_idx, (method, _asset, _key) in enumerate(zip(methods, assets, keys, strict=True)):  # noqa: E501
                # get the asset, key used in the response and the amount based on the index
                # for this address
                if idx % 3 == method_idx:
                    asset = _asset
                    key = _key
                    gain_info = contract.decode(result, method, arguments=[current_address])[0]
                    break

            # get price information for the asset and deserialize the amount
            asset_price = Inquirer.find_usd_price(asset)
            amount = deserialize_fval(
                token_normalized_value_decimals(gain_info, 18),
            )

            proxy_owner = None
            for proxy_type in ProxyType:
                if (proxy_owner := self.ethereum.proxies_inquirer.proxy_to_address[proxy_type].get(current_address)):  # noqa: E501
                    break

            if proxy_owner is not None:
                if data[proxy_owner]['proxies'] is None:
                    data[proxy_owner]['proxies'] = defaultdict(dict)

                data[proxy_owner]['proxies'][current_address][key] = AssetBalance(  # type: ignore[index]  # here and below mypy fails to detect that we check the None case
                    asset=asset,
                    balance=Balance(
                        amount=amount,
                        usd_value=asset_price * amount,
                    ),
                )
            else:
                if data[current_address]['balances'] is None:
                    data[current_address]['balances'] = {}

                data[current_address]['balances'][key] = AssetBalance(  # type: ignore[index]
                    asset=asset,
                    balance=Balance(
                        amount=amount,
                        usd_value=asset_price * amount,
                    ),
                )
        return data

    def get_stability_pool_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, LiquityBalanceWithProxy]:
        """Returns the balances of the liquity stability pool

        Returns the balances and whether the addresses returned
        is a proxy address to any of the tracked accounts.
        """
        return self._query_deposits_and_rewards(
            contract=self.stability_pool_contract,
            given_addresses=addresses,
            methods=('getDepositorETHGain', 'getDepositorLQTYGain', 'getCompoundedLUSDDeposit'),
            keys=('gains', 'rewards', 'deposited'),
            assets=(A_ETH, A_LQTY, A_LUSD),
        )

    def liquity_staking_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, LiquityBalanceWithProxy]:
        """Query the ethereum chain to retrieve information about staked assets.

        Returns the balances and whether the addresses returned
        is a proxy address to any of the tracked accounts.
        """
        return self._query_deposits_and_rewards(
            contract=self.staking_contract,
            given_addresses=addresses,
            methods=('stakes', 'getPendingLUSDGain', 'getPendingETHGain'),
            keys=('staked', 'lusd_rewards', 'eth_rewards'),
            assets=(A_LQTY, A_LUSD, A_ETH),
        )

    @staticmethod
    def _add_addr_and_proxy_balances(
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
            new_balances: dict[ChecksumEvmAddress, LiquityBalanceWithProxy],
            token: 'Asset',
            key: str,
    ) -> None:
        """
        Add to balances the information in new_balances abstracting the key and token fields
        """
        for address, staked_info in new_balances.items():
            if staked_info['balances'] is not None:
                pool_balance = staked_info['balances'][key].balance
                if pool_balance.amount > ZERO:
                    balances[address].assets[token][CPT_LIQUITY] += pool_balance

            if staked_info['proxies'] is not None:
                for proxy_balance in staked_info['proxies'].values():
                    pool_balance = proxy_balance[key].balance
                    if pool_balance.amount > ZERO:
                        balances[address].assets[token][CPT_LIQUITY] += pool_balance

    def enrich_staking_balances(
            self,
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
            queried_addresses: Sequence[ChecksumEvmAddress],
    ) -> None:
        """Include LQTY and LUSD staking balances in the balances mapping"""
        liquity_staked = self.liquity_staking_balances(addresses=queried_addresses)
        self._add_addr_and_proxy_balances(
            balances=balances,
            new_balances=liquity_staked,
            token=A_LQTY,
            key='staked',
        )
        lusd_stability_pool = self.get_stability_pool_balances(addresses=queried_addresses)
        self._add_addr_and_proxy_balances(
            balances=balances,
            new_balances=lusd_stability_pool,
            token=A_LUSD,
            key='deposited',
        )

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        ...

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        ...

    def deactivate(self) -> None:
        ...
