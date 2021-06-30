# flake8: noqa

import json
import os
from typing import Any, Dict, List, Optional

from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address

MAX_BLOCKTIME_CACHE = 250  # 55 mins with 13 secs avg block time
ZERO_ADDRESS = string_to_ethereum_address('0x0000000000000000000000000000000000000000')
AAVE_ETH_RESERVE_ADDRESS = string_to_ethereum_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')


class EthereumConstants():
    __instance = None
    contracts: Dict[str, Dict[str, Any]] = {}
    abi_entries: Dict[str, List[Dict[str, Any]]] = {}

    def __new__(cls) -> 'EthereumConstants':
        if EthereumConstants.__instance is not None:
            return EthereumConstants.__instance  # type: ignore

        EthereumConstants.__instance = object.__new__(cls)

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        with open(os.path.join(dir_path, 'data', 'eth_contracts.json'), 'r') as f:
            contracts = json.loads(f.read())

        with open(os.path.join(dir_path, 'data', 'eth_abi.json'), 'r') as f:
            abi_entries = json.loads(f.read())

        EthereumConstants.__instance.contracts = contracts
        EthereumConstants.__instance.abi_entries = abi_entries
        return EthereumConstants.__instance

    @staticmethod
    def get() -> Dict[str, Dict[str, Any]]:
        return EthereumConstants().contracts

    @staticmethod
    def contract_or_none(name: str) -> Optional[EthereumContract]:
        """Gets details of an ethereum contract from the contracts json file

        Returns None if missing
        """
        contract = EthereumConstants().contracts.get(name, None)
        if contract is None:
            return None

        return EthereumContract(
            address=contract['address'],
            abi=contract['abi'],
            deployed_block=contract['deployed_block'],
        )

    @staticmethod
    def contract(name: str) -> EthereumContract:
        """Gets details of an ethereum contract from the contracts json file

        Missing contract is an error
        """
        contract = EthereumConstants().contract_or_none(name)
        assert contract, f'No contract data for {name} found'
        return contract

    @staticmethod
    def abi_or_none(name: str) -> Optional[List[Dict[str, Any]]]:
        """Gets abi of an ethereum contract from the abi json file

        Returns None if missing
        """
        return EthereumConstants().abi_entries.get(name, None)

    @staticmethod
    def abi(name: str) -> List[Dict[str, Any]]:
        abi = EthereumConstants().abi_or_none(name)
        assert abi, f'No abi for {name} found'
        return abi

# Latest contract addresses are in the makerdao changelog. These values are taken from here:
# https://changelog.makerdao.com/releases/mainnet/1.2.4/contracts.json


MAKERDAO_DAI_JOIN = EthereumConstants().contract('MAKERDAO_DAI_JOIN')
MAKERDAO_CDP_MANAGER = EthereumConstants().contract('MAKERDAO_CDP_MANAGER')
MAKERDAO_GET_CDPS = EthereumConstants().contract('MAKERDAO_GET_CDPS')
MAKERDAO_PROXY_REGISTRY = EthereumConstants().contract('MAKERDAO_PROXY_REGISTRY')
MAKERDAO_SPOT = EthereumConstants().contract('MAKERDAO_SPOT')
MAKERDAO_POT = EthereumConstants().contract('MAKERDAO_POT')
MAKERDAO_VAT = EthereumConstants().contract('MAKERDAO_VAT')
MAKERDAO_ETH_A_JOIN = EthereumConstants().contract('MAKERDAO_ETH_A_JOIN')
MAKERDAO_ETH_B_JOIN = EthereumConstants().contract('MAKERDAO_ETH_B_JOIN')
MAKERDAO_ETH_C_JOIN = EthereumConstants().contract('MAKERDAO_ETH_C_JOIN')
MAKERDAO_BAT_A_JOIN = EthereumConstants().contract('MAKERDAO_BAT_A_JOIN')
MAKERDAO_USDC_A_JOIN = EthereumConstants().contract('MAKERDAO_USDC_A_JOIN')
MAKERDAO_USDC_B_JOIN = EthereumConstants().contract('MAKERDAO_USDC_B_JOIN')
MAKERDAO_USDT_A_JOIN = EthereumConstants().contract('MAKERDAO_USDT_A_JOIN')
MAKERDAO_WBTC_A_JOIN = EthereumConstants().contract('MAKERDAO_WBTC_A_JOIN')
MAKERDAO_KNC_A_JOIN = EthereumConstants().contract('MAKERDAO_KNC_A_JOIN')
MAKERDAO_MANA_A_JOIN = EthereumConstants().contract('MAKERDAO_MANA_A_JOIN')
MAKERDAO_TUSD_A_JOIN = EthereumConstants().contract('MAKERDAO_TUSD_A_JOIN')
MAKERDAO_ZRX_A_JOIN = EthereumConstants().contract('MAKERDAO_ZRX_A_JOIN')
MAKERDAO_PAXUSD_A_JOIN = EthereumConstants().contract('MAKERDAO_PAXUSD_A_JOIN')
MAKERDAO_COMP_A_JOIN = EthereumConstants().contract('MAKERDAO_COMP_A_JOIN')
MAKERDAO_LRC_A_JOIN = EthereumConstants().contract('MAKERDAO_LRC_A_JOIN')
MAKERDAO_LINK_A_JOIN = EthereumConstants().contract('MAKERDAO_LINK_A_JOIN')
MAKERDAO_BAL_A_JOIN = EthereumConstants().contract('MAKERDAO_BAL_A_JOIN')
MAKERDAO_YFI_A_JOIN = EthereumConstants().contract('MAKERDAO_YFI_A_JOIN')
MAKERDAO_GUSD_A_JOIN = EthereumConstants().contract('MAKERDAO_GUSD_A_JOIN')
MAKERDAO_UNI_A_JOIN = EthereumConstants().contract('MAKERDAO_UNI_A_JOIN')
MAKERDAO_RENBTC_A_JOIN = EthereumConstants().contract('MAKERDAO_RENBTC_A_JOIN')
MAKERDAO_AAVE_A_JOIN = EthereumConstants().contract('MAKERDAO_AAVE_A_JOIN')

