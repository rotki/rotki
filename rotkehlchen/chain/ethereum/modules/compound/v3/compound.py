import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.constants import ETH_MANTISSA
from rotkehlchen.chain.ethereum.modules.compound.utils import CompoundBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_ETH_BALANCES
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CompoundV3:
    def __init__(self, ethereum_inquirer: 'EthereumInquirer', database: 'DBHandler'):
        self.database = database
        self.ethereum = ethereum_inquirer

    def _get_v3_interest_rates(
            self,
            tokens_and_types: dict['ChecksumEvmAddress', list[BalanceType]],
    ) -> defaultdict['ChecksumEvmAddress', defaultdict[BalanceType, FVal]]:
        """Make multicalls to the compound v3 tokens to get the lending and borrowing interest
        rates from the contracts. First get the utilization for each token and then pass it in the
        supply/borrow rate calls. Returns them as a dict of asset -> balance type -> rate."""
        rates: defaultdict[ChecksumEvmAddress, defaultdict[BalanceType, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501
        token_contract = EvmContract(
            address=ZERO_ADDRESS,  # not used here
            abi=self.ethereum.contracts.abi('COMPOUND_V3_TOKEN'),
            deployed_block=0,  # not used here
        )
        calls = [  # prepare calls for utilizations of tokens
            (token_address, token_contract.encode(method_name='getUtilization'))
            for token_address in tokens_and_types
        ]

        try:
            call_output = self.ethereum.multicall(calls=calls)  # get utilizations
        except RemoteError as e:
            log.error(f'Failed to query Compound v3 token utilizations while fetching the interest rates due to {e!s}')  # noqa: E501
            return rates

        rates_calls: dict[BalanceType, list[tuple[ChecksumEvmAddress, str]]] = defaultdict(list)
        rates_calls_arguments: dict[BalanceType, list[str]] = defaultdict(list)
        for idx, (token_address, _) in enumerate(calls):  # prepare calls for interest rates
            for balance_type in tokens_and_types[token_address]:
                decoded_utilization = token_contract.decode(
                    result=call_output[idx],
                    method_name='getUtilization',
                )[0]
                rates_calls[balance_type].append((
                    token_address,
                    token_contract.encode(
                        method_name=f'get{"Supply" if balance_type == BalanceType.ASSET else "Borrow"}Rate',  # noqa: E501
                        arguments=[decoded_utilization],  # passing decoded utilization
                    ),
                ))
                rates_calls_arguments[balance_type].append(decoded_utilization)

        try:
            call_output = self.ethereum.multicall(  # get n supply and m borrow rates
                calls=rates_calls[BalanceType.ASSET] + rates_calls[BalanceType.LIABILITY],  # n + m
            )
        except RemoteError as e:
            log.error(f'Failed to query Compound v3 Supply and Borrow rates due to {e!s}')
            return rates

        for idx, (token_address, _) in enumerate(rates_calls[BalanceType.ASSET]):
            try:
                rates[token_address][BalanceType.ASSET] = (deserialize_fval(
                    name='supply rate',
                    location='_get_v3_interest_rates',
                    value=token_contract.decode(
                        method_name='getSupplyRate',
                        arguments=[rates_calls_arguments[BalanceType.ASSET][idx]],
                        result=call_output[idx],  # first n are supply rates
                    )[0],
                ) / ETH_MANTISSA) * YEAR_IN_SECONDS
            except DeserializationError as e:
                log.error(f'Ignoring compound v3 supply rate for token address {token_address} due to {e}')  # noqa: E501

        for idx, (token_address, _) in enumerate(rates_calls[BalanceType.LIABILITY]):
            try:
                rates[token_address][BalanceType.LIABILITY] = (deserialize_fval(
                    name='borrow rate',
                    location='_get_v3_interest_rates',
                    value=token_contract.decode(
                        method_name='getBorrowRate',
                        arguments=[rates_calls_arguments[BalanceType.LIABILITY][idx]],
                        result=call_output[len(rates_calls[BalanceType.ASSET]) + idx],  # next m are borrow rates  # noqa: E501
                    )[0],
                ) / ETH_MANTISSA) * YEAR_IN_SECONDS
            except DeserializationError as e:
                log.error(f'Ignoring compound v3 borrow rate for token address {token_address} due to {e}')  # noqa: E501

        return rates

    def _get_v3_rewards(
            self,
            users: list[ChecksumEvmAddress],
    ) -> dict['EvmToken', dict[ChecksumEvmAddress, FVal]]:
        """Make multicalls to the compound v3 reward contracts to get the rewards of the users.
        Returns them as a dict of token -> user_address -> rewards."""
        rewards: dict[EvmToken, dict[ChecksumEvmAddress, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501
        reward_contract = EvmContract(
            address=ZERO_ADDRESS,  # not used here
            abi=self.ethereum.contracts.abi('COMPOUND_V3_REWARDS'),
            deployed_block=0,  # not used here
        )
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        token_arguments: list[ChecksumEvmAddress] = []
        user_address_arguments: list[ChecksumEvmAddress] = []
        for token_address in (  # Ethereum mainnet tokens taken from https://docs.compound.finance/#networks
            string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),  # cUSDCv3
            string_to_evm_address('0xA17581A9E3356d9A858b789D68B4d866e593aE94'),  # cWETHv3
        ):
            for user_address in users:
                calls.append((
                    string_to_evm_address('0x1B0e765F6224C21223AeA2af16c1C46E38885a40'),  # reward contract  # noqa: E501
                    reward_contract.encode(
                        method_name='getRewardOwed',
                        arguments=[token_address, user_address],
                    ),
                ))
                token_arguments.append(token_address)
                user_address_arguments.append(user_address)

        try:
            call_output = self.ethereum.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query Compound v3 rewards due to {e!s}')
            return rewards

        for idx in range(len(calls)):
            reward_token_address, reward_amount = reward_contract.decode(
                method_name='getRewardOwed',
                arguments=[token_arguments[idx], user_address_arguments[idx]],
                result=call_output[idx],
            )[0]

            try:
                reward_token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=reward_token_address,
                    chain_id=ChainID.ETHEREUM,
                    token_kind=EvmTokenKind.ERC20,
                    evm_inquirer=self.ethereum,
                )
            except (NotERC20Conformant, NotERC721Conformant) as e:
                log.error(f'Found {reward_token_address} for compound v3 reward which is not ERC20 conformant: {e!s}. Ignoring')  # noqa: E501
                continue

            try:
                rewards[reward_token][user_address_arguments[idx]] += deserialize_fval(
                    name='reward',
                    location='_get_v3_rewards',
                    value=reward_amount,
                ) / (10 ** reward_token.get_decimals())
            except DeserializationError as e:
                log.error(f'Ignoring {reward_token.symbol} reward for user {user_address_arguments[idx]} due to {e}')  # noqa: E501

        return rewards

    def populate_v3_balances(
            self,
            compound_balances: dict[ChecksumEvmAddress, dict[str, dict['Asset', CompoundBalance]]],
            given_eth_balances: 'GIVEN_ETH_BALANCES',
    ) -> dict[ChecksumEvmAddress, dict[str, dict['Asset', CompoundBalance]]]:
        v3_balances: dict[ChecksumEvmAddress, dict[str, dict[EvmToken, Balance]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(Balance)))  # noqa: E501
        interest_rate_multicall_args: dict[ChecksumEvmAddress, list[BalanceType]] = defaultdict(list)  # noqa: E501
        rewards_multicall_args: list[ChecksumEvmAddress] = []
        for account, asset_balances in (
            given_eth_balances if isinstance(given_eth_balances, dict) else given_eth_balances()
        ).items():
            for asset, balance in asset_balances.assets.items():
                if (
                    asset.is_evm_token() and
                    (asset := asset.resolve_to_evm_token()).protocol == CPT_COMPOUND_V3 and
                    asset.underlying_tokens is not None
                ):
                    v3_balances[account]['lending'][asset] = balance  # type: ignore[index]  # asset is EvmToken here
                    interest_rate_multicall_args[asset.evm_address].append(BalanceType.ASSET)  # type: ignore[attr-defined]  # asset is EvmToken here
                    rewards_multicall_args.append(account)

            for asset, balance in asset_balances.liabilities.items():
                with GlobalDBHandler().conn.read_ctx() as cursor:
                    if (compound_token := cursor.execute(  # get compound token of this asset
                        'SELECT parent_token_entry FROM underlying_tokens_list '
                        'WHERE identifier = ? AND parent_token_entry in '
                        '(SELECT identifier FROM evm_tokens WHERE protocol = ?);',
                        (asset.identifier, CPT_COMPOUND_V3),
                    ).fetchone()) is None:
                        continue  # it's not a compound liability

                compound_token = EvmToken(compound_token[0])
                v3_balances[account]['borrowing'][compound_token] = balance
                interest_rate_multicall_args[compound_token.evm_address].append(BalanceType.LIABILITY)
                rewards_multicall_args.append(account)

        interest_rates = self._get_v3_interest_rates(interest_rate_multicall_args)
        rewards = self._get_v3_rewards(rewards_multicall_args)

        # set the APYs
        for user_address, balances in v3_balances.items():
            for asset, balance in balances['lending'].items():
                compound_balances[user_address]['lending'][asset] = CompoundBalance(
                    balance_type=BalanceType.ASSET,
                    balance=balance,
                    apy=interest_rates[asset.evm_address][BalanceType.ASSET],
                )

            for liability, balance in balances['borrowing'].items():
                compound_balances[user_address]['borrowing'][liability] = CompoundBalance(
                    balance_type=BalanceType.LIABILITY,
                    balance=balance,
                    apy=interest_rates[liability.evm_address][BalanceType.LIABILITY],
                )

        # set the v3 rewards
        for token in rewards:
            for user_address, reward in rewards[token].items():
                compound_balances[user_address]['rewards'][token] = CompoundBalance(
                    balance_type=BalanceType.ASSET,
                    balance=Balance(
                        amount=reward,
                        usd_value=reward * Inquirer.find_usd_price(asset=token),
                    ),
                    apy=None,
                )

        return compound_balances
