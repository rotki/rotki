import logging
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Union,
    cast,
    overload,
)

import requests
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from typing_extensions import Literal
from web3 import Web3

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.constants import YEAR_IN_SECONDS, ZERO
from rotkehlchen.constants.assets import A_ADX, A_DAI, A_USD
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_ethereum_address,
    deserialize_timestamp,
)
from rotkehlchen.typing import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import create_timestamp, ts_now
from rotkehlchen.utils.serialization import rlk_jsonloads_list

from .graph import BONDS_QUERY, CHANNEL_WITHDRAWS_QUERY, UNBOND_REQUESTS_QUERY, UNBONDS_QUERY
from .typing import (
    POOL_ID_POOL_NAME,
    TOM_POOL_ID,
    AdexEvent,
    AdexEventType,
    ADXStakingBalance,
    ADXStakingDetail,
    ADXStakingEvents,
    ADXStakingHistory,
    Bond,
    ChannelWithdraw,
    DeserializationMethod,
    FeeRewards,
    TomPoolIncentive,
    Unbond,
    UnbondRequest,
    UnclaimedReward,
)
from .utils import (
    ADEX_EVENTS_PREFIX,
    ADX_AMOUNT_MANTISSA,
    CREATE2_SALT,
    DAI_AMOUNT_MANTISSA,
    EVENT_TYPE_ORDER_IN_ASC,
    IDENTITY_FACTORY_ADDR,
    IDENTITY_PROXY_INIT_CODE,
    OUTSTANDING_REWARD_THRESHOLD,
    STAKING_ADDR,
    SUBGRAPH_REMOTE_ERROR_MSG,
    TOM_POOL_FEE_REWARDS_ADX_LEGACY_CHANNEL,
    TOM_POOL_FEE_REWARDS_API_URL,
    TOM_POOL_PERIOD_FORMAT,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Adex(EthereumModule):
    """AdEx integration module

    AdEx subgraph:
    https://github.com/samparsky/adex_subgraph
    """
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        try:
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/adexnetwork/adex-protocol-v2',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('subgraph remote error') from e

    @staticmethod
    def _calculate_unclaimed_reward(
            address: ChecksumAddress,
            user_identity: ChecksumAddress,
            fee_rewards: FeeRewards,
            channel_withdraws: List[ChannelWithdraw],
            is_pnl_report: bool = False,
    ) -> UnclaimedReward:
        """May raise DeserializationError"""
        if is_pnl_report:
            return UnclaimedReward(
                adx_amount=ZERO,
                dai_amount=ZERO,
            )

        adx_unclaimed_amount = ZERO
        dai_unclaimed_amount = ZERO
        now = ts_now()
        for entry in fee_rewards:
            try:
                valid_until = deserialize_timestamp(entry['channelArgs']['validUntil'])
                if valid_until < now:
                    continue

                balances = entry['balances']
                if address not in balances and user_identity not in balances:
                    continue

                channel_id = entry['channelId']
                token_ethereum_address = deserialize_ethereum_address(
                    entry['channelArgs']['tokenAddr'],
                )
                try:
                    token_ethereum_address = to_checksum_address(token_ethereum_address)
                except ValueError as e:
                    raise DeserializationError(
                        f"Invalid ethereum address: {token_ethereum_address} in channel: {channel_id}.",  # noqa: E501
                    ) from e

                if token_ethereum_address == A_ADX.ethereum_address:
                    channel_adx_reward_amount = FVal(
                        balances.get(address, None) or balances[user_identity],
                    ) / ADX_AMOUNT_MANTISSA
                    channel_adx_claimed_amount = FVal(sum(
                        channel_withdraw.value.amount
                        for channel_withdraw in channel_withdraws
                        if channel_withdraw.channel_id == channel_id
                    ))
                    adx_unclaimed_amount += channel_adx_reward_amount - channel_adx_claimed_amount

                elif token_ethereum_address == A_DAI.ethereum_address:
                    channel_dai_reward_amount = FVal(
                        balances.get(address, None) or balances[user_identity],
                    ) / DAI_AMOUNT_MANTISSA
                    channel_dai_claimed_amount = FVal(sum(
                        channel_withdraw.value.amount
                        for channel_withdraw in channel_withdraws
                        if channel_withdraw.channel_id == channel_id
                    ))
                    dai_unclaimed_amount += channel_dai_reward_amount - channel_dai_claimed_amount

            except (DeserializationError, KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key in event: {msg}.'

                log.error(
                    'Failed to deserialize the AdEx Tom pool fee rewards when calculating '
                    'the claimed amount',
                    error=msg,
                    entry=entry,
                )
                raise DeserializationError(
                    'Failed to deserialize the AdEx Tom pool fee rewards. '
                    'Check logs for more details',
                ) from e

        if dai_unclaimed_amount < OUTSTANDING_REWARD_THRESHOLD:
            dai_unclaimed_amount = ZERO

        return UnclaimedReward(
            adx_amount=adx_unclaimed_amount,
            dai_amount=dai_unclaimed_amount,
        )

    def _calculate_staking_balances(
            self,
            staking_events: ADXStakingEvents,
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            fee_rewards: FeeRewards,
            adx_usd_price: Price,
            dai_usd_price: Price,
            is_pnl_report: bool = False,
    ) -> Dict[ChecksumAddress, List[ADXStakingBalance]]:
        """Given a list of bonds, unbonds and unbond requests returns per address
        the balance. The balance is the staked amount plus the unclaimed rewards

        Given an address, its staked amount per pool is computed by deducting
        the unbonds and the unbond requests from its bonds.
        """
        inverse_identity_address_map = {
            address: identity for identity, address in identity_address_map.items()
        }
        address_bonds = defaultdict(list)
        address_unbonds_set = {
            (unbond.address, unbond.bond_id)
            for unbond in staking_events.unbonds
        }
        address_unbond_requests_set = {
            (unbond_request.address, unbond_request.bond_id)
            for unbond_request in staking_events.unbond_requests
        }
        address_channel_withdraws = defaultdict(list)
        for channel_withdraw in staking_events.channel_withdraws:
            address_channel_withdraws[channel_withdraw.address].append(channel_withdraw)

        # Get bonds whose `bond_id` is not in unbonds or unbond_requests
        for bond in staking_events.bonds:
            if (
                (bond.address, bond.bond_id) in
                address_unbonds_set.union(address_unbond_requests_set)
            ):
                continue
            address_bonds[bond.address].append(bond)

        adex_balances: DefaultDict[ChecksumAddress, List[ADXStakingBalance]] = defaultdict(list)
        for address, bonds in address_bonds.items():
            pool_ids = {bond.pool_id for bond in bonds}
            for pool_id in pool_ids:
                if pool_id != TOM_POOL_ID:
                    log.warning(
                        'Unexpected AdEx pool. Please update the code for supporting it',
                        pool_id=pool_id,
                    )
                    continue

                # ADX amount staked, ADX and DAI claimed amounts
                adx_staked_amount = FVal(
                    sum(bond.value.amount for bond in bonds if bond.pool_id == pool_id),
                )
                try:
                    unclaimed_reward = self._calculate_unclaimed_reward(
                        address=address,
                        user_identity=inverse_identity_address_map[address],
                        fee_rewards=fee_rewards,
                        channel_withdraws=address_channel_withdraws[address],
                        is_pnl_report=is_pnl_report,
                    )
                except DeserializationError:
                    unclaimed_reward = UnclaimedReward(
                        adx_amount=ZERO,
                        dai_amount=ZERO,
                    )
                    self.msg_aggregator.add_error(
                        'There was an error processing the AdEx fee rewards API data. '
                        'The AdEx staking balances won\'t include the unclaimed '
                        'amounts of ADX and DAI. Check logs for more details',
                    )

                adx_amount = adx_staked_amount + unclaimed_reward.adx_amount
                pool_balance = ADXStakingBalance(
                    pool_id=pool_id,
                    pool_name=POOL_ID_POOL_NAME[pool_id],
                    adx_balance=Balance(
                        amount=adx_amount,
                        usd_value=adx_amount * adx_usd_price,
                    ),
                    adx_unclaimed_balance=Balance(
                        amount=unclaimed_reward.adx_amount,
                        usd_value=unclaimed_reward.adx_amount * adx_usd_price,
                    ),
                    dai_unclaimed_balance=Balance(
                        amount=unclaimed_reward.dai_amount,
                        usd_value=unclaimed_reward.dai_amount * dai_usd_price,
                    ),
                    contract_address=to_checksum_address(STAKING_ADDR),
                )
                adex_balances[address].append(pool_balance)

        return dict(adex_balances)

    @staticmethod
    def _get_staking_history(
            staking_balances: Dict[ChecksumAddress, List[ADXStakingBalance]],
            staking_events: ADXStakingEvents,
            tom_pool_incentive: TomPoolIncentive,
    ) -> Dict[ChecksumAddress, ADXStakingHistory]:
        """Given the following params:
          - staking_balances: the balances of the addresses per pool.
          - staking_events: all the events of the addresses mixed but grouped by
          type.
          - tom_pool_incentive: the current ADX incentives of the Tom pool.

        Return a map between an address and its <ADXStakingDetail>, which contains
        all the events that belong to the address, and the performance details
        per staking pool.
        """
        staking_history = {}
        address_staking_events = defaultdict(list)
        all_events = staking_events.get_all()
        # Map addresses with their events
        for event in all_events:
            address_staking_events[event.address].append(event)

        # Sort staking events per address by timestamp (older first) and event type
        for address in address_staking_events.keys():
            address_staking_events[address].sort(
                key=lambda event: (event.timestamp, EVENT_TYPE_ORDER_IN_ASC[type(event)]),
            )

        for address, adx_staking_balances in staking_balances.items():
            adx_staking_details = []
            for adx_staking_balance in adx_staking_balances:
                # NB: currently it only returns staking details for Tom pool
                if adx_staking_balance.pool_id != TOM_POOL_ID:
                    log.warning(
                        'Unexpected AdEx pool. Please update the code for supporting it',
                        pool_id=adx_staking_balance.pool_id,
                    )
                    continue

                adx_total_profit = Balance()
                dai_total_profit = Balance()
                # Add claimed amounts and their historical usd value
                for event in address_staking_events[address]:
                    if isinstance(event, ChannelWithdraw):
                        if event.token == A_ADX:
                            adx_total_profit += event.value
                        elif event.token == A_DAI:
                            dai_total_profit += event.value

                # Add unclaimed amounts and their current usd value
                adx_total_profit += adx_staking_balance.adx_unclaimed_balance
                dai_total_profit += adx_staking_balance.dai_unclaimed_balance

                pool_staking_detail = ADXStakingDetail(
                    contract_address=adx_staking_balance.contract_address,
                    pool_id=adx_staking_balance.pool_id,
                    pool_name=adx_staking_balance.pool_name,
                    total_staked_amount=(
                        tom_pool_incentive.total_staked_amount / ADX_AMOUNT_MANTISSA
                    ),
                    apr=tom_pool_incentive.apr,
                    adx_balance=adx_staking_balance.adx_balance,
                    adx_unclaimed_balance=adx_staking_balance.adx_unclaimed_balance,
                    dai_unclaimed_balance=adx_staking_balance.dai_unclaimed_balance,
                    adx_profit_loss=adx_total_profit,
                    dai_profit_loss=dai_total_profit,
                )
                adx_staking_details.append(pool_staking_detail)

            staking_history[address] = ADXStakingHistory(
                events=address_staking_events[address],
                staking_details=adx_staking_details,
            )
        return staking_history

    def _deserialize_bond(
            self,
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> Bond:
        """Deserialize a bond event.

        May raise DeserializationError.
        """
        try:
            adex_event = self._deserialize_adex_staking_event(
                raw_event=raw_event,
                identity_address_map=identity_address_map,
                case='bond',
            )
            amount_int = int(raw_event['amount'])
            amount = FVal(raw_event['amount']) / ADX_AMOUNT_MANTISSA
            pool_id = raw_event['poolId']
            nonce = int(raw_event['nonce'])
            bond_id = self._get_bond_id(
                identity_address=adex_event.identity_address,
                amount=amount_int,
                pool_id=pool_id,
                nonce=nonce,
            )
            slashed_at = deserialize_timestamp(raw_event['slashedAtStart'])
        except (DeserializationError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in event: {msg}.'

            log.error(
                'Failed to deserialize an AdEx bond event',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx bond event. Check logs for more details',
            ) from e

        return Bond(
            tx_hash=adex_event.tx_hash,
            address=adex_event.address,
            identity_address=adex_event.identity_address,
            timestamp=adex_event.timestamp,
            bond_id=bond_id,
            value=Balance(amount=amount),
            pool_id=pool_id,
            nonce=nonce,
            slashed_at=slashed_at,
        )

    @staticmethod
    def _deserialize_channel_withdraw(
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> ChannelWithdraw:
        """Deserialize a channel withdraw event. Only for Tom pool.

        May raise DeserializationError.
        """
        inverse_identity_address_map = {
            address: identity for identity, address in identity_address_map.items()
        }
        try:
            event_id = raw_event['id']
            user_address = raw_event['user']
            timestamp = deserialize_timestamp(raw_event['timestamp'])
            amount = FVal(raw_event['amount']) / ADX_AMOUNT_MANTISSA
            channel_id = raw_event['channel']['channelId']
            token_address = raw_event['channel']['tokenAddr']
        except (DeserializationError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in event: {msg}.'

            log.error(
                'Failed to deserialize an AdEx channel withdraw event',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx channel withdraw event. Check logs for more details',  # noqa: E501
            ) from e

        try:
            # tx_hash:identity_address:log_index
            tx_hash, tx_address, tx_log_index = event_id.split(':')
            log_index = int(tx_log_index)
        except (AttributeError, ValueError) as e:
            msg = str(e)
            if isinstance(e, AttributeError):
                msg = f'Unexpected type in event id: {type(raw_event["id"])}.'

            log.error(
                'Failed to deserialize an AdEx channel withdraw event id',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx channel withdraw event. Check logs for more details',  # noqa: E501
            ) from e

        try:
            address = to_checksum_address(user_address)
            identity_address = inverse_identity_address_map[address]
            tx_address = to_checksum_address(tx_address)
            token_address = to_checksum_address(token_address)
        except (KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in event: {msg}.'

            log.error(
                'Failed to deserialize an AdEx channel withdraw event',
                error=f'Invalid ethereum address in channel withdraw event: {token_address}. {msg}.',  # noqa: E501
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx channel withdraw event. Check logs for more details',  # noqa: E501
            ) from e

        if tx_address != address:
            msg = (
                f'Unexpected ethereum address in channel withdraw event id: {tx_address}. '
                f'The event address does not match the address: {address}.'
            )
            log.error(
                'Failed to deserialize an AdEx channel withdraw event',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx channel withdraw event. Check logs for more details',  # noqa: E501
            )

        if token_address == A_ADX.ethereum_address:
            token = A_ADX
        elif token_address == A_DAI.ethereum_address:
            token = A_DAI
        else:
            log.error(
                'Failed to deserialize an AdEx channel withdraw event',
                error=f'Unexpected token address: {token_address} on channel: {channel_id}',
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx channel withdraw event. Check logs for more details',  # noqa: E501
            )

        return ChannelWithdraw(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
            value=Balance(amount=amount),
            channel_id=channel_id,
            pool_id=TOM_POOL_ID,
            token=token,
            log_index=log_index,
        )

    @staticmethod
    def _deserialize_adex_staking_event(
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            case: Literal['bond', 'unbond', 'unbond_request'],
    ) -> AdexEvent:
        """Deserialize the common attributes of a staking event.

        May raise:
        - KeyError
        - DeserializationError
        """
        try:
            identity_address = to_checksum_address(raw_event['owner'])
        except ValueError as e:
            raise DeserializationError(
                f"Invalid ethereum address in {case} event owner: {raw_event['owner']}.",
            ) from e

        address = identity_address_map[identity_address]
        event_id = raw_event['id']
        if not isinstance(event_id, str):
            raise DeserializationError(f'Unexpected type in {case} event id: {type(event_id)}.')

        try:
            if case == 'bond':
                tx_hash = event_id
            elif case in ('unbond', 'unbond_request'):
                # tx_hash:address
                tx_hash, tx_address = event_id.split(':')
            else:
                raise AssertionError(f'Unexpected deserialization case: {case}.')
        except ValueError as e:
            raise DeserializationError(f'Unexpected format in {case} event id: {event_id}') from e

        if case in ('unbond', 'unbond_request'):
            try:
                tx_address = to_checksum_address(tx_address)
            except ValueError as e:
                raise DeserializationError(
                    f'Invalid ethereum address in {case} event id: {tx_address}.',
                ) from e

            if address != tx_address:
                raise DeserializationError(
                    f'Unexpected ethereum address in {case} event id: {tx_address}. '
                    f'The event address does not match the user address: {address}.',
                )

        timestamp = deserialize_timestamp(raw_event['timestamp'])

        return AdexEvent(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
        )

    def _deserialize_unbond(
            self,
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> Unbond:
        """Deserialize an unbond event.

        May raise DeserializationError.
        """
        try:
            adex_event = self._deserialize_adex_staking_event(
                raw_event=raw_event,
                identity_address_map=identity_address_map,
                case='unbond',
            )
            bond_id = raw_event['bondId']
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in event: {msg}.'

            log.error(
                'Failed to deserialize an AdEx unbond event',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx unbond event. Check logs for more details',
            ) from e

        return Unbond(
            tx_hash=adex_event.tx_hash,
            address=adex_event.address,
            identity_address=adex_event.identity_address,
            timestamp=adex_event.timestamp,
            bond_id=bond_id,
            value=Balance(),
        )

    def _deserialize_unbond_request(
            self,
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> UnbondRequest:
        """Deserialize an unbond request event.

        It may raise KeyError.
        """
        try:
            adex_event = self._deserialize_adex_staking_event(
                raw_event=raw_event,
                identity_address_map=identity_address_map,
                case='unbond_request',
            )
            bond_id = raw_event['bondId']
            unlock_at = deserialize_timestamp(raw_event['willUnlock'])
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in event: {msg}.'

            log.error(
                'Failed to deserialize an AdEx unbond request event',
                error=msg,
                raw_event=raw_event,
                identity_address_map=identity_address_map,
            )
            raise DeserializationError(
                'Failed to deserialize an AdEx unbond request event. Check logs for more details',
            ) from e

        return UnbondRequest(
            tx_hash=adex_event.tx_hash,
            address=adex_event.address,
            identity_address=adex_event.identity_address,
            timestamp=adex_event.timestamp,
            bond_id=bond_id,
            value=Balance(),
            unlock_at=unlock_at,
        )

    def _get_tom_pool_fee_rewards_from_api(self) -> FeeRewards:
        """Do a GET request to the Tom pool fee rewards API"""
        try:
            response = self.session.get(TOM_POOL_FEE_REWARDS_API_URL)
        except requests.exceptions.RequestException as e:
            msg = (
                f'AdEx get request at {TOM_POOL_FEE_REWARDS_API_URL} connection error: {str(e)}.'
            )
            log.error(msg)
            raise RemoteError(msg) from e

        if response.status_code != HTTPStatus.OK:
            msg = (
                f'AdEx fee rewards API query responded with error status code: '
                f'{response.status_code} and text: {response.text}.'
            )
            log.error(msg)
            raise RemoteError(msg)

        fee_rewards: FeeRewards
        try:
            fee_rewards = rlk_jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'AdEx fee rewards API returned invalid JSON response: {response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        return fee_rewards

    def _get_staking_events(
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> ADXStakingEvents:
        """Given a list of addresses returns all their staking events within
        the given time range. The returned events are grouped by type in
        <ADXStakingEvents>.

        For new addresses it requests all the events via subgraph.
        For existing addresses it requests all the events since the latest
        request timestamp (the minimum timestamp among all the existing
        addresses).

        May raise:
        - RemoteError: when there is a problem either querying the subgraph or
        deserializing the events.
        """
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_from_timestamp: Timestamp = to_timestamp

        # Get addresses' last used query range for AdEx events
        for address in addresses:
            entry_name = f'{ADEX_EVENTS_PREFIX}_{address}'
            events_range = self.database.get_used_query_range(name=entry_name)
            if not events_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_from_timestamp = min(min_from_timestamp, events_range[1])

        # Request new addresses' events
        all_new_events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]] = []
        if new_addresses:
            new_events = self._get_new_staking_events_graph(
                addresses=addresses,
                identity_address_map=identity_address_map,
                from_timestamp=Timestamp(0),
                to_timestamp=to_timestamp,
            )
            all_new_events.extend(new_events)

        # Request existing DB addresses' events
        if existing_addresses and to_timestamp > min_from_timestamp:
            new_events = self._get_new_staking_events_graph(
                addresses=addresses,
                identity_address_map=identity_address_map,
                from_timestamp=min_from_timestamp,
                to_timestamp=to_timestamp,
            )
            all_new_events.extend(new_events)

        # Add new events in DB
        if all_new_events:
            new_staking_events = self._get_addresses_staking_events_grouped_by_type(
                events=all_new_events,
                addresses=set(addresses),
            )
            self._update_events_value(staking_events=new_staking_events)
            self.database.add_adex_events(new_staking_events.get_all())

        # Fetch all DB events within the time range
        db_events = self.database.get_adex_events(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        staking_events = self._get_addresses_staking_events_grouped_by_type(
            events=db_events,
            addresses=set(addresses),
        )
        return staking_events

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            event_type: Literal[AdexEventType.BOND],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[Bond]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            event_type: Literal[AdexEventType.UNBOND],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[Unbond]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            event_type: Literal[AdexEventType.UNBOND_REQUEST],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[UnbondRequest]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            event_type: Literal[AdexEventType.CHANNEL_WITHDRAW],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[ChannelWithdraw]:
        ...

    def _get_staking_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            event_type: AdexEventType,
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> Union[List[Bond], List[Unbond], List[UnbondRequest], List[ChannelWithdraw]]:
        """Get the addresses' events data querying the AdEx subgraph

        May raise:
        - DeserializationError: when there is a problem deserializing the
        events on the subgraph response.
        - RemoteError: when there is a problem querying the subgraph.
        """
        user_identities = [str(identity).lower() for identity in identity_address_map.keys()]
        deserialization_method: DeserializationMethod
        querystr: str
        schema: Literal['bonds', 'unbonds', 'unbondRequests', 'channelWithdraws']
        if event_type == AdexEventType.BOND:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_bond
            querystr = format_query_indentation(BONDS_QUERY.format())
            schema = 'bonds'
        elif event_type == AdexEventType.UNBOND:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_unbond
            querystr = format_query_indentation(UNBONDS_QUERY.format())
            schema = 'unbonds'
        elif event_type == AdexEventType.UNBOND_REQUEST:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_unbond_request
            querystr = format_query_indentation(UNBOND_REQUESTS_QUERY.format())
            schema = 'unbondRequests'
        elif event_type == AdexEventType.CHANNEL_WITHDRAW:
            queried_addresses = [address.lower() for address in addresses]
            deserialization_method = self._deserialize_channel_withdraw
            querystr = format_query_indentation(CHANNEL_WITHDRAWS_QUERY.format())
            schema = 'channelWithdraws'
        else:
            raise AssertionError(f'Unexpected AdEx event type: {event_type}.')

        start_ts = from_timestamp or 0
        end_ts = to_timestamp or ts_now()
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$queried_addresses': '[Bytes!]',
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'queried_addresses': queried_addresses,
            'start_ts': start_ts,
            'end_ts': end_ts,
        }
        events = []
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            result_data = result[schema]
            for raw_event in result_data:
                event = deserialization_method(
                    raw_event=raw_event,
                    identity_address_map=identity_address_map,
                )
                events.append(event)

            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            offset = cast(int, param_values['offset'])
            param_values = {
                **param_values,
                'offset': offset + GRAPH_QUERY_LIMIT,
            }

        return events  # type: ignore # the suggested type is not the right one

    @staticmethod
    def _get_addresses_staking_events_grouped_by_type(
            events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]],
            addresses: Set[ChecksumAddress],
    ) -> ADXStakingEvents:
        """Filter out events that don't belong to any of the addresses and
        return the valid ones grouped by event type in <ADXStakingEvents>.
        """
        bonds = []
        unbonds = []
        unbond_requests = []
        channel_withdraws = []
        for event in events:
            if event.address in addresses:
                if isinstance(event, Bond):
                    bonds.append(event)
                elif isinstance(event, Unbond):
                    unbonds.append(event)
                elif isinstance(event, UnbondRequest):
                    unbond_requests.append(event)
                elif isinstance(event, ChannelWithdraw):
                    channel_withdraws.append(event)
                else:
                    raise AssertionError(f'Unexpected AdEx event type: {type(event)}.')

        return ADXStakingEvents(
            bonds=bonds,
            unbonds=unbonds,
            unbond_requests=unbond_requests,
            channel_withdraws=channel_withdraws,
        )

    @staticmethod
    def _get_bond_id(
            identity_address: ChecksumAddress,
            amount: int,
            pool_id: str,
            nonce: int,
    ) -> str:
        """Given a LogBond event data, return its `bondId`"""
        arg_types = ['address', 'address', 'uint', 'bytes32', 'uint']
        args = [STAKING_ADDR, identity_address, amount, pool_id, nonce]
        return Web3.keccak(Web3().codec.encode_abi(arg_types, args)).hex()

    def _get_identity_address_map(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumAddress, ChecksumAddress]:
        """Returns a map between the user identity address in the protocol and
        the EOA/contract address.
        """
        return {self._get_user_identity(address): address for address in addresses}

    @staticmethod
    def _get_tom_pool_incentive(
            fee_rewards: FeeRewards,
            is_pnl_report: bool = False,
    ) -> TomPoolIncentive:
        """Get Tom pool incentive data (staking rewards).

        NB: the APR calculated here is the APY in the AdEx codebase and website stats.
        https://github.com/AdExNetwork/adex-staking/blob/master/src/actions/actions.js#L86

        May raise DeserializationError
        """
        if is_pnl_report is True:
            return TomPoolIncentive(
                total_staked_amount=ZERO,
                apr=ZERO,
            )

        total_staked_amount = ZERO
        total_reward_per_second = ZERO
        period_ends_at = Timestamp(0)
        now = ts_now()
        for entry in fee_rewards:
            try:
                if (
                    entry['channelArgs']['tokenAddr'] == A_ADX.ethereum_address and
                    entry['channelId'] != TOM_POOL_FEE_REWARDS_ADX_LEGACY_CHANNEL
                ):
                    starts_at = create_timestamp(entry['periodStart'], formatstr=TOM_POOL_PERIOD_FORMAT)  # noqa: E501
                    ends_at = create_timestamp(entry['periodEnd'], formatstr=TOM_POOL_PERIOD_FORMAT)  # noqa: E501
                    if starts_at < now <= ends_at:
                        total_staked_amount = FVal(entry['stats']['currentTotalActiveStake'])
                        total_reward_per_second = FVal(entry['stats']['currentRewardPerSecond'])
                        period_ends_at = ends_at
                        break
            except (KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key in event: {msg}.'

                log.error(
                    'Failed to deserialize the AdEx Tom pool fee rewards when '
                    'getting the pool incentives',
                    error=msg,
                    entry=entry,
                )
                raise DeserializationError(
                    'Failed to deserialize the AdEx Tom pool fee rewards. '
                    'Check logs for more details',
                ) from e

        if total_staked_amount == ZERO or period_ends_at == Timestamp(0):
            msg = (
                'Failed to calculate the AdEx Tom pool APR. The current ADX channel '
                'is missing or it has an invalid ending period.'
            )
            log.error(msg)
            raise DeserializationError(
                'Failed to deserialize the AdEx Tom pool fee rewards. '
                'Check logs for more details',
            )

        # Calculate Tom pool APR
        seconds_left = FVal(period_ends_at - now)
        to_distribute = total_reward_per_second * seconds_left
        apr = to_distribute * YEAR_IN_SECONDS / seconds_left / total_staked_amount

        return TomPoolIncentive(
            total_staked_amount=total_staked_amount,
            apr=apr,
        )

    def _get_new_staking_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]:
        """Returns events of the addresses within the time range and inserts/updates
        the used query range of the addresses as well.

        May raise:
        - RemoteError: when there is a problem either querying the subgraph or
        deserializing the events.
        """
        all_events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]] = []
        for event_type_ in AdexEventType:
            try:
                # TODO: fix. type -> overload does not work well with enum in this case
                events = self._get_staking_events_graph(  # type: ignore
                    addresses=addresses,
                    identity_address_map=identity_address_map,
                    event_type=event_type_,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )
            except DeserializationError as e:
                raise RemoteError(e) from e

            all_events.extend(events)

        for address in addresses:
            self.database.update_used_query_range(
                name=f'{ADEX_EVENTS_PREFIX}_{address}',
                start_ts=from_timestamp,
                end_ts=to_timestamp,
            )
        return all_events

    @staticmethod
    def _get_user_identity(address: ChecksumAddress) -> ChecksumEthAddress:
        """Given an address (signer) returns its protocol user identity"""
        return generate_address_via_create2(
            address=IDENTITY_FACTORY_ADDR,
            salt=CREATE2_SALT,
            init_code=IDENTITY_PROXY_INIT_CODE.format(signer_address=address),
        )

    def _update_events_value(
            self,
            staking_events: ADXStakingEvents,
    ) -> None:
        # Update amounts for unbonds and unbond requests
        bond_id_bond_map: Dict[str, Optional[Bond]] = {
            bond.bond_id: bond for bond in staking_events.bonds
        }
        for event in (
            staking_events.unbonds +
            staking_events.unbond_requests  # type: ignore # mypy bug concatenating lists
        ):
            has_bond = True
            bond = bond_id_bond_map.get(event.bond_id, None)
            if bond:
                event.value = Balance(amount=bond.value.amount)
                event.pool_id = bond.pool_id
            elif event.bond_id not in bond_id_bond_map:
                bond_id_bond_map[event.bond_id] = None
                db_bonds = cast(List[Bond], self.database.get_adex_events(
                    bond_id=event.bond_id,
                    event_type=AdexEventType.BOND,
                ))
                if db_bonds:
                    db_bond = db_bonds[0]
                    bond_id_bond_map[event.bond_id] = db_bond
                    event.value = Balance(amount=db_bond.value.amount)
                    event.pool_id = db_bond.pool_id
                else:
                    has_bond = False
            else:
                has_bond = False

            if has_bond is False:
                log.warning(
                    'Failed to update an AdEx event data. Unable to find its related bond event',
                    event=event,
                )

        # Update usd_value for all events
        for event in staking_events.get_all():  # type: ignore # event can have all types
            token = event.token if isinstance(event, ChannelWithdraw) else A_ADX
            usd_price = PriceHistorian().query_historical_price(
                from_asset=token,
                to_asset=A_USD,
                timestamp=event.timestamp,
            )
            event.value.usd_value = event.value.amount * usd_price

    def get_balances(
            self,
            addresses: List[ChecksumAddress],
    ) -> Dict[ChecksumAddress, List[ADXStakingBalance]]:
        """Return the addresses' balances (staked amount per pool) in the AdEx
        protocol.

        May raise:
        - RemoteError: when there is a problem either querying the subgraph or
        deserializing the events.

        TODO: route non-premium users through on-chain query.
        """
        staking_balances: Dict[ChecksumAddress, List[ADXStakingBalance]] = {}
        fee_rewards: FeeRewards
        try:
            fee_rewards = self._get_tom_pool_fee_rewards_from_api()
        except RemoteError:
            fee_rewards = []
            self.msg_aggregator.add_error(
                'There was an error requesting the AdEx fee rewards API. '
                'The AdEx balances won\'t include the unclaimed amounts of ADX and DAI. '
                'Check logs for more details',
            )

        identity_address_map = self._get_identity_address_map(addresses)
        all_events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]] = []
        try:
            for event_type_ in AdexEventType:
                # TODO: fix. type -> overload does not work well with enum in this case
                events = self._get_staking_events_graph(  # type: ignore
                    addresses=addresses,
                    identity_address_map=identity_address_map,
                    event_type=event_type_,
                )
                all_events.extend(events)
        except DeserializationError as e:
            raise RemoteError(e) from e

        staking_events = self._get_addresses_staking_events_grouped_by_type(
            events=all_events,
            addresses=set(addresses),
        )
        adx_usd_price = Inquirer().find_usd_price(A_ADX)
        dai_usd_price = Inquirer().find_usd_price(A_DAI)
        staking_balances = self._calculate_staking_balances(
            staking_events=staking_events,
            identity_address_map=identity_address_map,
            fee_rewards=fee_rewards,
            adx_usd_price=adx_usd_price,
            dai_usd_price=dai_usd_price,
        )
        return staking_balances

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            is_pnl_report: bool = False,
    ) -> Dict[ChecksumAddress, ADXStakingHistory]:
        """Get the staking history events of the addresses in the AdEx protocol.

        May raise:
        - RemoteError: when there is a problem either querying the subgraph or
        deserializing the events.
        """
        if reset_db_data is True:
            self.database.delete_adex_events_data()

        fee_rewards: FeeRewards
        try:
            fee_rewards = self._get_tom_pool_fee_rewards_from_api()
            tom_pool_incentive = self._get_tom_pool_incentive(
                fee_rewards=fee_rewards,
                is_pnl_report=is_pnl_report,
            )
        except (RemoteError, DeserializationError):
            fee_rewards = []
            tom_pool_incentive = TomPoolIncentive(
                total_staked_amount=ZERO,
                apr=ZERO,
            )
            self.msg_aggregator.add_error(
                'There was an error requesting the AdEx fee rewards API or processing the data. '
                'The AdEx events history won\'t include the unclaimed amounts of '
                'ADX and DAI nor the performance of the pools. Check logs for more details',
            )

        identity_address_map = self._get_identity_address_map(addresses)
        staking_events = self._get_staking_events(
            addresses=addresses,
            identity_address_map=identity_address_map,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        adx_usd_price = Inquirer().find_usd_price(A_ADX)
        dai_usd_price = Inquirer().find_usd_price(A_DAI)
        staking_balances = self._calculate_staking_balances(
            staking_events=staking_events,
            identity_address_map=identity_address_map,
            fee_rewards=fee_rewards,
            adx_usd_price=adx_usd_price,
            dai_usd_price=dai_usd_price,
            is_pnl_report=is_pnl_report,
        )
        staking_history = self._get_staking_history(
            staking_balances=staking_balances,
            staking_events=staking_events,
            tom_pool_incentive=tom_pool_incentive,
        )
        return staking_history

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: List[ChecksumEthAddress],
    ) -> List[DefiEvent]:
        mapping = self.get_history(
            addresses=addresses,
            reset_db_data=False,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            is_pnl_report=False,
        )
        events = []
        for _, history in mapping.items():
            for event in history.events:
                pnl = got_asset = got_balance = spent_asset = spent_balance = None  # noqa: E501
                if isinstance(event, Bond):
                    spent_asset = A_ADX
                    spent_balance = event.value
                elif isinstance(event, Unbond):
                    got_asset = A_ADX
                    got_balance = event.value
                elif isinstance(event, UnbondRequest):
                    continue  # just ignore those for accounting purposes
                elif isinstance(event, ChannelWithdraw):
                    got_asset = event.token
                    got_balance = event.value
                    pnl = [AssetBalance(asset=got_asset, balance=got_balance)]
                else:
                    raise AssertionError(f'Unexpected adex event type {type(event)}')

                events.append(DefiEvent(
                    timestamp=event.timestamp,
                    wrapped_event=event,
                    event_type=DefiEventType.ADEX_EVENT,
                    got_asset=got_asset,
                    got_balance=got_balance,
                    spent_asset=spent_asset,
                    spent_balance=spent_balance,
                    pnl=pnl,
                    # Do not count staking deposit/withdrawals as cost basis events
                    # the ADX was always ours. PnL will ofc still be counted.
                    count_spent_got_cost_basis=False,
                    tx_hash=event.tx_hash,
                ))

        return events

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_adex_events_data()
