import logging
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.manager import EthereumManager, address_to_bytes32
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.ethereum import (
    MAKERDAO_BAT_JOIN,
    MAKERDAO_CAT,
    MAKERDAO_CDP_MANAGER,
    MAKERDAO_DAI_JOIN,
    MAKERDAO_ETH_JOIN,
    MAKERDAO_GET_CDPS,
    MAKERDAO_POT,
    MAKERDAO_PROXY_REGISTRY,
    MAKERDAO_SPOT,
    MAKERDAO_USDC_JOIN,
    MAKERDAO_VAT,
    MAKERDAO_WBTC_JOIN,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    BlockchainQueryError,
    ConversionError,
    DeserializationError,
    RemoteError,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_blocknumber
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int, ts_now

log = logging.getLogger(__name__)

POT_CREATION_TIMESTAMP = 1573672721
CHI_BLOCKS_SEARCH_DISTANCE = 250  # Blocks per call query per side (before/after)
MAX_BLOCKS_TO_QUERY = 346000  # query about a month's worth of blocks in each side before giving up
REQUERY_PERIOD = 7200  # Refresh queries every 2 hours

GEMJOIN_MAPPING = {
    'ETH': MAKERDAO_ETH_JOIN,
    'BAT': MAKERDAO_BAT_JOIN,
    'USDC': MAKERDAO_USDC_JOIN,
    'WBTC': MAKERDAO_WBTC_JOIN,
}

WAD = int(1e18)
WAD_DIGITS = 18
RAY = int(1e27)
RAY_DIGITS = 27
RAD = int(1e45)
RAD_DIGITS = 45


def _shift_num_right_by(num: int, digits: int) -> int:
    """Shift a number to the right by discarding some digits

    We actually use string conversion here since division can provide
    wrong results due to precision errors for very big numbers. e.g.:
    6150000000000000000000000000000000000000000000000 // 1e27
    6.149999999999999e+21   <--- wrong
    """
    return int(str(num)[:-digits])


class ChiRetrievalError(Exception):
    pass


class VaultEventType(Enum):
    DEPOSIT_COLLATERAL = 1
    WITHDRAW_COLLATERAL = 2
    GENERATE_DEBT = 3
    PAYBACK_DEBT = 4
    LIQUIDATION = 5

    def __str__(self) -> str:
        if self == VaultEventType.DEPOSIT_COLLATERAL:
            return 'deposit'
        elif self == VaultEventType.WITHDRAW_COLLATERAL:
            return 'withdraw'
        elif self == VaultEventType.GENERATE_DEBT:
            return 'generate'
        elif self == VaultEventType.PAYBACK_DEBT:
            return 'payback'
        elif self == VaultEventType.LIQUIDATION:
            return 'liquidation'

        raise RuntimeError(f'Corrupt value {self} for VaultEventType -- Should never happen')


class VaultEvent(NamedTuple):
    event_type: VaultEventType
    amount: FVal
    timestamp: Timestamp
    tx_hash: str


class MakerDAOVault(NamedTuple):
    identifier: int
    name: str
    collateral_asset: Asset
    # The amount of collateral tokens locked
    collateral_amount: FVal
    # amount of DAI drawn
    debt_value: FVal
    # The current collateralization_ratio of the Vault. None if nothing is locked in.
    collateralization_ratio: Optional[str]
    # The ratio at which the vault is open for liquidation. (e.g. 1.5 for 150%)
    liquidation_ratio: FVal
    # The USD price of collateral at which the Vault becomes unsafe. None if nothing is locked in.
    liquidation_price: Optional[FVal]
    # The USD value of collateral locked, given the current price according to the price feed
    collateral_usd_value: FVal
    urn: ChecksumEthAddress

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        # But make sure to turn liquidation ratio to a percentage
        result['liquidation_ratio'] = self.liquidation_ratio.to_percentage(2)
        # And don't send unneeded data
        del result['urn']
        return result


class MakerDAOVaultDetails(NamedTuple):
    identifier: int
    creation_ts: Timestamp
    # Total amount of DAI owed to the vault, past and future as interest rate
    # Will be negative if vault has been liquidated. If it's negative then this
    # is the amount of DAI you managed to keep after liquidation.
    total_interest_owed: FVal
    # The total amount of collateral that got liquidated
    total_liquidated_amount: FVal
    # The total usd value of collateral that got liquidated. This is essentially
    # all liquidation events amounts multiplied by the USD price of collateral at the time.
    total_liquidated_usd: FVal
    events: List[VaultEvent]


def hex_or_bytes_to_address(value: Union[bytes, str]) -> ChecksumEthAddress:
    """Turns a 32bit bytes/HexBytes or a hexstring into an address

    May raise:
    - ConversionError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    if isinstance(value, bytes):
        hexstr = value.hex()
    else:
        hexstr = value

    return ChecksumEthAddress(to_checksum_address('0x' + hexstr[26:]))


def _find_closest_event(
        join_events: List[Dict[str, Any]],
        exit_events: List[Dict[str, Any]],
        index: int,
        comparison: Callable,
) -> Optional[Dict[str, Any]]:
    """Given lists of events and index/comparisonop find the closest event

    Index and comparisonon depend on whether we are searching for the events
    backwards or forwards.
    """
    found_event = None
    if len(join_events) != 0:
        found_event = join_events[index]
    if len(exit_events) != 0:
        if found_event:
            try:
                join_number = deserialize_blocknumber(found_event['blockNumber'])
                exit_number = deserialize_blocknumber(exit_events[index]['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR drip event block number. {str(e)}'
                raise ChiRetrievalError(msg)

            if comparison(exit_number, join_number):
                found_event = exit_events[index]
        else:
            found_event = exit_events[index]

    return found_event


def _normalize_amount(asset_symbol: str, amount: int) -> FVal:
    """Take in the big integer amount of the asset and normalizes it by decimals"""
    if asset_symbol in ('ETH', 'BAT', 'DAI'):
        return FVal(amount / WAD)
    elif asset_symbol == 'USDC':
        return FVal(amount / int(1e6))
    elif asset_symbol == 'WBTC':
        return FVal(amount / int(1e8))

    raise AssertionError('should never reach here')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMovement:
    movement_type: Literal['deposit', 'withdrawal']
    address: ChecksumEthAddress
    normalized_balance: int
    gain_so_far: int = field(init=False)
    amount: int
    block_number: int
    timestamp: Timestamp


class DSRCurrentBalances(NamedTuple):
    balances: Dict[ChecksumEthAddress, FVal]
    # The percentage of the current DSR. e.g. 8% would be 8.00
    current_dsr: FVal


class DSRAccountReport(NamedTuple):
    movements: List[DSRMovement]
    gain_so_far: int

    def serialize(self) -> Dict[str, Any]:
        serialized_report = {
            'gain_so_far': str(_dsrdai_to_dai(self.gain_so_far)),
            'movements': [],
        }
        for movement in self.movements:
            serialized_movement = {
                'movement_type': movement.movement_type,
                'gain_so_far': str(_dsrdai_to_dai(movement.gain_so_far)),
                'amount': str(_dsrdai_to_dai(movement.amount)),
                'block_number': movement.block_number,
                'timestamp': movement.timestamp,
            }
            serialized_report['movements'].append(serialized_movement)  # type: ignore
        return serialized_report


def _dsrdai_to_dai(value: Union[int, FVal]) -> FVal:
    """Turns a big integer that is the value of DAI in DSR into a proper DAI decimal FVal"""
    return FVal(value / FVal(1e27) / FVal(1e18))


class MakerDAO(EthereumModule):
    """Class to manage MakerDAO related stuff such as DSR and CDPs/Vaults"""

    def __init__(
            self,
            ethereum_manager: EthereumManager,
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.premium = premium
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.lock = Semaphore()
        self.vaults_lock = Semaphore()
        self.historical_dsr_reports: Dict[ChecksumEthAddress, DSRAccountReport] = {}
        self.last_proxy_mapping_query_ts = 0
        self.last_vault_mapping_query_ts = 0
        self.proxy_mappings: Dict[ChecksumEthAddress, ChecksumEthAddress] = {}
        self.usd_price: Dict[str, FVal] = defaultdict(FVal)
        self.vault_mappings: Dict[ChecksumEthAddress, List[MakerDAOVault]] = defaultdict(list)

    def premium_active(self) -> bool:
        return bool(self.premium and self.premium.is_active())

    def _get_account_proxy(self, address: ChecksumEthAddress) -> Optional[ChecksumEthAddress]:
        """Checks if a DSR proxy exists for the given address and returns it if it does

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_PROXY_REGISTRY.address,
            abi=MAKERDAO_PROXY_REGISTRY.abi,
            method_name='proxies',
            arguments=[address],
        )
        if int(result, 16) != 0:
            return to_checksum_address(result)
        return None

    def _get_accounts_having_maker_proxy(self) -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        """Returns a mapping of accounts that have DSR proxies to their proxies

        If the proxy mappings have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_proxy_mapping_query_ts < REQUERY_PERIOD:
            return self.proxy_mappings

        mapping = {}
        accounts = self.database.get_blockchain_accounts()
        for account in accounts.eth:
            proxy_result = self._get_account_proxy(account)
            if proxy_result:
                mapping[account] = proxy_result

        self.last_proxy_mapping_query_ts = ts_now()
        self.proxy_mappings = mapping
        return mapping

    def _query_vault_data(
            self,
            identifier: int,
            urn: ChecksumEthAddress,
            ilk: bytes,
    ) -> Optional[MakerDAOVault]:
        name = ilk.split(b'\0', 1)[0].decode()
        asset_symbol = name.split('-')[0]
        if asset_symbol not in ('ETH', 'BAT', 'USDC', 'WBTC'):
            self.msg_aggregator.add_warning(
                f'Detected vault with {asset_symbol} as collateral. That is not yet '
                f'supported by rotki',
            )
            return None

        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_VAT.address,
            abi=MAKERDAO_VAT.abi,
            method_name='urns',
            arguments=[ilk, urn],
        )
        # also known as ink in their contract
        collateral_amount = FVal(result[0] / WAD)
        normalized_debt = result[1]  # known as art in their contract
        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_VAT.address,
            abi=MAKERDAO_VAT.abi,
            method_name='ilks',
            arguments=[ilk],
        )
        rate = result[1]  # Accumulated Rates
        spot = FVal(result[2])  # Price with Safety Margin
        # How many DAI owner needs to pay back to the vault
        debt_value = FVal(((normalized_debt / WAD) * rate) / RAY)
        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_SPOT.address,
            abi=MAKERDAO_SPOT.abi,
            method_name='ilks',
            arguments=[ilk],
        )
        mat = result[1]
        liquidation_ratio = FVal(mat / RAY)
        asset = Asset(asset_symbol)
        price = FVal((spot / RAY) * liquidation_ratio)
        self.usd_price[asset_symbol] = price
        collateral_value = FVal(price * collateral_amount)
        if debt_value == 0:
            collateralization_ratio = None
        else:
            collateralization_ratio = FVal(collateral_value / debt_value).to_percentage(2)

        collateral_usd_value = price * collateral_amount
        if collateral_amount == 0:
            liquidation_price = None
        else:
            liquidation_price = (debt_value * liquidation_ratio) / collateral_amount

        return MakerDAOVault(
            identifier=identifier,
            name=name,
            collateral_asset=asset,
            collateral_amount=collateral_amount,
            debt_value=debt_value,
            liquidation_ratio=liquidation_ratio,
            collateralization_ratio=collateralization_ratio,
            collateral_usd_value=collateral_usd_value,
            liquidation_price=liquidation_price,
            urn=urn,
        )

    def _query_vault_details(
            self,
            vault: MakerDAOVault,
            proxy: ChecksumEthAddress,
            urn: ChecksumEthAddress,
    ) -> Optional[MakerDAOVaultDetails]:
        asset_symbol = vault.collateral_asset.identifier
        # They can raise:
        # ConversionError due to hex_or_bytes_to_address, hex_or_bytes_to_int
        # RemoteError due to external query errors
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_CDP_MANAGER.address,
            abi=MAKERDAO_CDP_MANAGER.abi,
            event_name='NewCdp',
            argument_filters={'cdp': vault.identifier},
            from_block=MAKERDAO_CDP_MANAGER.deployed_block,
        )
        if len(events) == 0:
            self.msg_aggregator.add_error(
                'No events found for a Vault creation. This should never '
                'happen. Please open a bug report: https://github.com/rotki/rotki/issues',
            )
            return None
        elif len(events) != 1:
            log.error(
                f'Multiple events found for a Vault creation: {events}. Taking '
                f'only the first. This should not happen. Something is wrong',
            )
            self.msg_aggregator.add_error(
                'Multiple events found for a Vault creation. This should never '
                'happen. Please open a bug report: https://github.com/rotki/rotki/issues',
            )
        creation_ts = self.ethereum.get_event_timestamp(events[0])

        gemjoin = GEMJOIN_MAPPING[vault.collateral_asset.identifier]
        vault_events = []
        # Get the collateral deposit events
        argument_filters = {
            'sig': '0x3b4da69f',  # join
            # In cases where a CDP has been migrated from a SAI CDP to a DAI
            # Vault the usr in the first deposit will be the old address. To
            # detect the first deposit in these cases we need to check for
            # arg1 being the urn
            # 'usr': proxy,
            'arg1': address_to_bytes32(urn),
        }
        events = self.ethereum.get_logs(
            contract_address=gemjoin.address,
            abi=gemjoin.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=gemjoin.deployed_block,
        )
        # all subsequent deposits should have the proxy as a usr
        # but for non-migrated CDPS the previous query would also work
        # so in those cases we will have the first deposit 2 times
        argument_filters = {
            'sig': '0x3b4da69f',  # join
            'usr': proxy,
        }
        events.extend(self.ethereum.get_logs(
            contract_address=gemjoin.address,
            abi=gemjoin.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=gemjoin.deployed_block,
        ))
        deposit_tx_hashes = set()
        for event in events:
            tx_hash = event['transactionHash']
            if tx_hash in deposit_tx_hashes:
                # Skip duplicate deposit that would be detected in non migrated CDP case
                continue
            deposit_tx_hashes.add(tx_hash)
            amount = _normalize_amount(
                asset_symbol=asset_symbol,
                amount=hex_or_bytes_to_int(event['topics'][3]),
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.DEPOSIT_COLLATERAL,
                amount=amount,
                timestamp=self.ethereum.get_event_timestamp(event),
                tx_hash=tx_hash,
            ))

        # Get the collateral withdrawal events
        argument_filters = {
            'sig': '0xef693bed',  # exit
            'usr': proxy,
        }
        events = self.ethereum.get_logs(
            contract_address=gemjoin.address,
            abi=gemjoin.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=gemjoin.deployed_block,
        )
        for event in events:
            amount = _normalize_amount(
                asset_symbol=asset_symbol,
                amount=hex_or_bytes_to_int(event['topics'][3]),
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.WITHDRAW_COLLATERAL,
                amount=amount,
                timestamp=self.ethereum.get_event_timestamp(event),
                tx_hash=event['transactionHash'],
            ))

        total_dai_wei = 0
        # Get the dai generation events
        argument_filters = {
            'sig': '0xbb35783b',  # move
            'arg1': address_to_bytes32(urn),
            # For CDPs that were created by migrating from SAI the first DAI generation
            # during vault creation will have the old owner as arg2. So we can't
            # filter for it here. Still seems like the urn as arg1 is sufficient
            # 'arg2': address_to_bytes32(proxy),
        }
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_VAT.address,
            abi=MAKERDAO_VAT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_VAT.deployed_block,
        )
        for event in events:
            given_amount = _shift_num_right_by(hex_or_bytes_to_int(event['topics'][3]), RAY_DIGITS)
            total_dai_wei += given_amount
            amount = _normalize_amount(
                asset_symbol='DAI',
                amount=given_amount,
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.GENERATE_DEBT,
                amount=amount,
                timestamp=self.ethereum.get_event_timestamp(event),
                tx_hash=event['transactionHash'],
            ))

        # Get the dai payback events
        argument_filters = {
            'sig': '0x3b4da69f',  # join
            'usr': proxy,
            'arg1': address_to_bytes32(urn),
        }
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_DAI_JOIN.address,
            abi=MAKERDAO_DAI_JOIN.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_DAI_JOIN.deployed_block,
        )
        for event in events:
            given_amount = hex_or_bytes_to_int(event['topics'][3])
            total_dai_wei -= given_amount
            amount = _normalize_amount(
                asset_symbol='DAI',
                amount=given_amount,
            )
            if amount == ZERO:
                # it seems there is a zero DAI value transfer from the urn when
                # withdrawing ETH. So we should ignore these as events
                continue
            vault_events.append(VaultEvent(
                event_type=VaultEventType.PAYBACK_DEBT,
                amount=amount,
                timestamp=self.ethereum.get_event_timestamp(event),
                tx_hash=event['transactionHash'],
            ))

        # Get the liquidation events
        argument_filters = {'urn': urn}
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_CAT.address,
            abi=MAKERDAO_CAT.abi,
            event_name='Bite',
            argument_filters=argument_filters,
            from_block=MAKERDAO_CAT.deployed_block,
        )
        sum_liquidation_amount = ZERO
        sum_liquidation_usd = ZERO
        for event in events:
            if isinstance(event['data'], str):
                lot = event['data'][:66]
            else:  # bytes
                lot = event['data'][:32]
            amount = _normalize_amount(
                asset_symbol=asset_symbol,
                amount=hex_or_bytes_to_int(lot),
            )
            timestamp = self.ethereum.get_event_timestamp(event)
            sum_liquidation_amount += amount
            usd_price = PriceHistorian().query_historical_price(
                from_asset=vault.collateral_asset,
                to_asset=A_USD,
                timestamp=timestamp,
            )
            sum_liquidation_usd += amount * usd_price
            vault_events.append(VaultEvent(
                event_type=VaultEventType.LIQUIDATION,
                amount=amount,
                timestamp=timestamp,
                tx_hash=event['transactionHash'],
            ))

        total_interest_owed = vault.debt_value - _normalize_amount(
            asset_symbol='DAI',
            amount=total_dai_wei,
        )
        # sort vault events by timestamp
        vault_events.sort(key=lambda event: event.timestamp)

        return MakerDAOVaultDetails(
            identifier=vault.identifier,
            total_interest_owed=total_interest_owed,
            creation_ts=creation_ts,
            total_liquidated_amount=sum_liquidation_amount,
            total_liquidated_usd=sum_liquidation_usd,
            events=vault_events,
        )

    def _get_vaults_of_address(
            self,
            user_address: ChecksumEthAddress,
            proxy_address: ChecksumEthAddress,
    ) -> List[MakerDAOVault]:
        """Gets the vaults of a single address

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_GET_CDPS.address,
            abi=MAKERDAO_GET_CDPS.abi,
            method_name='getCdpsAsc',
            arguments=[MAKERDAO_CDP_MANAGER.address, proxy_address],
        )

        vaults = []
        for idx, identifier in enumerate(result[0]):
            urn = to_checksum_address(result[1][idx])
            vault = self._query_vault_data(
                identifier=identifier,
                urn=urn,
                ilk=result[2][idx],
            )
            if vault:
                vaults.append(vault)
                self.vault_mappings[user_address].append(vault)

        return vaults

    def get_vaults(self) -> List[MakerDAOVault]:
        """Detects vaults the user has and returns basic info about each one

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        with self.vaults_lock:
            proxy_mappings = self._get_accounts_having_maker_proxy()
            vaults = []
            for user_address, proxy in proxy_mappings.items():
                vaults.extend(
                    self._get_vaults_of_address(user_address=user_address, proxy_address=proxy),
                )

            self.last_vault_mapping_query_ts = ts_now()
            # Returns vaults sorted. Oldest identifier first
            vaults.sort(key=lambda vault: vault.identifier)
        return vaults

    def _get_vault_mappings(self) -> Dict[ChecksumEthAddress, List[MakerDAOVault]]:
        """Returns a mapping of accounts to vault lists

        If the mappings have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_vault_mapping_query_ts < REQUERY_PERIOD:
            return self.vault_mappings

        # reset vault mappings, and set them with get_vaults
        self.vault_mappings = defaultdict(list)
        self.get_vaults()
        return self.vault_mappings

    def get_vault_details(self) -> List[MakerDAOVaultDetails]:
        """Queries vault details for the auto detected vaults of the user

        This is a premium only call

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        vault_details = []
        proxy_mappings = self._get_accounts_having_maker_proxy()
        # Make sure that before querying vault details there has been a recent vaults call
        vault_mappings = self._get_vault_mappings()
        for address, vaults in vault_mappings.items():
            proxy = proxy_mappings[address]
            for vault in vaults:
                vault_detail = self._query_vault_details(vault, proxy, vault.urn)
                if vault_detail:
                    vault_details.append(vault_detail)

        # Returns vault details sorted. Oldest identifier first
        vault_details.sort(key=lambda details: details.identifier)
        return vault_details

    def get_current_dsr(self) -> DSRCurrentBalances:
        """Gets the current DSR balance for all accounts that have DAI in DSR
        and the current DSR percentage

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        with self.lock:
            proxy_mappings = self._get_accounts_having_maker_proxy()
            balances = {}
            for account, proxy in proxy_mappings.items():
                guy_slice = self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT.address,
                    abi=MAKERDAO_POT.abi,
                    method_name='pie',
                    arguments=[proxy],
                )
                chi = self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT.address,
                    abi=MAKERDAO_POT.abi,
                    method_name='chi',
                )
                balance = _dsrdai_to_dai(guy_slice * chi)

                balances[account] = balance

            current_dsr = self.ethereum.call_contract(
                contract_address=MAKERDAO_POT.address,
                abi=MAKERDAO_POT.abi,
                method_name='dsr',
            )

            # Calculation is from here:
            # https://docs.makerdao.com/smart-contract-modules/rates-module#a-note-on-setting-rates
            current_dsr_percentage = ((FVal(current_dsr / 1e27) ** 31622400) % 1) * 100
            result = DSRCurrentBalances(balances=balances, current_dsr=current_dsr_percentage)

        return result

    def _get_vat_move_event_value(
            self,
            from_address: ChecksumEthAddress,
            to_address: ChecksumEthAddress,
            block_number: int,
            transaction_index: int,
    ) -> Optional[int]:
        """Returns values in DAI that were moved from to address at a block number and tx index

        Returns None if no value was found of if there was an error with conversion.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        arg1 = address_to_bytes32(from_address)
        arg2 = address_to_bytes32(to_address)
        argument_filters = {
            'sig': '0xbb35783b',  # move
            'arg1': arg1,  # src
            'arg2': arg2,  # dst
        }
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_VAT.address,
            abi=MAKERDAO_VAT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=block_number,
            to_block=block_number,
        )
        value = None
        for event in events:
            if event['transactionIndex'] == transaction_index:
                if value is not None:
                    log.error(  # type: ignore
                        'Mistaken assumption: There is multiple vat.move events for '
                        'the same transaction',
                    )
                try:
                    value = hex_or_bytes_to_int(event['topics'][3])
                    break
                except ConversionError:
                    value = None
        return value

    def _historical_dsr_for_account(
            self,
            account: ChecksumEthAddress,
            proxy: ChecksumEthAddress,
    ) -> DSRAccountReport:
        """Creates a historical DSR report for a single account

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        movements = []
        join_normalized_balances = []
        exit_normalized_balances = []
        argument_filters = {
            'sig': '0x049878f3',  # join
            'usr': proxy,
        }
        join_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_POT.deployed_block,
        )
        for join_event in join_events:
            try:
                wad_val = hex_or_bytes_to_int(join_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR join event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            join_normalized_balances.append(wad_val)

            # and now get the deposit amount
            try:
                block_number = deserialize_blocknumber(join_event['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR join event block number. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            dai_value = self._get_vat_move_event_value(
                from_address=proxy,
                to_address=MAKERDAO_POT.address,
                block_number=block_number,
                transaction_index=join_event['transactionIndex'],
            )
            if not dai_value:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot join. Skipping ...',
                )
                continue

            movements.append(
                DSRMovement(
                    movement_type='deposit',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=deserialize_blocknumber(join_event['blockNumber']),
                    timestamp=self.ethereum.get_event_timestamp(join_event),
                ),
            )

        argument_filters = {
            'sig': '0x7f8661a1',  # exit
            'usr': proxy,
        }
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_POT.deployed_block,
        )
        for exit_event in exit_events:
            try:
                wad_val = hex_or_bytes_to_int(exit_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR exit event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            exit_normalized_balances.append(wad_val)

            try:
                block_number = deserialize_blocknumber(exit_event['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR exit event block number. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue

            # and now get the withdrawal amount
            dai_value = self._get_vat_move_event_value(
                from_address=MAKERDAO_POT.address,
                to_address=proxy,
                block_number=block_number,
                transaction_index=exit_event['transactionIndex'],
            )
            if not dai_value:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot exit. Skipping ...',
                )
                continue

            movements.append(
                DSRMovement(
                    movement_type='withdrawal',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=deserialize_blocknumber(exit_event['blockNumber']),
                    timestamp=self.ethereum.get_event_timestamp(exit_event),
                ),
            )

        normalized_balance = 0
        amount_in_dsr = 0
        movements.sort(key=lambda x: x.block_number)

        for m in movements:
            current_chi = FVal(m.amount) / FVal(m.normalized_balance)
            gain_so_far = normalized_balance * current_chi - amount_in_dsr
            m.gain_so_far = gain_so_far.to_int(exact=False)
            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        chi = self.ethereum.call_contract(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            method_name='chi',
        )
        normalized_balance = normalized_balance * chi
        amount_in_dsr = amount_in_dsr
        gain = normalized_balance - amount_in_dsr

        return DSRAccountReport(movements=movements, gain_so_far=gain)

    def get_historical_dsr(self) -> Dict[ChecksumEthAddress, DSRAccountReport]:
        with self.lock:
            proxy_mappings = self._get_accounts_having_maker_proxy()
            reports = {}
            for account, proxy in proxy_mappings.items():
                report = self._historical_dsr_for_account(account, proxy)
                reports[account] = report

        return reports

    def _get_join_exit_events(
            self,
            from_block: int,
            to_block: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        join_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters={'sig': '0x049878f3'},  # join
            from_block=from_block,
            to_block=to_block,
        )
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters={'sig': '0x7f8661a1'},  # exit
            from_block=from_block,
            to_block=to_block,
        )
        return join_events, exit_events

    def _try_get_chi_close_to(self, time: Timestamp) -> FVal:
        """Best effort attempt to get a chi value close to the given timestamp

        It can't be 100% accurate since we use the logs of join() or exit()
        in order to find the closest time chi was changed. It also may not work
        if for some reason there is no logs in the block range we are looking for.

        Better solution would have been an archive node's query.

        May raise:
        - RemoteError if there are problems with querying etherscan
        - ChiRetrievalError if we are unable to query chi at the given timestamp
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """

        if time > 1584386100:
            # If the time is after 16/03/2020 19:15 GMT we know that
            # makerdao DSR was set to 0% we know chi has not changed
            # https://twitter.com/MakerDAO/status/1239270910810411008
            return FVal('1018008449363110619399951035')

        block_number = self.ethereum.etherscan.get_blocknumber_by_time(time)
        if self.ethereum.connected:
            latest_block = self.ethereum.web3.eth.blockNumber
        else:
            latest_block = self.ethereum.query_eth_highest_block()

        blocks_queried = 0
        counter = 1
        # Keep trying to find events that could reveal the chi to us. Go back
        # as far as MAX_BLOCKS_TO_QUERY and only then give up
        while blocks_queried < MAX_BLOCKS_TO_QUERY:
            back_from_block = max(
                MAKERDAO_POT.deployed_block,
                block_number - counter * CHI_BLOCKS_SEARCH_DISTANCE,
            )
            back_to_block = block_number - (counter - 1) * CHI_BLOCKS_SEARCH_DISTANCE
            forward_from_block = min(
                latest_block,
                block_number + (counter - 1) * CHI_BLOCKS_SEARCH_DISTANCE,
            )
            forward_to_block = min(
                latest_block,
                block_number + CHI_BLOCKS_SEARCH_DISTANCE,
            )
            back_joins, back_exits = self._get_join_exit_events(back_from_block, back_to_block)
            forward_joins, forward_exits = self._get_join_exit_events(
                from_block=forward_from_block,
                to_block=forward_to_block,
            )

            no_results = all(
                len(x) == 0 for x in (back_joins, back_exits, forward_joins, forward_exits)
            )
            if latest_block == forward_to_block and no_results:
                # if our forward querying got us to the latest block and there is
                # still no other results, then take current chi
                return self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT.address,
                    abi=MAKERDAO_POT.abi,
                    method_name='chi',
                )

            if not no_results:
                # got results!
                break

            blocks_queried += 2 * CHI_BLOCKS_SEARCH_DISTANCE
            counter += 1

        if no_results:
            raise ChiRetrievalError(
                f'Found no DSR events around timestamp {time}. Cant query chi.',
            )

        # Find the closest event to the to_block number, looking both at events
        # in the blocks before and in the blocks after block_number
        found_event = None
        back_event = _find_closest_event(back_joins, back_exits, -1, operator.gt)
        forward_event = _find_closest_event(forward_joins, forward_exits, 0, operator.lt)

        if back_event and not forward_event:
            found_event = back_event
        elif forward_event and not back_event:
            found_event = forward_event
        else:
            # We have both backward and forward events, get the one closer to block number
            try:
                back_block_number = deserialize_blocknumber(back_event['blockNumber'])  # type: ignore  # noqa: E501
                forward_block_number = deserialize_blocknumber(forward_event['blockNumber'])  # type: ignore  # noqa: E501
            except DeserializationError as e:
                msg = f'Error at reading DSR drip event block number. {str(e)}'
                raise ChiRetrievalError(msg)

            if block_number - back_block_number <= forward_block_number - block_number:
                found_event = back_event
            else:
                found_event = forward_event

        assert found_event, 'at this point found_event should be populated'  # helps mypy
        event_block_number = deserialize_blocknumber(found_event['blockNumber'])
        first_topic = found_event['topics'][0]
        if isinstance(first_topic, bytes):
            first_topic = first_topic.hex()

        if first_topic.startswith('0x049878f3'):  # join
            from_address = hex_or_bytes_to_address(found_event['topics'][1])
            to_address = MAKERDAO_POT.address
        else:
            from_address = MAKERDAO_POT.address
            to_address = hex_or_bytes_to_address(found_event['topics'][1])

        amount = self._get_vat_move_event_value(
            from_address=from_address,
            to_address=to_address,
            block_number=event_block_number,
            transaction_index=found_event['transactionIndex'],
        )
        if not amount:
            raise ChiRetrievalError(
                f'Found no VAT.move events around timestamp {time}. Cant query chi.',
            )

        wad_val = hex_or_bytes_to_int(found_event['topics'][2])
        chi = FVal(amount) / FVal(wad_val)
        return chi

    def _get_dsr_account_gain_in_period(
            self,
            movements: List[DSRMovement],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> FVal:
        """Get DSR gain for the account in a given period

        May raise:
        - ChiRetrievalError if we are unable to query chi at the given timestamp
        - RemoteError if etherscan is queried and there is a problem with the query
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        # First events show up ~432000 seconds after deployment
        if from_ts < POT_CREATION_TIMESTAMP:
            from_ts = Timestamp(POT_CREATION_TIMESTAMP + 432000)

        if to_ts < POT_CREATION_TIMESTAMP:
            to_ts = Timestamp(POT_CREATION_TIMESTAMP + 432000)

        from_chi = self._try_get_chi_close_to(from_ts)
        to_chi = self._try_get_chi_close_to(to_ts)
        normalized_balance = 0
        amount_in_dsr = 0
        gain_at_from_ts = ZERO
        gain_at_to_ts = ZERO
        gain_at_from_ts_found = False
        gain_at_to_ts_found = False
        for m in movements:
            if not gain_at_from_ts_found and m.timestamp >= from_ts:
                gain_at_from_ts = normalized_balance * from_chi - amount_in_dsr
                gain_at_from_ts_found = True

            if not gain_at_to_ts_found and m.timestamp >= to_ts:
                gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr
                gain_at_to_ts_found = True

            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        if not gain_at_from_ts_found:
            return ZERO
        if not gain_at_to_ts_found:
            gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr

        return _dsrdai_to_dai(gain_at_to_ts - gain_at_from_ts)

    def get_dsr_gains_in_period(self, from_ts: Timestamp, to_ts: Timestamp) -> FVal:
        """Get DSR gains for all accounts in a given period

        This is a best effort attempt and may also fail due to inability to find
        the required data via logs
        """
        with self.lock:
            history = self.historical_dsr_reports

        gain = ZERO
        for account, report in history.items():
            try:
                gain += self._get_dsr_account_gain_in_period(
                    movements=report.movements,
                    from_ts=from_ts,
                    to_ts=to_ts,
                )
            except (ChiRetrievalError, RemoteError, BlockchainQueryError) as e:
                self.msg_aggregator.add_warning(
                    f'Failed to get DSR gains for {account} between '
                    f'{from_ts} and {to_ts}: {str(e)}',
                )
                continue

        return gain

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        # Get the proxy of the account
        proxy_result = self._get_account_proxy(address)
        if not proxy_result:
            return

        # add it to the mapping
        self.proxy_mappings[address] = proxy_result
        # get any vaults the proxy owns
        self._get_vaults_of_address(user_address=address, proxy_address=proxy_result)

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        with self.lock:
            self.historical_dsr_reports.pop(address, 'None')
