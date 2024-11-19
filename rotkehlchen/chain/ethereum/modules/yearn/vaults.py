import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_YV1_3CRV,
    A_YV1_A3CRV,
    A_YV1_ALINK,
    A_YV1_ASUSD_CRV,
    A_YV1_BBTC_CRV,
    A_YV1_CDAI_CUSD,
    A_YV1_DAI,
    A_YV1_DAIUSDCTBUSD,
    A_YV1_DAIUSDCTTUSD,
    A_YV1_DUSD_3CRV,
    A_YV1_ETH_ANKER,
    A_YV1_EURS_CRV,
    A_YV1_GUSD,
    A_YV1_GUSD_CRV,
    A_YV1_HBTC_CRV,
    A_YV1_HUSD_CRV,
    A_YV1_MSUD_CRV,
    A_YV1_MUSD_VAULT,
    A_YV1_OBTC_CRV,
    A_YV1_PSLP,
    A_YV1_RENBT_CRV,
    A_YV1_RENWSBTC,
    A_YV1_SUSD_CRV,
    A_YV1_TBTC_CRV,
    A_YV1_TUSD,
    A_YV1_USDC,
    A_YV1_USDN_CRV,
    A_YV1_USDP_CRV,
    A_YV1_USDT,
    A_YV1_UST_CRV,
    A_YV1_WETH,
    A_YV1_YFI,
)
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.interfaces import EthereumModule

from .constants import BLOCKS_PER_YEAR
from .structures import YearnVault

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import (
        GIVEN_DEFI_BALANCES,
        DefiProtocolBalances,
    )
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnVaultBalance(NamedTuple):
    underlying_token: CryptoAsset
    vault_token: CryptoAsset
    underlying_value: Balance
    vault_value: Balance
    roi: FVal | None

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        if self.roi is not None:
            result['roi'] = self.roi.to_percentage(precision=2)
        else:
            del result['roi']

        return result


