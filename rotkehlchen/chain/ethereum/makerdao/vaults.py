import logging
from collections import defaultdict
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.makerdao.common import (
    MAKERDAO_REQUERY_PERIOD,
    RAY,
    RAY_DIGITS,
    WAD,
    MakerDAOCommon,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_BAT,
    A_COMP,
    A_DAI,
    A_ETH,
    A_KNC,
    A_LINK,
    A_LRC,
    A_MANA,
    A_PAX,
    A_TUSD,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_ZRX,
)
from rotkehlchen.constants.ethereum import (
    MAKERDAO_BAT_A_JOIN,
    MAKERDAO_CAT,
    MAKERDAO_CDP_MANAGER,
    MAKERDAO_COMP_A_JOIN,
    MAKERDAO_DAI_JOIN,
    MAKERDAO_ETH_A_JOIN,
    MAKERDAO_ETH_B_JOIN,
    MAKERDAO_GET_CDPS,
    MAKERDAO_JUG,
    MAKERDAO_KNC_A_JOIN,
    MAKERDAO_LINK_A_JOIN,
    MAKERDAO_LRC_A_JOIN,
    MAKERDAO_MANA_A_JOIN,
    MAKERDAO_PAXUSD_A_JOIN,
    MAKERDAO_SPOT,
    MAKERDAO_TUSD_A_JOIN,
    MAKERDAO_USDC_A_JOIN,
    MAKERDAO_USDC_B_JOIN,
    MAKERDAO_USDT_A_JOIN,
    MAKERDAO_VAT,
    MAKERDAO_WBTC_A_JOIN,
    MAKERDAO_ZRX_A_JOIN,
)
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import address_to_bytes32, hex_or_bytes_to_int, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

log = logging.getLogger(__name__)


GEMJOIN_MAPPING = {
    'BAT-A': MAKERDAO_BAT_A_JOIN,
    'ETH-A': MAKERDAO_ETH_A_JOIN,
    'ETH-B': MAKERDAO_ETH_B_JOIN,
    'KNC-A': MAKERDAO_KNC_A_JOIN,
    'TUSD-A': MAKERDAO_TUSD_A_JOIN,
    'USDC-A': MAKERDAO_USDC_A_JOIN,
    'USDC-B': MAKERDAO_USDC_B_JOIN,
    'USDT-A': MAKERDAO_USDT_A_JOIN,
    'WBTC-A': MAKERDAO_WBTC_A_JOIN,
    'ZRX-A': MAKERDAO_ZRX_A_JOIN,
    'MANA-A': MAKERDAO_MANA_A_JOIN,
    'PAXUSD-A': MAKERDAO_PAXUSD_A_JOIN,
    'COMP-A': MAKERDAO_COMP_A_JOIN,
    'LRC-A': MAKERDAO_LRC_A_JOIN,
    'LINK-A': MAKERDAO_LINK_A_JOIN,
}
COLLATERAL_TYPE_MAPPING = {
    'BAT-A': A_BAT,
    'ETH-A': A_ETH,
    'ETH-B': A_ETH,
    'KNC-A': A_KNC,
    'TUSD-A': A_TUSD,
    'USDC-A': A_USDC,
    'USDC-B': A_USDC,
    'USDT-A': A_USDT,
    'WBTC-A': A_WBTC,
    'ZRX-A': A_ZRX,
    'MANA-A': A_MANA,
    'PAXUSD-A': A_PAX,
    'COMP-A': A_COMP,
    'LRC-A': A_LRC,
    'LINK-A': A_LINK,
}


def _shift_num_right_by(num: int, digits: int) -> int:
    """Shift a number to the right by discarding some digits

    We actually use string conversion here since division can provide
    wrong results due to precision errors for very big numbers. e.g.:
    6150000000000000000000000000000000000000000000000 // 1e27
    6.149999999999999e+21   <--- wrong
    """
    return int(str(num)[:-digits])


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
    value: Balance
    timestamp: Timestamp
    tx_hash: str


class MakerDAOVault(NamedTuple):
    identifier: int
    # The type of collateral used for the vault. asset + set of parameters.
    # e.g. ETH-A. Various types can be seen here: https://catflip.co/
    collateral_type: str
    owner: ChecksumEthAddress
    collateral_asset: Asset
    # The amount/usd_value of collateral tokens locked
    collateral: Balance
    # amount/usd value of DAI drawn
    debt: Balance
    # The current collateralization_ratio of the Vault. None if nothing is locked in.
    collateralization_ratio: Optional[str]
    # The ratio at which the vault is open for liquidation. (e.g. 1.5 for 150%)
    liquidation_ratio: FVal
    # The USD price of collateral at which the Vault becomes unsafe. None if nothing is locked in.
    liquidation_price: Optional[FVal]
    urn: ChecksumEthAddress
    stability_fee: FVal

    def serialize(self) -> Dict[str, Any]:
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


