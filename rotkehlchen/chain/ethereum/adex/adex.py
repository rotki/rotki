import logging
from collections import defaultdict
from datetime import datetime
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
    Tuple,
    Union,
    cast,
    overload,
)

import requests
from eth_typing import ChecksumAddress, HexAddress, HexStr
from eth_utils import to_checksum_address
from typing_extensions import Literal
from web3 import Web3

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.constants import YEAR_IN_SECONDS, ZERO
from rotkehlchen.constants.assets import A_ADX, A_DAI, A_USD
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.serialization import rlk_jsonloads_list

from .graph import BONDS_QUERY, CHANNEL_WITHDRAWS_QUERY, UNBOND_REQUESTS_QUERY, UNBONDS_QUERY
from .typing import (
    POOL_ID_POOL_NAME,
    TOM_POOL_ID,
    AdexEventType,
    ADXStakingBalance,
    ADXStakingDetail,
    ADXStakingEvents,
    ADXStakingHistory,
    Bond,
    ChannelWithdraw,
    DeserializationMethod,
    EventCoreData,
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
    PERIOD_END_AT_FORMAT,
    STAKING_ADDR,
    TOM_POOL_FEE_REWARDS_API_URL,
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
            self.graph: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/adexnetwork/adex-protocol',
            )
        except RemoteError as e:
            self.graph = None
            self.msg_aggregator.add_error(
                f'Could not initialize the AdEx subgraph due to {str(e)}. '
                f'All AdEx balances and historical queries are not functioning until this is fixed. '  # noqa: E501
                f'Probably will get fixed with time. If not report it to Rotki\'s support channel.',  # noqa: E501
            )

    @staticmethod
    def _calculate_staking_balances(
            staking_events: ADXStakingEvents,
            unclaimed_rewards: Dict[ChecksumAddress, UnclaimedReward],
            adx_usd_price: Price,
            dai_usd_price: Price,
    ) -> Dict[ChecksumAddress, List[ADXStakingBalance]]:
        """Given a list of bonds, unbonds and unbond requests returns per address
        the balance. The balance is the staked amount plus the unclaimed rewards

        Given an address, its staked amount per pool is computed by deducting
        the unbonds and the unbond requests from its bonds.
        """
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

        # Get per address staked balances in pools
        adex_balances: DefaultDict[ChecksumAddress, List[ADXStakingBalance]] = defaultdict(list)
        for address, bonds in address_bonds.items():
            pool_ids = {bond.pool_id for bond in bonds}
            for pool_id in pool_ids:
                pool_name = POOL_ID_POOL_NAME.get(pool_id, None)
                if pool_name is None:
                    log.error(
                        f'Error getting name for AdEx pool: {pool_id}. '
                        f'Please, update the map of pools and names.',
                    )
                # Add the ADX amount staked
                adx_staked_amount = FVal(
                    sum(bond.value.amount for bond in bonds if bond.pool_id == pool_id),
                )
                # Add the ADX amount claimed
                adx_claimed_amount = FVal(
                    sum(
                        event.value.amount
                        for event in address_channel_withdraws.get(address, [])
                        if event.token == A_ADX
                    ),
                )
                # Add the DAI amount claimed
                dai_claimed_amount = FVal(
                    sum(
                        event.value.amount
                        for event in address_channel_withdraws.get(address, [])
                        if event.token == A_DAI
                    ),
                )

                # Add ADX and DAI from the unclaimed feed
                adx_unclaimed_amount = ZERO
                dai_unclaimed_amount = ZERO
                if address in unclaimed_rewards:
                    adx_unclaimed_amount = (
                        unclaimed_rewards[address].adx_amount - adx_claimed_amount
                    )
                    dai_unclaimed_amount = (
                        unclaimed_rewards[address].dai_amount - dai_claimed_amount
                    )

                pool_balance = ADXStakingBalance(
                    pool_id=pool_id,
                    pool_name=pool_name,
                    adx_balance=Balance(
                        amount=adx_staked_amount + adx_unclaimed_amount,
                        usd_value=(adx_staked_amount + adx_unclaimed_amount) * adx_usd_price,
                    ),
                    adx_unclaimed_balance=Balance(
                        amount=adx_unclaimed_amount,
                        usd_value=adx_unclaimed_amount * adx_usd_price,
                    ),
                    dai_unclaimed_balance=Balance(
                        amount=dai_unclaimed_amount,
                        usd_value=dai_unclaimed_amount * dai_usd_price,
                    ),
                    contract_address=to_checksum_address(STAKING_ADDR),
                )
                adex_balances[address].append(pool_balance)

        return dict(adex_balances)

    @staticmethod
    def _get_staking_history(
        staking_balances: Dict[ChecksumAddress, List[ADXStakingBalance]],
        staking_events: ADXStakingEvents,
        tom_pool_incentive: Optional[TomPoolIncentive] = None,
    ) -> Dict[ChecksumAddress, ADXStakingHistory]:
        """Given the following params:
          - staking_balances: the balances of the addresses per pool.
          - staking_events: all the events of the addresses mixed but grouped by
          type.
          - tom_pool_incentive (optional): Tom pool incentive data.

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
                if adx_staking_balance.pool_id == TOM_POOL_ID and tom_pool_incentive is not None:
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

        It may raise KeyError.
        """
        event_core_data = self._deserialize_event_core_data(
            raw_event=raw_event,
            identity_address_map=identity_address_map,
        )
        amount_int = int(raw_event['amount'])
        amount = FVal(raw_event['amount']) / ADX_AMOUNT_MANTISSA
        pool_id = HexStr(raw_event['poolId'])
        nonce = int(raw_event['nonce'])
        bond_id = self._get_bond_id(
            identity_address=event_core_data.identity_address,
            amount=amount_int,
            pool_id=pool_id,
            nonce=nonce,
        )
        return Bond(
            tx_hash=event_core_data.tx_hash,
            address=event_core_data.address,
            identity_address=event_core_data.identity_address,
            timestamp=event_core_data.timestamp,
            bond_id=bond_id,
            value=Balance(amount=amount),
            pool_id=pool_id,
            nonce=nonce,
            slashed_at=Timestamp(int(raw_event['slashedAtStart'])),
        )

    @staticmethod
    def _deserialize_channel_withdraw(
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> ChannelWithdraw:
        """Deserialize a channel withdraw event. Only for Tom pool.

        It may raise KeyError.

        TODO: use bidict or already pass the inverse identity_address_map.
        """
        inverse_identity_address_map = {
            address: identity for identity, address in identity_address_map.items()
        }
        address = to_checksum_address(raw_event['user'])
        identity_address = inverse_identity_address_map[address]
        amount = FVal(raw_event['amount']) / ADX_AMOUNT_MANTISSA
        return ChannelWithdraw(
            tx_hash=HexStr(raw_event['id'].split(':')[0]),
            address=address,
            identity_address=identity_address,
            timestamp=Timestamp(raw_event['timestamp']),
            value=Balance(amount=amount),
            channel_id=HexStr(raw_event['channelId']),
            pool_id=TOM_POOL_ID,
        )

    @staticmethod
    def _deserialize_event_core_data(
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> EventCoreData:
        """Deserialize the common event attributes.

        It may raise KeyError.
        Id for unbond and unbond request events is 'tx_hash:address'.
        """
        identity_address = to_checksum_address(raw_event['owner'])
        return EventCoreData(
            tx_hash=HexStr(raw_event['id'].split(':')[0]),
            address=identity_address_map[identity_address],
            identity_address=identity_address,
            timestamp=Timestamp(raw_event['timestamp']),
        )

    def _deserialize_unbond(
            self,
            raw_event: Dict[str, Any],
            identity_address_map: Dict[ChecksumAddress, ChecksumAddress],
    ) -> Unbond:
        """Deserialize an unbond event.

        It may raise KeyError.
        """
        event_core_data = self._deserialize_event_core_data(
            raw_event=raw_event,
            identity_address_map=identity_address_map,
        )
        return Unbond(
            tx_hash=event_core_data.tx_hash,
            address=event_core_data.address,
            identity_address=event_core_data.identity_address,
            timestamp=event_core_data.timestamp,
            bond_id=HexStr(raw_event['bondId']),
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
        event_core_data = self._deserialize_event_core_data(
            raw_event=raw_event,
            identity_address_map=identity_address_map,
        )
        return UnbondRequest(
            tx_hash=event_core_data.tx_hash,
            address=event_core_data.address,
            identity_address=event_core_data.identity_address,
            timestamp=event_core_data.timestamp,
            bond_id=HexStr(raw_event['bondId']),
            value=Balance(),
            unlock_at=Timestamp(int(raw_event['willUnlock'])),
        )

    def _get_tom_pool_fee_rewards_from_api(self) -> FeeRewards:
        """Do a GET request to the Tom pool fee rewards API.
        """
        fee_rewards: FeeRewards = []
        try:
            response = self.session.get(TOM_POOL_FEE_REWARDS_API_URL)
        except requests.exceptions.RequestException as e:
            msg = (
                f'AdEx get request at {TOM_POOL_FEE_REWARDS_API_URL} connection error: {str(e)}.'
            )
            self.msg_aggregator.add_error(
                f'Got remote error while querying AdEx fee rewards API: {msg}',
            )
            return fee_rewards

        if response.status_code != HTTPStatus.OK:
            msg = (
                f'AdEx fee rewards API query responded with error status code: '
                f'{response.status_code} and text: {response.text}.'
            )
            self.msg_aggregator.add_error(
                f'Got remote error while querying AdEx fee rewards API: {msg}',
            )
            return fee_rewards

        try:
            fee_rewards = rlk_jsonloads_list(response.text)
        except JSONDecodeError:
            msg = f'AdEx fee rewards API returned invalid JSON response: {response.text}.'
            self.msg_aggregator.add_error(
                f'Got remote error while querying AdEx fee rewards API: {msg}',
            )
            return fee_rewards

        return fee_rewards

    def _get_staking_events(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            fee_rewards: FeeRewards,
    ) -> ADXStakingEvents:
        """Given a list of addresses returns all their staking events within
        the given time range. The returned events are grouped by type in
        <ADXStakingEvents>.

        For new addresses it requests all the events via subgraph.
        For existing addresses it requests all the events since the latest
        request timestamp (the minimum timestamp among all the existing
        addresses).
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
                from_timestamp=Timestamp(0),
                to_timestamp=to_timestamp,
            )
            all_new_events.extend(new_events)

        # Request existing DB addresses' events
        if existing_addresses and min_from_timestamp <= to_timestamp:
            new_events = self._get_new_staking_events_graph(
                addresses=addresses,
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
            self._update_channel_withdraw_events_token(
                channel_withdraws=new_staking_events.channel_withdraws,
                fee_rewards=fee_rewards,
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
            event_type: Literal[AdexEventType.BOND],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[Bond]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            event_type: Literal[AdexEventType.UNBOND],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[Unbond]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            event_type: Literal[AdexEventType.UNBOND_REQUEST],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[UnbondRequest]:
        ...

    @overload  # noqa: F811
    def _get_staking_events_graph(  # pylint: disable=no-self-use
            self,
            addresses: List[ChecksumEthAddress],
            event_type: Literal[AdexEventType.CHANNEL_WITHDRAW],
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[ChannelWithdraw]:
        ...

    def _get_staking_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            event_type: AdexEventType,
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> Union[List[Bond], List[Unbond], List[UnbondRequest], List[ChannelWithdraw]]:
        """Get the addresses' events data querying the AdEx subgraph.
        """
        identity_address_map = self._get_identity_address_map(addresses)
        user_identities = [str(identity).lower() for identity in identity_address_map.keys()]
        deserialization_method: DeserializationMethod
        querystr: str
        schema: Literal['bonds', 'unbonds', 'unbondRequests', 'channelWithdraws']
        if event_type == AdexEventType.BOND:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_bond
            querystr = format_query_indentation(BONDS_QUERY.format())
            schema = 'bonds'
            event_type_pretty = 'bond'
        elif event_type == AdexEventType.UNBOND:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_unbond
            querystr = format_query_indentation(UNBONDS_QUERY.format())
            schema = 'unbonds'
            event_type_pretty = 'unbond'
        elif event_type == AdexEventType.UNBOND_REQUEST:
            queried_addresses = user_identities
            deserialization_method = self._deserialize_unbond_request
            querystr = format_query_indentation(UNBOND_REQUESTS_QUERY.format())
            schema = 'unbondRequests'
            event_type_pretty = 'unbond request'
        elif event_type == AdexEventType.CHANNEL_WITHDRAW:
            queried_addresses = [address.lower() for address in addresses]
            deserialization_method = self._deserialize_channel_withdraw
            querystr = format_query_indentation(CHANNEL_WITHDRAWS_QUERY.format())
            schema = 'channelWithdraws'
            event_type_pretty = 'channel withdraws'
        else:
            raise AssertionError(f'Unexpected AdEx event type: {event_type}.')

        start_ts = from_timestamp or 0
        end_ts = to_timestamp or int(datetime.utcnow().timestamp())
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
                result = self.graph.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    f'{msg}. All AdEx balances queries are not functioning until this is fixed.',
                )
                raise

            result_data = result[schema]
            for raw_event in result_data:
                try:
                    event = deserialization_method(
                        raw_event=raw_event,
                        identity_address_map=identity_address_map,
                    )
                except KeyError as e:
                    msg = str(e)
                    log.error(
                        f'Error processing an AdEx {event_type_pretty}.',
                        raw_event=raw_event,
                        error=msg,
                    )
                    self.msg_aggregator.add_error(
                        f'Failed to deserialize an AdEx {event_type_pretty}. '
                        f'Check logs for details. Ignoring it.',
                    )
                    continue

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
            pool_id: HexStr,
            nonce: int,
    ) -> HexStr:
        """Given a LogBond event data, return its `bondId`.
        """
        arg_types = ['address', 'address', 'uint', 'bytes32', 'uint']
        args = [STAKING_ADDR, identity_address, amount, pool_id, nonce]
        return HexStr(Web3.keccak(Web3().codec.encode_abi(arg_types, args)).hex())

    def _get_identity_address_map(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumAddress, ChecksumAddress]:
        """Returns a map between the user identity address in the protocol and
        the EOA/contract address.
        """
        return {self._get_user_identity(address): address for address in addresses}

    def _get_tom_pool_unclaimed_rewards(
            self,
            addresses: List[ChecksumEthAddress],
            fee_rewards: FeeRewards,
    ) -> Dict[ChecksumAddress, UnclaimedReward]:
        """Get Tom pool unclaimed rewards per address

        NB: the unclaimed rewards are ADX and DAI balances associated with the
        user identity of the address.
        """
        identity_address_map = self._get_identity_address_map(addresses)
        address_adx_amount = defaultdict(list)
        address_dai_amount = defaultdict(list)
        for entry in fee_rewards:
            try:
                token_ethereum_address = entry['channelArgs']['tokenAddr']
                balances = entry['balances']
                if token_ethereum_address == A_ADX.ethereum_address:
                    for user_identity in identity_address_map.keys():
                        address = identity_address_map[user_identity]
                        address_adx_amount[address].append(FVal(balances.get(user_identity, ZERO)))
                elif token_ethereum_address == A_DAI.ethereum_address:
                    for user_identity in identity_address_map.keys():
                        address = identity_address_map[user_identity]
                        address_dai_amount[address].append(FVal(balances.get(user_identity, ZERO)))
                else:
                    log.error(
                        'Unexpected token address processing AdEx unclaimed rewards. ',
                        token_address=token_ethereum_address,
                    )
            except (KeyError, ValueError) as e:
                msg = str(e)
                log.error(
                    'Error processing AdEx Tom pool unclaimed rewards. ',
                    entry=entry,
                    error=msg,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize the AdEx Tom pool unclaimed rewards. '
                    'Check logs for details. Ignoring it.',
                )
                return {}

        unclaimed_rewards = {}
        for address in addresses:
            total_adx_amount = sum(address_adx_amount.get(address, []))
            total_dai_amount = sum(address_dai_amount.get(address, []))
            # Discard addresses without amounts
            if total_adx_amount + total_dai_amount > ZERO:
                unclaimed_rewards[address] = UnclaimedReward(
                    adx_amount=total_adx_amount / ADX_AMOUNT_MANTISSA,
                    dai_amount=total_dai_amount / DAI_AMOUNT_MANTISSA,
                )
        return unclaimed_rewards

    def _get_tom_pool_incentive(self) -> Optional[TomPoolIncentive]:
        """Get Tom pool incentive data (staking rewards).

        NB: the APR calculated here is the APY in the AdEx codebase and website stats.
        https://github.com/AdExNetwork/adex-staking/blob/master/src/actions/actions.js#L86

        TODO: once AdEx rolls out issue #94, check how they handle incentives
        with multiple channels, for instance how they process `periodEnd`.
        https://github.com/AdExNetwork/adex-staking/issues/94
        """
        fee_rewards = self._get_tom_pool_fee_rewards_from_api()
        total_staked_amount = ZERO
        total_reward_per_second = ZERO
        period_ends_at = Timestamp(0)
        apr = ZERO
        for entry in fee_rewards:
            try:
                if entry['channelArgs']['tokenAddr'] == A_ADX.ethereum_address:
                    total_staked_amount += entry['stats']['currentTotalActiveStake']
                    total_reward_per_second += entry['stats']['currentRewardPerSecond']
                    # NB: `period_ends_at` is always overwritten
                    period_ends_at = Timestamp(int(
                        datetime.strptime(entry['periodEnd'], PERIOD_END_AT_FORMAT).timestamp(),
                    ))
            except (KeyError, ValueError) as e:
                msg = str(e)
                log.error(
                    'Error processing AdEx Tom pool incentives. ',
                    entry=entry,
                    error=msg,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize the AdEx Tom pool incentives. '
                    'Check logs for details. Ignoring it.',
                )
                return None

        now = Timestamp(int(datetime.utcnow().timestamp()))
        # Calculate Tom pool APR
        if now < period_ends_at:  # else apr is zero
            seconds_left = FVal(period_ends_at - now)
            to_distribute = total_reward_per_second * seconds_left
            apr = to_distribute * YEAR_IN_SECONDS / seconds_left / total_staked_amount

        return TomPoolIncentive(
            total_staked_amount=total_staked_amount,
            total_reward_per_second=total_reward_per_second,
            period_ends_at=period_ends_at,
            apr=apr,
        )

    def _get_new_staking_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]:
        """Returns events of the addresses within the time range and inserts/updates
        the used query range of the addresses as well.
        """
        all_events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]] = []
        for event_type_ in AdexEventType:
            try:
                # TODO: fix. type -> overload does not work well with enum in this case
                events = self._get_staking_events_graph(  # type: ignore
                    addresses=addresses,
                    event_type=event_type_,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )
            except RemoteError:
                return []

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
        """Given an address (signer) returns its protocol user identity.
        """
        return generate_address_via_create2(
            address=HexAddress(HexStr(IDENTITY_FACTORY_ADDR)),
            salt=HexStr(CREATE2_SALT),
            init_code=HexStr(IDENTITY_PROXY_INIT_CODE.format(signer_address=address)),
        )

    def _update_channel_withdraw_events_token(
            self,
            channel_withdraws: List[ChannelWithdraw],
            fee_rewards: FeeRewards,
    ) -> None:
        if not fee_rewards:
            return None

        channel_id_token: Dict[HexStr, EthereumToken] = {}
        for entry in fee_rewards:
            try:
                channel_id = entry['channelId']
                token_address = entry['channelArgs']['tokenAddr']
                if token_address == A_DAI.ethereum_address:
                    channel_id_token[channel_id] = A_DAI
                elif token_address == A_ADX.ethereum_address:
                    channel_id_token[channel_id] = A_ADX
                else:
                    log.error(
                        'Unexpected token address processing AdEx fee rewards for '
                        'updating channel withdraw events. ',
                        channel_id=channel_id,
                        token_address=token_address,
                        entry=entry,
                    )
            except KeyError as e:
                msg = str(e)
                log.error(
                    'Error processing AdEx Tom pool fee rewards for '
                    'updating channel withdraw events. ',
                    entry=entry,
                    error=msg,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize the AdEx Tom pool fee rewards for '
                    'updating channel withdraw events. Check logs for details. Ignoring it.',
                )
                return None

        # Update token property for each channel withdraw event
        for channel_withdraw in channel_withdraws:
            channel_withdraw.token = channel_id_token.get(channel_withdraw.channel_id, None)

        return None

    def _update_events_value(
            self,
            staking_events: ADXStakingEvents,
    ) -> None:
        # Update amounts for unbonds and unbond requests
        bond_id_bond_map: Dict[HexStr, Optional[Bond]] = {
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
                msg = (
                    f'Failed to update AdEx event data. '
                    f'Unable to find the related bond event: {event}'
                )
                self.msg_aggregator.add_error(msg)

        # Update usd_value for all events
        token_usd_price_history: Dict[Tuple[EthereumToken, Timestamp], Price] = {}
        for event in staking_events.get_all():  # type: ignore # event can have all types
            # NB: channel withdraw events can have nullable token
            if isinstance(event, ChannelWithdraw):
                if event.token is None:
                    continue
                key = (event.token, event.timestamp)
                token = event.token
            else:
                key = (A_ADX, event.timestamp)
                token = A_ADX

            usd_price = token_usd_price_history.get(key, None)
            if usd_price is None:
                usd_price = PriceHistorian().query_historical_price(
                    from_asset=token,
                    to_asset=A_USD,
                    timestamp=event.timestamp,
                )

            event.value.usd_value = event.value.amount * usd_price
            token_usd_price_history[key] = usd_price

    def get_balances(
            self,
            addresses: List[ChecksumAddress],
    ) -> Dict[ChecksumAddress, List[ADXStakingBalance]]:
        """Return the addresses' balances (staked amount per pool) in the AdEx
        protocol.

        TODO: route non-premium users through on-chain query.
        """
        staking_balances: Dict[ChecksumAddress, List[ADXStakingBalance]] = {}
        is_graph_mode = self.graph and self.premium
        if is_graph_mode:
            all_events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]] = []
            for event_type_ in AdexEventType:
                try:
                    # TODO: fix. type -> overload does not work well with enum in this case
                    events = self._get_staking_events_graph(  # type: ignore
                        addresses=addresses,
                        event_type=event_type_,
                    )
                except RemoteError:
                    return staking_balances

                all_events.extend(events)

            staking_events = self._get_addresses_staking_events_grouped_by_type(
                events=all_events,
                addresses=set(addresses),
            )
            fee_rewards = self._get_tom_pool_fee_rewards_from_api()
            self._update_channel_withdraw_events_token(
                channel_withdraws=staking_events.channel_withdraws,
                fee_rewards=fee_rewards,
            )
            unclaimed_rewards = self._get_tom_pool_unclaimed_rewards(
                addresses=addresses,
                fee_rewards=fee_rewards,
            )
            adx_usd_price = Inquirer().find_usd_price(A_ADX)
            dai_usd_price = Inquirer().find_usd_price(A_DAI)
            staking_balances = self._calculate_staking_balances(
                staking_events=staking_events,
                unclaimed_rewards=unclaimed_rewards,
                adx_usd_price=adx_usd_price,
                dai_usd_price=dai_usd_price,
            )
        else:
            raise NotImplementedError(
                "Get AdEx balances for non premium user is not implemented.",
            )
        return staking_balances

    def get_events_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[ChecksumAddress, ADXStakingHistory]:
        """Get the staking history events of the addresses in the AdEx protocol.
        """
        if self.graph is None:  # could not initialize graph
            return {}

        if reset_db_data is True:
            self.database.delete_adex_events_data()

        fee_rewards = self._get_tom_pool_fee_rewards_from_api()
        staking_events = self._get_staking_events(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            fee_rewards=fee_rewards,
        )
        unclaimed_rewards = self._get_tom_pool_unclaimed_rewards(
            addresses=addresses,
            fee_rewards=fee_rewards,
        )
        adx_usd_price = Inquirer().find_usd_price(A_ADX)
        dai_usd_price = Inquirer().find_usd_price(A_DAI)
        staking_balances = self._calculate_staking_balances(
            staking_events=staking_events,
            unclaimed_rewards=unclaimed_rewards,
            adx_usd_price=adx_usd_price,
            dai_usd_price=dai_usd_price,
        )
        tom_pool_incentive = self._get_tom_pool_incentive()
        staking_history = self._get_staking_history(
            staking_balances=staking_balances,
            staking_events=staking_events,
            tom_pool_incentive=tom_pool_incentive,
        )
        return staking_history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
