import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import YEARN_VAULTS_V2_PROTOCOL, ChecksumEvmAddress
from rotkehlchen.utils.interfaces import EthereumModule

from .constants import BLOCKS_PER_YEAR
from .vaults import YearnVaultBalance

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_ETH_BALANCES
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnVaultsV2(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: 'Premium | None',  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.msg_aggregator = msg_aggregator

    def _calculate_vault_roi_and_pps(self, vault: EvmToken) -> tuple[FVal | None, int]:
        """
        getPricePerFullShare A @ block X
        getPricePerFullShare B @ block Y

        (A-B / X-Y) * blocksPerYear (2425846)

        So the numbers you see displayed on http://yearn.fi/vaults
        are ROI since launch of contract. All vaults start with pricePerFullShare = 1e18

        Returns a tuple[ROI, price_per_share] with the result.
        None is returned for first tuple entry if ROI could not be calculated.
        """
        price_per_full_share = self.ethereum.call_contract(
            contract_address=vault.evm_address,
            abi=self.ethereum.contracts.abi('YEARN_VAULT_V2'),  # Any vault ABI will do
            method_name='pricePerShare',
        )

        if vault.started is None:
            log.error(
                f'Failed to query ROI for vault {vault.evm_address}. Missing creation time.',
            )
            return None, price_per_full_share

        nominator = price_per_full_share - EXP18
        now_block_number = self.ethereum.get_latest_block_number()
        try:
            denominator = now_block_number - self.ethereum.etherscan.get_blocknumber_by_time(ts=vault.started, closest='before')  # noqa: E501
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query ROI for vault {vault.evm_address}. '
                f'Etherscan error {e!s}.',
            )
            return None, price_per_full_share
        return FVal(nominator) / FVal(denominator) * BLOCKS_PER_YEAR / EXP18, price_per_full_share

    def _get_single_addr_balance(
            self,
            defi_balances: dict[Asset, Balance],
            roi_cache: dict[str, FVal],
            pps_cache: dict[str, int],  # price per share
    ) -> dict[ChecksumEvmAddress, YearnVaultBalance]:
        result = {}
        with GlobalDBHandler().conn.read_ctx() as cursor:
            for asset, balance in defi_balances.items():
                if asset.is_evm_token() is False:
                    continue

                token = asset.resolve_to_evm_token()
                if token.protocol == YEARN_VAULTS_V2_PROTOCOL:
                    underlying = GlobalDBHandler.fetch_underlying_tokens(cursor, ethaddress_to_identifier(token.evm_address))  # noqa: E501
                    if underlying is None:
                        log.error(f'Found yearn asset {token} without underlying asset')
                        continue
                    underlying_token = EvmToken(ethaddress_to_identifier(underlying[0].address))
                    vault_address = token.evm_address

                    roi = roi_cache.get(vault_address)
                    pps = pps_cache.get(vault_address)
                    if roi is None:
                        roi, pps = self._calculate_vault_roi_and_pps(token)
                        if roi is not None:
                            roi_cache[vault_address] = roi
                            pps_cache[vault_address] = pps

                    underlying_balance = Balance(
                        amount=balance.amount * FVal(pps * 10**-token.get_decimals()),
                        usd_value=balance.usd_value,
                    )
                    result[token.evm_address] = YearnVaultBalance(
                        underlying_token=underlying_token,
                        vault_token=token,
                        underlying_value=underlying_balance,
                        vault_value=balance,
                        roi=roi,
                    )

        return result

    def get_balances(
            self,
            given_eth_balances: 'GIVEN_ETH_BALANCES',
    ) -> dict[ChecksumEvmAddress, dict[ChecksumEvmAddress, YearnVaultBalance]]:

        if isinstance(given_eth_balances, dict):
            defi_balances = given_eth_balances
        else:
            defi_balances = given_eth_balances()

        roi_cache: dict[str, FVal] = {}
        pps_cache: dict[str, int] = {}  # price per share cache
        result = {}

        for address, balances in defi_balances.items():
            vault_balances = self._get_single_addr_balance(balances.assets, roi_cache, pps_cache)
            if len(vault_balances) != 0:
                result[address] = vault_balances
        return result

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        ...

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        ...

    def deactivate(self) -> None:
        ...