class MakerDAOVaultDetails(NamedTuple):
    identifier: int
    creation_ts: Timestamp
    # Total amount of DAI owed to the vault, past and future as interest rate
    # Will be negative if vault has been liquidated. If it's negative then this
    # is the amount of DAI you managed to keep after liquidation.
    total_interest_owed: FVal
    # The total amount/usd_value of collateral that got liquidated
    total_liquidated: Balance
    events: List[VaultEvent]


def get_vault_normalized_balance(vault: MakerDAOVault) -> Balance:
    """Get the balance in the vault's collateral asset after deducting the generated debt"""
    collateral_usd_price = Inquirer().find_usd_price(vault.collateral_asset)
    normalized_usd_value = vault.collateral.usd_value - vault.debt.usd_value

    return Balance(
        amount=normalized_usd_value / collateral_usd_price,
        usd_value=normalized_usd_value,
    )


class MakerDAOVaults(MakerDAOCommon):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:

        super().__init__(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.reset_last_query_ts()
        self.lock = Semaphore()
        self.usd_price: Dict[str, FVal] = defaultdict(FVal)
        self.vault_mappings: Dict[ChecksumEthAddress, List[MakerDAOVault]] = defaultdict(list)
        self.ilk_to_stability_fee: Dict[bytes, FVal] = {}
        self.vault_details: List[MakerDAOVaultDetails] = []

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        super().reset_last_query_ts()
        self.last_vault_mapping_query_ts = 0
        self.last_vault_details_query_ts = 0

    def get_stability_fee(self, ilk: bytes) -> FVal:
        """If we already know the current stability_fee for ilk return it. If not query it"""
        if ilk in self.ilk_to_stability_fee:
            return self.ilk_to_stability_fee[ilk]

        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_JUG.address,
            abi=MAKERDAO_JUG.abi,
            method_name='ilks',
            arguments=[ilk],
        )
        # result[0] is the duty variable of the ilks in the contract
        stability_fee = FVal(result[0] / RAY) ** (YEAR_IN_SECONDS) - 1
        return stability_fee

    def _query_vault_data(
            self,
            identifier: int,
            owner: ChecksumEthAddress,
            urn: ChecksumEthAddress,
            ilk: bytes,
    ) -> Optional[MakerDAOVault]:
        collateral_type = ilk.split(b'\0', 1)[0].decode()
        asset = COLLATERAL_TYPE_MAPPING.get(collateral_type, None)
        if asset is None:
            self.msg_aggregator.add_warning(
                f'Detected vault with collateral_type {collateral_type}. That '
                f'is not yet supported by rotki. Skipping...',
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
        price = FVal((spot / RAY) * liquidation_ratio)
        self.usd_price[asset.identifier] = price
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

        dai_usd_price = Inquirer().find_usd_price(A_DAI)
        return MakerDAOVault(
            identifier=identifier,
            owner=owner,
            collateral_type=collateral_type,
            collateral_asset=asset,
            collateral=Balance(collateral_amount, collateral_usd_value),
            debt=Balance(debt_value, dai_usd_price * debt_value),
            liquidation_ratio=liquidation_ratio,
            collateralization_ratio=collateralization_ratio,
            liquidation_price=liquidation_price,
            urn=urn,
            stability_fee=self.get_stability_fee(ilk),
        )

    def _query_vault_details(
            self,
            vault: MakerDAOVault,
            proxy: ChecksumEthAddress,
            urn: ChecksumEthAddress,
    ) -> Optional[MakerDAOVaultDetails]:
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

        # get vat frob events for cross-checking
        argument_filters = {
            'sig': '0x76088703',  # frob
            'arg1': '0x' + vault.ilk.hex(),  # ilk
            'arg2': address_to_bytes32(urn),  # urn
            # arg3 can be urn for the 1st deposit, and proxy/owner for the next ones
            # so don't filter for it
            # 'arg3': address_to_bytes32(proxy),  # proxy - owner
        }
        frob_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_VAT.address,
            abi=MAKERDAO_VAT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_VAT.deployed_block,
        )
        frob_event_tx_hashes = [x['transactionHash'] for x in frob_events]

        gemjoin = GEMJOIN_MAPPING.get(vault.collateral_type, None)
        if gemjoin is None:
            self.msg_aggregator.add_warning(
                f'Unknown makerdao vault collateral type detected {vault.collateral_type}.'
                'Skipping ...',
            )
            return None

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

            if tx_hash not in frob_event_tx_hashes:
                # If there is no corresponding frob event then skip
                continue

            deposit_tx_hashes.add(tx_hash)
            amount = asset_normalized_value(
                amount=hex_or_bytes_to_int(event['topics'][3]),
                asset=vault.collateral_asset,
            )
            timestamp = self.ethereum.get_event_timestamp(event)
            usd_price = query_usd_price_or_use_default(
                asset=vault.collateral_asset,
                time=timestamp,
                default_value=ZERO,
                location='vault collateral deposit',
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.DEPOSIT_COLLATERAL,
                value=Balance(amount, amount * usd_price),
                timestamp=timestamp,
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
            tx_hash = event['transactionHash']
            if tx_hash not in frob_event_tx_hashes:
                # If there is no corresponding frob event then skip
                continue
            amount = asset_normalized_value(
                amount=hex_or_bytes_to_int(event['topics'][3]),
                asset=vault.collateral_asset,
            )
            timestamp = self.ethereum.get_event_timestamp(event)
            usd_price = query_usd_price_or_use_default(
                asset=vault.collateral_asset,
                time=timestamp,
                default_value=ZERO,
                location='vault collateral withdrawal',
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.WITHDRAW_COLLATERAL,
                value=Balance(amount, amount * usd_price),
                timestamp=timestamp,
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
            amount = token_normalized_value(
                token_amount=given_amount,
                token=A_DAI,
            )
            timestamp = self.ethereum.get_event_timestamp(event)
            usd_price = query_usd_price_or_use_default(
                asset=A_DAI,
                time=timestamp,
                default_value=FVal(1),
                location='vault debt generation',
            )
            vault_events.append(VaultEvent(
                event_type=VaultEventType.GENERATE_DEBT,
                value=Balance(amount, amount * usd_price),
                timestamp=timestamp,
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
            amount = token_normalized_value(
                token_amount=given_amount,
                token=A_DAI,
            )
            if amount == ZERO:
                # it seems there is a zero DAI value transfer from the urn when
                # withdrawing ETH. So we should ignore these as events
                continue

            timestamp = self.ethereum.get_event_timestamp(event)
            usd_price = query_usd_price_or_use_default(
                asset=A_DAI,
                time=timestamp,
                default_value=FVal(1),
                location='vault debt payback',
            )

            vault_events.append(VaultEvent(
                event_type=VaultEventType.PAYBACK_DEBT,
                value=Balance(amount, amount * usd_price),
                timestamp=timestamp,
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
            amount = asset_normalized_value(
                amount=hex_or_bytes_to_int(lot),
                asset=vault.collateral_asset,
            )
            timestamp = self.ethereum.get_event_timestamp(event)
            sum_liquidation_amount += amount
            usd_price = query_usd_price_or_use_default(
                asset=vault.collateral_asset,
                time=timestamp,
                default_value=ZERO,
                location='vault collateral liquidation',
            )
            amount_usd_value = amount * usd_price
            sum_liquidation_usd += amount_usd_value
            vault_events.append(VaultEvent(
                event_type=VaultEventType.LIQUIDATION,
                value=Balance(amount, amount_usd_value),
                timestamp=timestamp,
                tx_hash=event['transactionHash'],
            ))

        total_interest_owed = vault.debt.amount - token_normalized_value(
            token_amount=total_dai_wei,
            token=A_DAI,
        )
        # sort vault events by timestamp
        vault_events.sort(key=lambda event: event.timestamp)

        return MakerDAOVaultDetails(
            identifier=vault.identifier,
            total_interest_owed=total_interest_owed,
            creation_ts=creation_ts,
            total_liquidated=Balance(sum_liquidation_amount, sum_liquidation_usd),
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
                owner=user_address,
                urn=urn,
                ilk=result[2][idx],
            )
            if vault:
                vaults.append(vault)
                self.vault_mappings[user_address].append(vault)

        return vaults

    def get_vaults(self) -> List[MakerDAOVault]:
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
            for _, vaults in self.vault_mappings.items():
                prequeried_vaults.extend(vaults)

            prequeried_vaults.sort(key=lambda vault: vault.identifier)
            return prequeried_vaults

        with self.lock:
            self.vault_mappings = defaultdict(list)
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

    def get_vault_details(self) -> List[MakerDAOVaultDetails]:
        """Queries vault details for the auto detected vaults of the user

        This is a premium only call. Check happens only at the API level.

        If the details have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_vault_details_query_ts < MAKERDAO_REQUERY_PERIOD:
            return self.vault_details

        self.vault_details = []
        proxy_mappings = self._get_accounts_having_maker_proxy()
        # Make sure that before querying vault details there has been a recent vaults call
        vaults = self.get_vaults()
        for vault in vaults:
            proxy = proxy_mappings[vault.owner]
            vault_detail = self._query_vault_details(vault, proxy, vault.urn)
            if vault_detail:
                self.vault_details.append(vault_detail)

        # Returns vault details sorted. Oldest identifier first
        self.vault_details.sort(key=lambda details: details.identifier)
        self.last_vault_details_query_ts = ts_now()
        return self.vault_details

    def get_normalized_balances(self) -> Dict[Asset, Balance]:
        """Return a mapping of asset to balance indicating all normalized balances in vaults

        Normalized balance is defined as the balance of the collateral asset minus
        that of the generated debt.
        """
        vaults = self.get_vaults()
        balances: Dict[Asset, Balance] = defaultdict(Balance)
        for vault in vaults:
            normalized_balance = get_vault_normalized_balance(vault)
            balances[vault.collateral_asset] += normalized_balance

        return balances

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        super().on_startup()

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        super().on_account_addition(address)
        # Check if it has been added to the mapping
        proxy_address = self.proxy_mappings.get(address)
        if proxy_address:
            # get any vaults the proxy owns
            self._get_vaults_of_address(user_address=address, proxy_address=proxy_address)

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        super().on_account_removal(address)