class YearnVaults(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.yearn_vaults = {
            'yyDAI+yUSDC+yUSDT+yTUSD': YearnVault(
                name='YCRV Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c')),
                token=A_YV1_DAIUSDCTTUSD.resolve_to_evm_token(),
            ),
            'yDAI': YearnVault(
                name='YDAI Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952')),
                token=A_YV1_DAI.resolve_to_evm_token(),
            ),
            'yWETH': YearnVault(
                name='YWETH Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xe1237aA7f535b0CC33Fd973D66cBf830354D16c7')),
                token=A_YV1_WETH.resolve_to_evm_token(),
            ),
            'yYFI': YearnVault(
                name='YYFI Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1')),
                token=A_YV1_YFI.resolve_to_evm_token(),
            ),
            'yaLINK': YearnVault(
                name='YALINK Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x29E240CFD7946BA20895a7a02eDb25C210f9f324')),
                token=A_YV1_ALINK.resolve_to_evm_token(),
            ),
            'yUSDT': YearnVault(
                name='YUSDT Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x2f08119C6f07c006695E079AAFc638b8789FAf18')),
                token=A_YV1_USDT.resolve_to_evm_token(),
            ),
            'yUSDC': YearnVault(
                name='YUSDC Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x597aD1e0c13Bfe8025993D9e79C69E1c0233522e')),
                token=A_YV1_USDC.resolve_to_evm_token(),
            ),
            'yTUSD': YearnVault(
                name='YTUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x37d19d1c4E1fa9DC47bD1eA12f742a0887eDa74a')),
                token=A_YV1_TUSD.resolve_to_evm_token(),
            ),
            'yGUSD': YearnVault(
                name='GUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xec0d8D3ED5477106c6D4ea27D90a60e594693C90')),
                token=A_YV1_GUSD.resolve_to_evm_token(),
            ),
            'yyDAI+yUSDC+yUSDT+yBUSD': YearnVault(
                name='YBCURVE Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x2994529C0652D127b7842094103715ec5299bBed')),
                token=A_YV1_DAIUSDCTBUSD.resolve_to_evm_token(),
            ),
            'ycrvRenWSBTC': YearnVault(
                name='YSRENCURVE Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6')),
                token=A_YV1_RENWSBTC.resolve_to_evm_token(),
            ),
            'y3Crv': YearnVault(
                name='Y3CRV Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x9cA85572E6A3EbF24dEDd195623F188735A5179f')),
                token=A_YV1_3CRV.resolve_to_evm_token(),
            ),
            'pSLP': YearnVault(
                name='pickling SushiSwap LP Token Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xbD17B1ce622d73bD438b9E658acA5996dc394b0d')),
                token=A_YV1_PSLP.resolve_to_evm_token(),
            ),
            'yvcDAI+cUSDC': YearnVault(
                name='curve.fi/compound Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x629c759D1E83eFbF63d84eb3868B564d9521C129')),
                token=A_YV1_CDAI_CUSD.resolve_to_evm_token(),
            ),
            'yvmusd3CRV': YearnVault(
                name='curve.fi/musd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x0FCDAeDFb8A7DfDa2e9838564c5A1665d856AFDF')),
                token=A_YV1_MSUD_CRV.resolve_to_evm_token(),
            ),
            'yvgusd3CRV': YearnVault(
                name='curve.fi/gusd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xcC7E70A958917cCe67B4B87a8C30E6297451aE98')),
                token=A_YV1_GUSD_CRV.resolve_to_evm_token(),
            ),
            'yveursCRV': YearnVault(
                name='curve.fi/eurs Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x98B058b2CBacF5E99bC7012DF757ea7CFEbd35BC')),
                token=A_YV1_EURS_CRV.resolve_to_evm_token(),
            ),
            'yvmUSD': YearnVault(
                name='mUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xE0db48B4F71752C4bEf16De1DBD042B82976b8C7')),
                token=A_YV1_MUSD_VAULT.resolve_to_evm_token(),
            ),
            'yvcrvRenWBTC': YearnVault(
                name='curve.fi/renbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765')),
                token=A_YV1_RENBT_CRV.resolve_to_evm_token(),
            ),
            'yvusdn3CRV': YearnVault(
                name='curve.fi/usdn Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xFe39Ce91437C76178665D64d7a2694B0f6f17fE3')),
                token=A_YV1_USDN_CRV.resolve_to_evm_token(),
            ),
            'yvust3CRV': YearnVault(
                name='curve.fi/ust Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xF6C9E9AF314982A4b38366f4AbfAa00595C5A6fC')),
                token=A_YV1_UST_CRV.resolve_to_evm_token(),
            ),
            'yvbBTC/sbtcCRV': YearnVault(
                name='curve.fi/bbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xA8B1Cb4ed612ee179BDeA16CCa6Ba596321AE52D')),
                token=A_YV1_BBTC_CRV.resolve_to_evm_token(),
            ),
            'yvtbtc/sbtcCrv': YearnVault(
                name='curve.fi/tbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x07FB4756f67bD46B748b16119E802F1f880fb2CC')),
                token=A_YV1_TBTC_CRV.resolve_to_evm_token(),
            ),
            'yvoBTC/sbtcCRV': YearnVault(
                name='curve.fi/obtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x7F83935EcFe4729c4Ea592Ab2bC1A32588409797')),
                token=A_YV1_OBTC_CRV.resolve_to_evm_token(),
            ),
            'yvhCRV': YearnVault(
                name='curve.fi/hbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x46AFc2dfBd1ea0c0760CAD8262A5838e803A37e5')),
                token=A_YV1_HBTC_CRV.resolve_to_evm_token(),
            ),
            'yvcrvPlain3andSUSD': YearnVault(
                name='curve.fi/susd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5533ed0a3b83F70c3c4a1f69Ef5546D3D4713E44')),
                token=A_YV1_SUSD_CRV.resolve_to_evm_token(),
            ),
            'yvhusd3CRV': YearnVault(
                name='curve.fi/husd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x39546945695DCb1c037C836925B355262f551f55')),
                token=A_YV1_HUSD_CRV.resolve_to_evm_token(),
            ),
            'yvdusd3CRV': YearnVault(
                name='curve.fi/dusd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x8e6741b456a074F0Bc45B8b82A755d4aF7E965dF')),
                token=A_YV1_DUSD_3CRV.resolve_to_evm_token(),
            ),
            'yva3CRV': YearnVault(
                name='curve.fi/aave Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x03403154afc09Ce8e44C3B185C82C6aD5f86b9ab')),
                token=A_YV1_A3CRV.resolve_to_evm_token(),
            ),
            'yvankrCRV': YearnVault(
                name='curve.fi/ankreth Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xE625F5923303f1CE7A43ACFEFd11fd12f30DbcA4')),
                token=A_YV1_ETH_ANKER.resolve_to_evm_token(),
            ),
            'yvsaCRV': YearnVault(
                name='curve.fi/saave Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xBacB69571323575C6a5A3b4F9EEde1DC7D31FBc1')),
                token=A_YV1_ASUSD_CRV.resolve_to_evm_token(),
            ),
            'yvusdp3CRV': YearnVault(
                name='curve.fi/usdp Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x1B5eb1173D2Bf770e50F10410C9a96F7a8eB6e75')),
                token=A_YV1_USDP_CRV.resolve_to_evm_token(),
            ),
        }

    def _calculate_vault_roi(self, vault: YearnVault) -> FVal:
        """
        getPricePerFullShare A @ block X
        getPricePerFullShare B @ block Y

        (A-B / X-Y) * blocksPerYear (2425846)

        So the numbers you see displayed on http://yearn.fi/vaults
        are ROI since launch of contract. All vaults start with pricePerFullShare = 1e18
        """
        now_block_number = self.ethereum.get_latest_block_number()
        price_per_full_share = self.ethereum.call_contract(
            contract_address=vault.contract.address,
            abi=self.ethereum.contracts.contract(string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952')).abi,  # Any vault ABI will do  # noqa: E501
            method_name='getPricePerFullShare',
        )
        nominator = price_per_full_share - EXP18
        denominator = now_block_number - vault.contract.deployed_block
        return FVal(nominator) / FVal(denominator) * BLOCKS_PER_YEAR / EXP18

    def _get_single_addr_balance(
            self,
            defi_balances: list['DefiProtocolBalances'],
            roi_cache: dict[str, FVal],
    ) -> dict[str, YearnVaultBalance]:
        result = {}
        for balance in defi_balances:
            if balance.protocol.name == 'yearn.finance • Vaults':
                underlying_address = balance.underlying_balances[0].token_address
                vault_symbol = balance.base_balance.token_symbol
                vault_address = balance.base_balance.token_address
                vault = self.yearn_vaults.get(vault_symbol, None)
                if vault is None:
                    self.msg_aggregator.add_warning(
                        f'Found balance for unsupported yearn vault {vault_symbol}',
                    )
                    continue

                try:
                    underlying_asset = EvmToken(ethaddress_to_identifier(underlying_address))
                    vault_asset = EvmToken(ethaddress_to_identifier(vault_address))
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown asset {e.identifier} for yearn vault entry',
                    )
                    continue

                roi = roi_cache.get(underlying_asset.identifier, None)
                if roi is None:
                    roi = self._calculate_vault_roi(vault)
                    roi_cache[underlying_asset.identifier] = roi

                result[vault.name] = YearnVaultBalance(
                    underlying_token=underlying_asset,
                    vault_token=vault_asset,
                    underlying_value=balance.underlying_balances[0].balance,
                    vault_value=balance.base_balance.balance,
                    roi=roi,
                )

        return result

    def get_balances(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
    ) -> dict[ChecksumEvmAddress, dict[str, YearnVaultBalance]]:
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        roi_cache: dict[str, FVal] = {}
        result = {}
        for address, balances in defi_balances.items():
            vault_balances = self._get_single_addr_balance(balances, roi_cache)
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
