import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_crypto_asset_by_symbol
from rotkehlchen.chain.ethereum.defi.price import handle_defi_price_query
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_USDC
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer, get_underlying_asset_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


PROTOCOLS_QUERY_NUM = 40  # number of protocols to query in a single call
KNOWN_ZERION_PROTOCOL_NAMES = (
    'Curve • Vesting',
    'Curve • Liquidity Gauges',
    'Curve • Vote Escrowed CRV',
    'ygov.finance (v1)',
    'ygov.finance (v2)',
    'Swerve • Liquidity Gauges',
    'Pickle Finance • Farms',
    'Pickle Finance • Staking',
    'Aave • Staking',
    'C.R.E.A.M. • Staking',
    'Compound Governance',
    'zlot.finance',
    'FinNexus',
    'Pickle Finance',
    'DODO',
    'Berezka',
    'bZx',
    'bZx • Staking',
    'bZx • Vested Staking',
    'C.R.E.A.M.',
    'Swerve',
    'SashimiSwap',
    'Harvest',
    'Harvest • Profit Sharing',
    'KIMCHI',
    'SushiSwap',
    'SushiSwap • Staking',
    'Nexus Mutual',
    'Mooniswap',
    'Matic',
    'Aragon',
    'Melon',
    'Enzyme',
    'yearn.finance • Vaults',
    'Yearn Token Vaults',
    'KeeperDAO',
    'mStable',
    'mStable • Staking',
    'mStable V2',
    'KyberDAO',
    'DDEX • Spot',
    'DDEX • Margin',
    'DDEX • Lending',
    'Ampleforth',
    'Maker Governance',
    'Gnosis Protocol',
    'Chi Gastoken by 1inch',
    '1inch Liquidity Protocol',
    '1inch LP • Staking',
    'Idle • Risk-Adjusted',
    'Aave • Uniswap Market',
    'Uniswap V2',
    'PieDAO',
    'PieDAO ExperiPies',
    'Multi-Collateral Dai',
    'Bancor',
    'Bancor • Locked BNT',
    'Bancor • Liquidity Protection',
    'DeFi Money Market',
    'TokenSets',
    '0x Staking',
    'Uniswap V1',
    'Synthetix',
    'PoolTogether',
    'PoolTogether V3',
    'Dai Savings Rate',
    'Chai',
    'iearn.finance (v3)',
    'iearn.finance (v2)',
    'Idle',
    'Idle • Early Rewards',
    'dYdX',
    'Curve',
    'Compound',
    'Balancer',
    'Aave',
    'SnowSwap',
    'Aave V2',
    'Aave V2 • Variable Debt',
    'Aave V2 • Stable Debt',
    'Mushrooms Finance',
    'Mushrooms Finance • Staking',
    'Akropolis • AKRO Staking',
    'Akropolis • ADEL Staking',
    'Liquity',
    'Alpha Homora',
    'Alpha Homora V2',
    'Stake DAO',
    'Saddle',
    'Reflexer',
    'Cometh • Tube',
    'Cometh • Staking',
    'Livepeer',
    'Cozy',
    'Cozy • Yearn',
    'Cozy • Compound',
    'Unagii',
    'Origin Protocol • OGN Staking',
    'TimeWarp • Staking',
    'Gelato Network • Locked GEL',
)
WEIGHTED_NODES_WITH_HIGH_GAS_LIMIT = (
    WeightedNode(
        node_info=NodeName(
            name='1inch',
            endpoint='https://web3.1inch.exchange',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        weight=FVal(0.15),
        active=True,
    ),
)


def _is_token_non_standard(symbol: str, address: ChecksumEvmAddress) -> bool:
    """ignore some assets we do not query directly as token balances

    UNI-V2 is queried from the uniswap pairs code
    pDAI is useless since the hack so ignore it
    """
    if symbol in {'UNI-V2', 'pDAI'}:
        return True

    return address in (
        '0xCb2286d9471cc185281c4f763d34A962ED212962',  # Sushi LP token
        ETH_SPECIAL_ADDRESS,
    )


def _handle_pooltogether(normalized_balance: FVal, token_name: str) -> DefiBalance | None:
    """Special handling for pooltogether

    https://github.com/rotki/rotki/issues/1429
    """
    if 'DAI' in token_name:
        dai_price = Inquirer.find_usd_price(A_DAI)
        return DefiBalance(
            token_address=string_to_evm_address('0x49d716DFe60b37379010A75329ae09428f17118d'),
            token_name='Pool Together DAI token',
            token_symbol='plDAI',
            balance=Balance(
                amount=normalized_balance,
                usd_value=normalized_balance * dai_price,
            ),
        )
    if 'USDC' in token_name:
        usdc_price = Inquirer.find_usd_price(A_USDC)
        return DefiBalance(
            token_address=string_to_evm_address('0xBD87447F48ad729C5c4b8bcb503e1395F62e8B98'),
            token_name='Pool Together USDC token',
            token_symbol='plUSDC',
            balance=Balance(
                amount=normalized_balance,
                usd_value=normalized_balance * usdc_price,
            ),
        )
    # else
    return None


# supported zerion adapter address
ZERION_ADAPTER_ADDRESS = string_to_evm_address('0x06FE76B2f432fdfEcAEf1a7d4f6C3d41B5861672')


class ZerionSDK:
    """Adapter for the Zerion DeFi SDK https://github.com/zeriontech/defi-sdk"""

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            msg_aggregator: 'MessagesAggregator',
            database: 'DBHandler',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.msg_aggregator = msg_aggregator
        self.contract = EvmContract(
            address=ZERION_ADAPTER_ADDRESS,
            abi=self.ethereum.contracts.abi('ZERION_ADAPTER'),
            deployed_block=1586199170,
        )
        self.database = database
        self.protocol_names: list[str] | None = None

    def _get_protocol_names(self) -> list[str]:
        if self.protocol_names is not None:
            return self.protocol_names

        try:
            protocol_names = self.contract.call(
                node_inquirer=self.ethereum,
                method_name='getProtocolNames',
                arguments=[],
            )
        except RemoteError as e:
            log.warning(
                f'Failed to query zerion adapter contract for protocol names due to {e!s}. '
                f'Falling back to known list of names.',
            )
            return list(KNOWN_ZERION_PROTOCOL_NAMES)

        self.protocol_names = protocol_names
        return protocol_names

    def _query_chain_for_all_balances(self, account: ChecksumEvmAddress) -> list:
        if (own_node_info := self.ethereum.get_own_node_info()) is not None:
            try:
                # In this case we don't care about the gas limit
                own_node = WeightedNode(
                    node_info=own_node_info,
                    active=True,
                    weight=ONE,
                )
                return self.contract.call(  # this may raise
                    node_inquirer=self.ethereum,
                    method_name='getBalances',
                    arguments=[account],
                    call_order=(own_node, ) + WEIGHTED_NODES_WITH_HIGH_GAS_LIMIT,
                )
            except RemoteError:
                log.warning(
                    'Failed to query zerionsdk balances with own node. Falling '
                    'back to multiple calls to getProtocolBalances',
                )

        # but if we are not connected to our own node the zerion sdk get balances call
        # has unfortunately crossed the default limits of almost all open nodes apart from 1inch
        # https://github.com/rotki/rotki/issues/1969
        # So now we get all supported protocols and query in batches
        protocol_names = self._get_protocol_names()
        result = []
        protocol_chunks: list[list[str]] = list(get_chunks(
            list(protocol_names),
            n=PROTOCOLS_QUERY_NUM,
        ))
        for protocol_names in protocol_chunks:
            contract_result = self.contract.call(
                node_inquirer=self.ethereum,
                method_name='getProtocolBalances',
                arguments=[account, protocol_names],
            )
            if len(contract_result) == 0:
                continue
            result.extend(contract_result)

        return result

    def all_balances_for_account(self, account: ChecksumEvmAddress) -> list[DefiProtocolBalances]:
        """Calls the contract's getBalances() to get all protocol balances for account

        https://docs.zerion.io/smart-contracts/adapterregistry-v3#getbalances
        """
        result = self._query_chain_for_all_balances(account=account)
        protocol_balances = []
        for entry in result:
            protocol = DefiProtocol(
                name=entry[0][0],
                description=entry[0][1],
                url=entry[0][2],
                version=entry[0][4],
            )
            for adapter_balance in entry[1]:
                balance_type = adapter_balance[0][1]  # can be either 'Asset' or 'Debt'
                for balances in adapter_balance[1]:
                    underlying_balances = []
                    try:
                        base_balance = self._get_single_balance(protocol.name, balances[0])
                    except DeserializationError:
                        log.error(
                            f'Deserialization error trying to get base balance'
                            f'in {protocol.name}. Skipping {balances[0]}',
                        )
                        continue

                    for balance in balances[1]:
                        try:
                            defi_balance = self._get_single_balance(protocol.name, balance)
                            underlying_balances.append(defi_balance)
                        except DeserializationError:
                            log.error(
                                f'Deserialization error trying to get single balance '
                                f'in {protocol.name}. {balances[0]}'
                                f' Skipping underlying balance',
                            )
                            # In this case we just skip the underlying balance
                            continue

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
            entry: tuple[tuple[str, str, str, int], int],
    ) -> DefiBalance:
        """
        This method can raise DeserializationError while deserializing the token address
        or handling the specific protocol.
        """
        metadata = entry[0]
        balance_value = entry[1]
        decimals = metadata[3]
        normalized_value = token_normalized_value_decimals(balance_value, decimals)
        token_symbol = metadata[2]
        token_address = deserialize_evm_address(metadata[0])
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
            identifier = ethaddress_to_identifier(token_address)
            token = EvmToken(identifier)
            usd_price = Inquirer.find_usd_price(token)
        except (UnknownAsset, UnsupportedAsset):
            if not _is_token_non_standard(token_symbol, token_address):
                self.msg_aggregator.add_warning(
                    f'Unsupported asset {token_symbol} with address '
                    f'{token_address} encountered during DeFi protocol queries',
                )
            usd_price = ZERO_PRICE

        usd_value = normalized_value * usd_price
        return DefiBalance(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            balance=Balance(normalized_value, usd_value=usd_value),
        )

    def handle_protocols(
            self,
            protocol_name: str,
            token_symbol: str,
            normalized_balance: FVal,
            token_address: str,
            token_name: str,
    ) -> DefiBalance | None:
        """Special handling for price for token/protocols which are easier to do onchain
        or need some kind of special treatment.
        This method can raise DeserializationError
        """
        if protocol_name == 'PoolTogether':
            result = _handle_pooltogether(normalized_balance, token_name)
            if result is not None:
                return result

        asset = get_crypto_asset_by_symbol(token_symbol, chain_id=ChainID.ETHEREUM)
        if asset is None:
            return None

        try:
            token = asset.resolve_to_evm_token()
        except (UnknownAsset, WrongAssetType):
            return None
        underlying_asset_price, _ = get_underlying_asset_price(token)
        usd_price = handle_defi_price_query(self.ethereum, token, underlying_asset_price)
        if usd_price is None:
            return None

        return DefiBalance(
            token_address=deserialize_evm_address(token_address),
            token_name=token_name,
            token_symbol=token_symbol,
            balance=Balance(normalized_balance, usd_value=normalized_balance * usd_price),
        )