MAKERDAO_CAT = EthereumConstants().contract('MAKERDAO_CAT')
MAKERDAO_JUG = EthereumConstants().contract('MAKERDAO_JUG')

YEARN_YCRV_VAULT = EthereumConstants().contract('YEARN_YCRV_VAULT')
YEARN_3CRV_VAULT = EthereumConstants().contract('YEARN_3CRV_VAULT')
YEARN_DAI_VAULT = EthereumConstants().contract('YEARN_DAI_VAULT')
YEARN_WETH_VAULT = EthereumConstants().contract('YEARN_WETH_VAULT')
YEARN_YFI_VAULT = EthereumConstants().contract('YEARN_YFI_VAULT')
YEARN_ALINK_VAULT = EthereumConstants().contract('YEARN_ALINK_VAULT')
YEARN_USDT_VAULT = EthereumConstants().contract('YEARN_USDT_VAULT')
YEARN_USDC_VAULT = EthereumConstants().contract('YEARN_USDC_VAULT')
YEARN_TUSD_VAULT = EthereumConstants().contract('YEARN_TUSD_VAULT')
YEARN_GUSD_VAULT = EthereumConstants().contract('YEARN_GUSD_VAULT')
YEARN_BCURVE_VAULT = EthereumConstants().contract('YEARN_BCURVE_VAULT')
YEARN_SRENCURVE_VAULT = EthereumConstants().contract('YEARN_SRENCURVE_VAULT')

ETH_SCAN = EthereumConstants().contract('ETH_SCAN')
ETH_MULTICALL = EthereumConstants().contract('ETH_MULTICALL')
ETH_MULTICALL_2 = EthereumConstants().contract('ETH_MULTICALL_2')


AAVE_LENDING_POOL = EthereumConstants().contract('AAVE_LENDING_POOL')

ATOKEN_ABI = EthereumConstants.abi('ATOKEN')
ZERION_ABI = EthereumConstants.abi('ZERION_ADAPTER')
CTOKEN_ABI = EthereumConstants.abi('CTOKEN')
ERC20TOKEN_ABI = EthereumConstants.abi('ERC20_TOKEN')
FARM_ASSET_ABI = EthereumConstants.abi('FARM_ASSET')
UNISWAP_V2_LP_ABI = EthereumConstants.abi('UNISWAP_V2_LP')
CURVE_POOL_ABI = EthereumConstants.abi('CURVE_POOL')
YEARN_VAULT_V2_ABI = EthereumConstants.abi('YEARN_VAULT_V2')

YEARN_VAULTS_PREFIX = 'yearn_vaults_events'
YEARN_VAULTS_V2_PREFIX = 'yearn_vaults_v2_events'
