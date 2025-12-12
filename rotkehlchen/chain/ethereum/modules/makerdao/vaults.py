import logging
from collections import defaultdict
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.evm.proxies_inquirer import ProxyType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import (
    ts_now,
)

from .cache import collateral_type_to_underlying_asset
from .constants import CPT_VAULT, MAKERDAO_REQUERY_PERIOD, WAD

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VaultEventType(Enum):
    DEPOSIT_COLLATERAL = 1
    WITHDRAW_COLLATERAL = 2
    GENERATE_DEBT = 3
    PAYBACK_DEBT = 4
    LIQUIDATION = 5

    def __str__(self) -> str:
        if self == VaultEventType.DEPOSIT_COLLATERAL:
            return 'deposit'
        if self == VaultEventType.WITHDRAW_COLLATERAL:
            return 'withdraw'
        if self == VaultEventType.GENERATE_DEBT:
            return 'generate'
        if self == VaultEventType.PAYBACK_DEBT:
            return 'payback'
        if self == VaultEventType.LIQUIDATION:
            return 'liquidation'
        # else
        raise RuntimeError(f'Corrupt value {self} for VaultEventType -- Should never happen')


class VaultEvent(NamedTuple):
    event_type: VaultEventType
    value: Balance
    timestamp: Timestamp
    tx_hash: EVMTxHash

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        result = f'Makerdao Vault {self.event_type}'
        if self.event_type in (VaultEventType.GENERATE_DEBT, VaultEventType.PAYBACK_DEBT):
            result += ' debt'
        return result


class MakerdaoVault(NamedTuple):
    identifier: int
    # The type of collateral used for the vault. asset + set of parameters.
    # e.g. ETH-A. Various types can be seen here: https://catflip.co/
    collateral_type: str
    owner: ChecksumEvmAddress
    collateral_asset: CryptoAsset
    # The amount/usd_value of collateral tokens locked
    collateral: Balance
    # amount/usd value of DAI drawn
    debt: Balance
    # The current collateralization_ratio of the Vault. None if nothing is locked in.
    collateralization_ratio: str | None
    # The ratio at which the vault is open for liquidation. (e.g. 1.5 for 150%)
    liquidation_ratio: FVal
    # The USD price of collateral at which the Vault becomes unsafe. None if nothing is locked in.
    liquidation_price: FVal | None
    urn: ChecksumEvmAddress
    stability_fee: FVal

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        # But make sure to turn liquidation ratio and stability fee to a percentage
        result['collateral_asset'] = self.collateral_asset.identifier
        result['liquidation_ratio'] = self.liquidation_ratio.to_percentage(2)
        result['stability_fee'] = self.stability_fee.to_percentage(2)
        result['collateral'] = self.collateral.serialize()
        result['debt'] = self.debt.serialize()
        result['liquidation_price'] = (
            str(self.liquidation_price) if self.liquidation_price else None
        )
        # And don't send unneeded data
        del result['urn']
        return result

    @property
    def ilk(self) -> bytes:
        """Returns the collateral type string encoded into bytes32, known as ilk in makerdao"""
        return self.collateral_type.encode('utf-8').ljust(32, b'\x00')

    def get_balance(self) -> BalanceSheet:
        starting_assets: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501
        starting_liabilities: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501
        if self.collateral.amount != ZERO:
            starting_assets[self.collateral_asset][CPT_VAULT] = self.collateral

        if self.debt.amount != ZERO:
            starting_liabilities[A_DAI][CPT_VAULT] = self.debt

        return BalanceSheet(
            assets=starting_assets,
            liabilities=starting_liabilities,
        )


