import logging
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.accounting.structures.defi import DefiEvent, DefiEventType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import MAX_BLOCKTIME_CACHE, ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_ALINK_V1,
    A_CRV_3CRV,
    A_CRV_3CRVSUSD,
    A_CRV_GUSD,
    A_CRV_RENWBTC,
    A_CRVP_DAIUSDCTBUSD,
    A_CRVP_DAIUSDCTTUSD,
    A_CRVP_RENWSBTC,
    A_DAI,
    A_GUSD,
    A_MUSD,
    A_PSLP,
    A_TUSD,
    A_USDC,
    A_USDT,
    A_WETH,
    A_YFI,
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
    CRV_ADAI_ASUSD,
    CRV_AETH,
    CRV_BBTC_SBTC,
    CRV_CDAI_CUSDC,
    CRV_DUSD,
    CRV_EURS,
    CRV_HBTC,
    CRV_HUSD,
    CRV_MUSD,
    CRV_OBTC_SBTC,
    CRV_TBTC_SBTC,
    CRV_USDN,
    CRV_USDP,
    CRV_UST,
)
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import (
    YEARN_VAULTS_V2_PROTOCOL,
    ChecksumEvmAddress,
    Price,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import address_to_bytes32, hexstr_to_int, ts_now

from .constants import BLOCKS_PER_YEAR, YEARN_VAULTS_PREFIX
from .db import add_yearn_vaults_events, get_yearn_vaults_events
from .structures import YearnVault, YearnVaultEvent

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import (
        GIVEN_DEFI_BALANCES,
        DefiProtocolBalances,
    )
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnVaultHistory(NamedTuple):
    events: list[YearnVaultEvent]
    profit_loss: Balance


class YearnVaultBalance(NamedTuple):
    underlying_token: CryptoAsset
    vault_token: CryptoAsset
    underlying_value: Balance
    vault_value: Balance
    roi: Optional[FVal]

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        if self.roi is not None:
            result['roi'] = self.roi.to_percentage(precision=2)
        else:
            del result['roi']

        return result


def get_usd_price_zero_if_error(
        asset: CryptoAsset,
        time: Timestamp,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> Price:
    """A special version of query_usd_price_zero_if_error using current price instead
    of historical token price for some assets.

    Since these assets are not supported by our price oracles we derive current
    price from the chain but without an archive node can't query old prices.

    TODO: MAke an issue about this
    This can be solved when we have an archive node.
    """
    inquirer = Inquirer()
    if (
        asset.identifier in inquirer.special_tokens or
        isinstance(asset, EvmToken) and asset.protocol == YEARN_VAULTS_V2_PROTOCOL
    ):
        return inquirer.find_usd_price(asset)

    return query_usd_price_zero_if_error(
        asset=asset,
        time=time,
        location=location,
        msg_aggregator=msg_aggregator,
    )


class YearnVaults(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()
        self.yearn_vaults = {
            'yyDAI+yUSDC+yUSDT+yTUSD': YearnVault(
                name='YCRV Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c')),
                underlying_token=A_CRVP_DAIUSDCTTUSD.resolve_to_evm_token(),
                token=A_YV1_DAIUSDCTTUSD.resolve_to_evm_token(),
            ),
            'yDAI': YearnVault(
                name='YDAI Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952')),
                underlying_token=A_DAI.resolve_to_evm_token(),
                token=A_YV1_DAI.resolve_to_evm_token(),
            ),
            'yWETH': YearnVault(
                name='YWETH Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xe1237aA7f535b0CC33Fd973D66cBf830354D16c7')),
                underlying_token=A_WETH.resolve_to_evm_token(),
                token=A_YV1_WETH.resolve_to_evm_token(),
            ),
            'yYFI': YearnVault(
                name='YYFI Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1')),
                underlying_token=A_YFI.resolve_to_evm_token(),
                token=A_YV1_YFI.resolve_to_evm_token(),
            ),
            'yaLINK': YearnVault(
                name='YALINK Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x29E240CFD7946BA20895a7a02eDb25C210f9f324')),
                underlying_token=A_ALINK_V1.resolve_to_evm_token(),
                token=A_YV1_ALINK.resolve_to_evm_token(),
            ),
            'yUSDT': YearnVault(
                name='YUSDT Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x2f08119C6f07c006695E079AAFc638b8789FAf18')),
                underlying_token=A_USDT.resolve_to_evm_token(),
                token=A_YV1_USDT.resolve_to_evm_token(),
            ),
            'yUSDC': YearnVault(
                name='YUSDC Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x597aD1e0c13Bfe8025993D9e79C69E1c0233522e')),
                underlying_token=A_USDC.resolve_to_evm_token(),
                token=A_YV1_USDC.resolve_to_evm_token(),
            ),
            'yTUSD': YearnVault(
                name='YTUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x37d19d1c4E1fa9DC47bD1eA12f742a0887eDa74a')),
                underlying_token=A_TUSD.resolve_to_evm_token(),
                token=A_YV1_TUSD.resolve_to_evm_token(),
            ),
            'yGUSD': YearnVault(
                name='GUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xec0d8D3ED5477106c6D4ea27D90a60e594693C90')),
                underlying_token=A_GUSD.resolve_to_evm_token(),
                token=A_YV1_GUSD.resolve_to_evm_token(),
            ),
            'yyDAI+yUSDC+yUSDT+yBUSD': YearnVault(
                name='YBCURVE Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x2994529C0652D127b7842094103715ec5299bBed')),
                underlying_token=A_CRVP_DAIUSDCTBUSD.resolve_to_evm_token(),
                token=A_YV1_DAIUSDCTBUSD.resolve_to_evm_token(),
            ),
            'ycrvRenWSBTC': YearnVault(
                name='YSRENCURVE Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6')),
                underlying_token=A_CRVP_RENWSBTC.resolve_to_evm_token(),
                token=A_YV1_RENWSBTC.resolve_to_evm_token(),
            ),
            'y3Crv': YearnVault(
                name='Y3CRV Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x9cA85572E6A3EbF24dEDd195623F188735A5179f')),
                underlying_token=A_CRV_3CRV.resolve_to_evm_token(),
                token=A_YV1_3CRV.resolve_to_evm_token(),
            ),
            'pSLP': YearnVault(
                name='pickling SushiSwap LP Token Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xbD17B1ce622d73bD438b9E658acA5996dc394b0d')),
                underlying_token=A_PSLP.resolve_to_evm_token(),
                token=A_YV1_PSLP.resolve_to_evm_token(),
            ),
            'yvcDAI+cUSDC': YearnVault(
                name='curve.fi/compound Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x629c759D1E83eFbF63d84eb3868B564d9521C129')),
                underlying_token=CRV_CDAI_CUSDC.resolve_to_evm_token(),
                token=A_YV1_CDAI_CUSD.resolve_to_evm_token(),
            ),
            'yvmusd3CRV': YearnVault(
                name='curve.fi/musd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x0FCDAeDFb8A7DfDa2e9838564c5A1665d856AFDF')),
                underlying_token=CRV_MUSD.resolve_to_evm_token(),
                token=A_YV1_MSUD_CRV.resolve_to_evm_token(),
            ),
            'yvgusd3CRV': YearnVault(
                name='curve.fi/gusd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xcC7E70A958917cCe67B4B87a8C30E6297451aE98')),
                underlying_token=A_CRV_GUSD.resolve_to_evm_token(),
                token=A_YV1_GUSD_CRV.resolve_to_evm_token(),
            ),
            'yveursCRV': YearnVault(
                name='curve.fi/eurs Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x98B058b2CBacF5E99bC7012DF757ea7CFEbd35BC')),
                underlying_token=CRV_EURS.resolve_to_evm_token(),
                token=A_YV1_EURS_CRV.resolve_to_evm_token(),
            ),
            'yvmUSD': YearnVault(
                name='mUSD Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xE0db48B4F71752C4bEf16De1DBD042B82976b8C7')),
                underlying_token=A_MUSD.resolve_to_evm_token(),
                token=A_YV1_MUSD_VAULT.resolve_to_evm_token(),
            ),
            'yvcrvRenWBTC': YearnVault(
                name='curve.fi/renbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765')),
                underlying_token=A_CRV_RENWBTC.resolve_to_evm_token(),
                token=A_YV1_RENBT_CRV.resolve_to_evm_token(),
            ),
            'yvusdn3CRV': YearnVault(
                name='curve.fi/usdn Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xFe39Ce91437C76178665D64d7a2694B0f6f17fE3')),
                underlying_token=CRV_USDN.resolve_to_evm_token(),
                token=A_YV1_USDN_CRV.resolve_to_evm_token(),
            ),
            'yvust3CRV': YearnVault(
                name='curve.fi/ust Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xF6C9E9AF314982A4b38366f4AbfAa00595C5A6fC')),
                underlying_token=CRV_UST.resolve_to_evm_token(),
                token=A_YV1_UST_CRV.resolve_to_evm_token(),
            ),
            'yvbBTC/sbtcCRV': YearnVault(
                name='curve.fi/bbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xA8B1Cb4ed612ee179BDeA16CCa6Ba596321AE52D')),
                underlying_token=CRV_BBTC_SBTC.resolve_to_evm_token(),
                token=A_YV1_BBTC_CRV.resolve_to_evm_token(),
            ),
            'yvtbtc/sbtcCrv': YearnVault(
                name='curve.fi/tbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x07FB4756f67bD46B748b16119E802F1f880fb2CC')),
                underlying_token=CRV_TBTC_SBTC.resolve_to_evm_token(),
                token=A_YV1_TBTC_CRV.resolve_to_evm_token(),
            ),
            'yvoBTC/sbtcCRV': YearnVault(
                name='curve.fi/obtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x7F83935EcFe4729c4Ea592Ab2bC1A32588409797')),
                underlying_token=CRV_OBTC_SBTC.resolve_to_evm_token(),
                token=A_YV1_OBTC_CRV.resolve_to_evm_token(),
            ),
            'yvhCRV': YearnVault(
                name='curve.fi/hbtc Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x46AFc2dfBd1ea0c0760CAD8262A5838e803A37e5')),
                underlying_token=CRV_HBTC.resolve_to_evm_token(),
                token=A_YV1_HBTC_CRV.resolve_to_evm_token(),
            ),
            'yvcrvPlain3andSUSD': YearnVault(
                name='curve.fi/susd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x5533ed0a3b83F70c3c4a1f69Ef5546D3D4713E44')),
                underlying_token=A_CRV_3CRVSUSD.resolve_to_evm_token(),
                token=A_YV1_SUSD_CRV.resolve_to_evm_token(),
            ),
            'yvhusd3CRV': YearnVault(
                name='curve.fi/husd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x39546945695DCb1c037C836925B355262f551f55')),
                underlying_token=CRV_HUSD.resolve_to_evm_token(),
                token=A_YV1_HUSD_CRV.resolve_to_evm_token(),
            ),
            'yvdusd3CRV': YearnVault(
                name='curve.fi/dusd Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x8e6741b456a074F0Bc45B8b82A755d4aF7E965dF')),
                underlying_token=CRV_DUSD.resolve_to_evm_token(),
                token=A_YV1_DUSD_3CRV.resolve_to_evm_token(),
            ),
            'yva3CRV': YearnVault(
                name='curve.fi/aave Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x03403154afc09Ce8e44C3B185C82C6aD5f86b9ab')),
                underlying_token=A_CRV_3CRV.resolve_to_evm_token(),
                token=A_YV1_A3CRV.resolve_to_evm_token(),
            ),
            'yvankrCRV': YearnVault(
                name='curve.fi/ankreth Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xE625F5923303f1CE7A43ACFEFd11fd12f30DbcA4')),
                underlying_token=CRV_AETH.resolve_to_evm_token(),
                token=A_YV1_ETH_ANKER.resolve_to_evm_token(),
            ),
            'yvsaCRV': YearnVault(
                name='curve.fi/saave Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0xBacB69571323575C6a5A3b4F9EEde1DC7D31FBc1')),
                underlying_token=CRV_ADAI_ASUSD.resolve_to_evm_token(),
                token=A_YV1_ASUSD_CRV.resolve_to_evm_token(),
            ),
            'yvusdp3CRV': YearnVault(
                name='curve.fi/usdp Vault',
                contract=self.ethereum.contracts.contract(string_to_evm_address('0x1B5eb1173D2Bf770e50F10410C9a96F7a8eB6e75')),
                underlying_token=CRV_USDP.resolve_to_evm_token(),
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
        denonimator = now_block_number - vault.contract.deployed_block
        return FVal(nominator) / FVal(denonimator) * BLOCKS_PER_YEAR / EXP18

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

    def _get_vault_deposit_events(
            self,
            vault: YearnVault,
            address: ChecksumEvmAddress,
            from_block: int,
            to_block: int,
    ) -> list[YearnVaultEvent]:
        """Get all deposit events of the underlying token to the vault
        May raise:
        - DeserializationError if tx_hash cannot be converted to bytes or mint_amount cannot be
          converted from hex string to int.
        """
        events: list[YearnVaultEvent] = []
        argument_filters = {'from': address, 'to': vault.contract.address}
        deposit_events = self.ethereum.get_logs(
            contract_address=vault.underlying_token.evm_address,
            abi=self.ethereum.contracts.erc20_abi,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )
        for deposit_event in deposit_events:
            timestamp = self.ethereum.get_event_timestamp(deposit_event)
            deposit_amount = token_normalized_value(
                token_amount=hexstr_to_int(deposit_event['data']),
                token=vault.underlying_token,
            )
            tx_hash = deserialize_evm_tx_hash(deposit_event['transactionHash'])
            tx_receipt = self.ethereum.get_transaction_receipt(tx_hash)
            deposit_index = deposit_event['logIndex']
            mint_amount = None
            for tx_log in tx_receipt['logs']:
                found_event = (
                    tx_log['topics'][0] == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' and  # noqa: E501
                    tx_log['topics'][1] == address_to_bytes32(ZERO_ADDRESS) and
                    tx_log['topics'][2] == address_to_bytes32(address)
                )
                if found_event:
                    # found the mint log
                    mint_amount = token_normalized_value(
                        token_amount=hexstr_to_int(tx_log['data']),
                        token=vault.token,
                    )

            if mint_amount is None:
                self.msg_aggregator.add_error(
                    f'Ignoring yearn deposit event with tx_hash {tx_hash.hex()} and log index '  # pylint: disable=no-member
                    f'{deposit_index} due to inability to find corresponding mint event',
                )
                continue

            deposit_usd_price = get_usd_price_zero_if_error(
                asset=vault.underlying_token,
                time=timestamp,
                location=f'yearn vault deposit {tx_hash.hex()}',  # pylint: disable=no-member
                msg_aggregator=self.msg_aggregator,
            )
            mint_usd_price = get_usd_price_zero_if_error(
                asset=vault.token,
                time=timestamp,
                location=f'yearn vault mint {tx_hash.hex()}',  # pylint: disable=no-member
                msg_aggregator=self.msg_aggregator,
            )
            events.append(YearnVaultEvent(
                event_type='deposit',
                block_number=deposit_event['blockNumber'],
                timestamp=timestamp,
                from_asset=vault.underlying_token,
                from_value=Balance(
                    amount=deposit_amount,
                    usd_value=deposit_amount * deposit_usd_price,
                ),
                to_asset=vault.token,
                to_value=Balance(
                    amount=mint_amount,
                    usd_value=mint_amount * mint_usd_price,
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=deposit_index,
                version=1,
            ))

        return events

    def _get_vault_withdraw_events(
            self,
            vault: YearnVault,
            address: ChecksumEvmAddress,
            from_block: int,
            to_block: int,
    ) -> list[YearnVaultEvent]:
        """Get all withdraw events of the underlying token to the vault
        May raise:
        - DeserializationError if tx_hash cannot be converted to bytes or burn_amount cannot be
          converted from hex string to int.
        """
        events: list[YearnVaultEvent] = []
        argument_filters = {'from': vault.contract.address, 'to': address}
        withdraw_events = self.ethereum.get_logs(
            contract_address=vault.underlying_token.evm_address,
            abi=self.ethereum.contracts.erc20_abi,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )
        for withdraw_event in withdraw_events:
            timestamp = self.ethereum.get_event_timestamp(withdraw_event)
            withdraw_amount = token_normalized_value(
                token_amount=hexstr_to_int(withdraw_event['data']),
                token=vault.token,
            )
            tx_hash = deserialize_evm_tx_hash(withdraw_event['transactionHash'])
            tx_receipt = self.ethereum.get_transaction_receipt(tx_hash)
            withdraw_index = withdraw_event['logIndex']
            burn_amount = None
            for tx_log in tx_receipt['logs']:
                found_event = (
                    tx_log['topics'][0] == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' and  # noqa: E501
                    tx_log['topics'][1] == address_to_bytes32(address) and
                    tx_log['topics'][2] == address_to_bytes32(ZERO_ADDRESS)
                )
                if found_event:
                    # found the burn log
                    burn_amount = token_normalized_value(
                        token_amount=hexstr_to_int(tx_log['data']),
                        token=vault.token,
                    )

            if burn_amount is None:
                self.msg_aggregator.add_error(
                    f'Ignoring yearn withdraw event with tx_hash {tx_hash.hex()} and log index '  # pylint: disable=no-member
                    f'{withdraw_index} due to inability to find corresponding burn event',
                )
                continue

            withdraw_usd_price = get_usd_price_zero_if_error(
                asset=vault.underlying_token,
                time=timestamp,
                location=f'yearn vault withdraw {tx_hash.hex()}',  # pylint: disable=no-member
                msg_aggregator=self.msg_aggregator,
            )
            burn_usd_price = get_usd_price_zero_if_error(
                asset=vault.token,
                time=timestamp,
                location=f'yearn vault withdraw {tx_hash.hex()}',  # pylint: disable=no-member
                msg_aggregator=self.msg_aggregator,
            )
            events.append(YearnVaultEvent(
                event_type='withdraw',
                block_number=withdraw_event['blockNumber'],
                timestamp=timestamp,
                from_asset=vault.token,
                from_value=Balance(
                    amount=burn_amount,
                    usd_value=burn_amount * burn_usd_price,
                ),
                to_asset=vault.underlying_token,
                to_value=Balance(
                    amount=withdraw_amount,
                    usd_value=withdraw_amount * withdraw_usd_price,
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=withdraw_index,
                version=1,
            ))

        return events

    def _process_vault_events(self, events: list[YearnVaultEvent]) -> Balance:
        """Process the events for a single vault and returns total profit/loss after all events"""
        total = Balance()
        profit_so_far = Balance()

        if len(events) < 2:
            return total

        for event in events:
            if event.event_type == 'deposit':
                total -= event.from_value
            else:  # withdraws
                profit_amount = total.amount + event.to_value.amount - profit_so_far.amount
                profit: Optional[Balance]
                if profit_amount >= 0:
                    usd_price = get_usd_price_zero_if_error(
                        asset=event.to_asset,
                        time=event.timestamp,
                        location=f'yearn vault event {event.tx_hash.hex()} processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far += profit
                else:
                    profit = None

                event.realized_pnl = profit
                total += event.to_value

        return total

    def get_vault_history(
            self,
            defi_balances: list['DefiProtocolBalances'],
            vault: YearnVault,
            address: ChecksumEvmAddress,
            from_block: int,
            to_block: int,
    ) -> Optional[YearnVaultHistory]:
        """Queries for vault events history and saves it in the database"""
        from_block = max(from_block, vault.contract.deployed_block)
        with self.database.conn.read_ctx() as cursor:
            last_query = self.database.get_used_query_range(
                cursor=cursor,
                name=f'{YEARN_VAULTS_PREFIX}_{vault.name.replace(" ", "_")}_{address}',
            )
            skip_query = last_query and to_block - last_query[1] < MAX_BLOCKTIME_CACHE

            events = get_yearn_vaults_events(cursor=cursor, address=address, vault=vault, msg_aggregator=self.msg_aggregator)  # noqa: E501
        if not skip_query:
            query_from_block = last_query[1] + 1 if last_query else from_block
            new_events = self._get_vault_deposit_events(vault, address, query_from_block, to_block)
            if len(events) == 0 and len(new_events) == 0:
                # After all events have been queried then also update the query range.
                # Even if no events are found for an address we need to remember the range
                with self.database.user_write() as write_cursor:
                    self.database.update_used_block_query_range(
                        write_cursor=write_cursor,
                        name=f'{YEARN_VAULTS_PREFIX}_{vault.name.replace(" ", "_")}_{address}',
                        from_block=from_block,
                        to_block=to_block,
                    )
                return None

            new_events.extend(
                self._get_vault_withdraw_events(vault, address, query_from_block, to_block),
            )
            # Now update the DB with the new events
            with self.database.user_write() as write_cursor:
                add_yearn_vaults_events(write_cursor, address, new_events)
            events.extend(new_events)

        # After all events have been queried then also update the query range.
        # Even if no events are found for an address we need to remember the range
        with self.database.user_write() as write_cursor:
            self.database.update_used_block_query_range(
                write_cursor=write_cursor,
                name=f'{YEARN_VAULTS_PREFIX}_{vault.name.replace(" ", "_")}_{address}',
                from_block=from_block,
                to_block=to_block,
            )
        if len(events) == 0:
            return None

        events.sort(key=lambda x: x.timestamp)
        total_pnl = self._process_vault_events(events)

        current_balance = None
        for balance in defi_balances:
            found_balance = (
                balance.protocol.name == 'yearn.finance • Vaults' and
                balance.base_balance.token_symbol == vault.token.symbol
            )
            if found_balance:
                current_balance = balance.underlying_balances[0].balance
                total_pnl += current_balance
                break

        # Due to the way we calculate usd prices for vaults we need to get the current
        # usd price of the actual pnl amount at this point
        if total_pnl.amount != ZERO:
            usd_price = get_usd_price_zero_if_error(
                asset=vault.underlying_token,
                time=ts_now(),
                location='yearn vault history',
                msg_aggregator=self.msg_aggregator,
            )
            total_pnl.usd_value = usd_price * total_pnl.amount

        return YearnVaultHistory(events=events, profit_loss=total_pnl)

    def get_history(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            addresses: list[ChecksumEvmAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,
    ) -> dict[ChecksumEvmAddress, dict[str, YearnVaultHistory]]:
        with self.history_lock:
            if reset_db_data is True:
                with self.database.user_write() as write_cursor:
                    self.database.delete_yearn_vaults_data(write_cursor=write_cursor, version=1)

            if isinstance(given_defi_balances, dict):
                defi_balances = given_defi_balances
            else:
                defi_balances = given_defi_balances()

            from_block = self.ethereum.get_blocknumber_by_time(from_timestamp, closest='before')
            to_block = self.ethereum.get_blocknumber_by_time(to_timestamp, closest='before')
            history: dict[ChecksumEvmAddress, dict[str, YearnVaultHistory]] = {}

            for address in addresses:
                history[address] = {}
                for vault in self.yearn_vaults.values():
                    vault_history = self.get_vault_history(
                        defi_balances=defi_balances.get(address, []),
                        vault=vault,
                        address=address,
                        from_block=from_block,
                        to_block=to_block,
                    )
                    if vault_history:
                        history[address][vault.name] = vault_history

                if len(history[address]) == 0:
                    del history[address]

        return history

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: list[ChecksumEvmAddress],
    ) -> list[DefiEvent]:
        """Gets the history events from maker vaults for accounting

            This is a premium only call. Check happens only in the API level.
        """
        if len(addresses) == 0:
            return []

        from_block = self.ethereum.get_blocknumber_by_time(from_timestamp, closest='before')
        to_block = self.ethereum.get_blocknumber_by_time(to_timestamp, closest='before')

        events = []
        for address in addresses:
            for vault in self.yearn_vaults.values():
                vault_history = self.get_vault_history(
                    defi_balances=[],
                    vault=vault,
                    address=address,
                    from_block=from_block,
                    to_block=to_block,
                )
                if vault_history is None:
                    continue

                if len(vault_history.events) != 0:
                    # process the vault's events to populate realized_pnl
                    self._process_vault_events(vault_history.events)

                for event in vault_history.events:
                    pnl = got_asset = got_balance = spent_asset = spent_balance = None
                    if event.event_type == 'deposit':
                        spent_asset = event.from_asset
                        spent_balance = event.from_value
                        got_asset = event.to_asset
                        got_balance = event.to_value
                    else:  # withdraw
                        spent_asset = event.from_asset
                        spent_balance = event.from_value
                        got_asset = event.to_asset
                        got_balance = event.to_value
                        if event.realized_pnl is not None:
                            pnl = [AssetBalance(asset=got_asset, balance=event.realized_pnl)]

                    events.append(DefiEvent(
                        timestamp=event.timestamp,
                        wrapped_event=event,
                        event_type=DefiEventType.YEARN_VAULTS_EVENT,
                        got_asset=got_asset,
                        got_balance=got_balance,
                        spent_asset=spent_asset,
                        spent_balance=spent_balance,
                        pnl=pnl,
                        # Depositing and withdrawing from a vault is not counted in
                        # cost basis. Assets were always yours, you did not rebuy them
                        count_spent_got_cost_basis=False,
                        tx_hash=event.tx_hash,
                    ))

        return events

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        with self.database.user_write() as cursor:
            self.database.delete_yearn_vaults_data(write_cursor=cursor, version=1)