class MakerdaoVaults(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.msg_aggregator = msg_aggregator
        self.reset_last_query_ts()
        self.lock = Semaphore()
        self.vault_mappings: dict[ChecksumEvmAddress, list[MakerdaoVault]] = defaultdict(list)
        self.ilk_to_stability_fee: dict[bytes, FVal] = {}

        self.dai = A_DAI.resolve_to_evm_token()
        self.makerdao_jug = self.ethereum.contracts.contract(string_to_evm_address('0x19c0976f590D67707E62397C87829d896Dc0f1F1'))  # noqa: E501
        self.makerdao_vat = self.ethereum.contracts.contract(string_to_evm_address('0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B'))  # noqa: E501
        self.makerdao_cdp_manager = self.ethereum.contracts.contract(string_to_evm_address('0x5ef30b9986345249bc32d8928B7ee64DE9435E39'))  # noqa: E501
        self.makerdao_get_cdps = self.ethereum.contracts.contract(string_to_evm_address('0x36a724Bd100c39f0Ea4D3A20F7097eE01A8Ff573'))  # noqa: E501
        self.makerdao_spot = self.ethereum.contracts.contract(string_to_evm_address('0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3'))  # noqa: E501

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        self.ethereum.proxies_inquirer.reset_last_query_ts()
        self.last_vault_mapping_query_ts = 0

    def get_stability_fee(self, ilk: bytes) -> FVal:
        """If we already know the current stability_fee for ilk return it. If not query it"""
        if ilk in self.ilk_to_stability_fee:
            return self.ilk_to_stability_fee[ilk]

        result = self.makerdao_jug.call(self.ethereum, 'ilks', arguments=[ilk])
        # result[0] is the duty variable of the ilks in the contract
        return FVal(result[0] / RAY) ** (YEAR_IN_SECONDS) - 1

    def _query_vault_data(
            self,
            identifier: int,
            owner: ChecksumEvmAddress,
            urn: ChecksumEvmAddress,
            ilk: bytes,
    ) -> MakerdaoVault | None:
        collateral_type = ilk.split(b'\0', 1)[0].decode()
        asset = collateral_type_to_underlying_asset(collateral_type)
        if asset is None:
            self.msg_aggregator.add_warning(
                f'Detected vault with collateral_type {collateral_type}. That '
                f'is not yet supported by rotki. Skipping...',
            )
            return None

        result = self.makerdao_vat.call(self.ethereum, 'urns', arguments=[ilk, urn])
        # also known as ink in their contract
        collateral_amount = FVal(result[0] / WAD)
        normalized_debt = result[1]  # known as art in their contract
        result = self.makerdao_vat.call(self.ethereum, 'ilks', arguments=[ilk])
        rate = result[1]  # Accumulated Rates
        spot = FVal(result[2])  # Price with Safety Margin
        # How many DAI owner needs to pay back to the vault
        debt_value = FVal(((normalized_debt / WAD) * rate) / RAY)
        result = self.makerdao_spot.call(self.ethereum, 'ilks', arguments=[ilk])
        mat = result[1]
        liquidation_ratio = FVal(mat / RAY)
        price = FVal((spot / RAY) * liquidation_ratio)
        collateral_value = FVal(price * collateral_amount)
        if debt_value == 0:
            collateralization_ratio = None
        else:
            collateralization_ratio = FVal(collateral_value / debt_value).to_percentage(2)

        if collateral_amount == 0:
            liquidation_price = None
        else:
            liquidation_price = (debt_value * liquidation_ratio) / collateral_amount

        prices = Inquirer.find_main_currency_prices([asset, A_DAI])
        return MakerdaoVault(
            identifier=identifier,
            owner=owner,
            collateral_type=collateral_type,
            collateral_asset=asset,
            collateral=Balance(amount=collateral_amount, value=prices[asset] * collateral_amount),
            debt=Balance(amount=debt_value, value=prices[A_DAI] * debt_value),
            liquidation_ratio=liquidation_ratio,
            collateralization_ratio=collateralization_ratio,
            liquidation_price=liquidation_price,
            urn=urn,
            stability_fee=self.get_stability_fee(ilk),
        )

    def _get_vaults_of_address(
            self,
            user_address: ChecksumEvmAddress,
            proxy_address: ChecksumEvmAddress,
    ) -> list[MakerdaoVault]:
        """Gets the vaults of a single address

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        result = self.makerdao_get_cdps.call(
            node_inquirer=self.ethereum,
            method_name='getCdpsAsc',
            arguments=[self.makerdao_cdp_manager.address, proxy_address],
        )

        vaults = []
        for idx, identifier in enumerate(result[0]):
            try:
                urn = deserialize_evm_address(result[1][idx])
            except DeserializationError as e:
                raise RemoteError(
                    f'Failed to deserialize address {result[1][idx]} '
                    f'when processing vaults of {user_address}',
                ) from e
            vault = self._query_vault_data(
                identifier=identifier,
                owner=user_address,
                urn=urn,
                ilk=result[2][idx],
            )
            if vault:
                vaults.append(vault)
                self.vault_mappings[user_address].append(vault)

        return vaults

    def get_vaults(self) -> list[MakerdaoVault]:
        """Detects vaults the user has and returns basic info about each one

        If the vaults have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_vault_mapping_query_ts < MAKERDAO_REQUERY_PERIOD:
            prequeried_vaults = []
            for vaults in self.vault_mappings.values():
                prequeried_vaults.extend(vaults)

            prequeried_vaults.sort(key=lambda vault: vault.identifier)
            return prequeried_vaults

        with self.lock:
            self.vault_mappings = defaultdict(list)
            proxy_mappings = self.ethereum.proxies_inquirer.get_accounts_having_proxy(proxy_type=ProxyType.DS)  # noqa: E501
            vaults = []
            for user_address, proxies in proxy_mappings.items():
                for proxy in proxies:
                    vaults.extend(
                        self._get_vaults_of_address(user_address=user_address, proxy_address=proxy),  # noqa: E501
                    )

            self.last_vault_mapping_query_ts = ts_now()
            # Returns vaults sorted. Oldest identifier first
            vaults.sort(key=lambda vault: vault.identifier)
        return vaults

    def get_balances(self) -> dict[ChecksumEvmAddress, BalanceSheet]:
        """Return a mapping of all assets locked as collateral in the vaults and
        all DAI owed as debt
        """
        balances: defaultdict[ChecksumEvmAddress, BalanceSheet] = defaultdict(BalanceSheet)
        for vault in self.get_vaults():
            balances[vault.owner] += vault.get_balance()
        return balances

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:  # pylint: disable=useless-return
        # Check if it has been added to the mapping
        proxy_addresses = self.ethereum.proxies_inquirer.address_to_proxies[ProxyType.DS].get(address, set())  # noqa: E501
        for proxy_address in proxy_addresses:
            # get any vaults the proxy owns
            self._get_vaults_of_address(user_address=address, proxy_address=proxy_address)

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        self.vault_mappings.pop(address, None)

    def deactivate(self) -> None:
        ...
