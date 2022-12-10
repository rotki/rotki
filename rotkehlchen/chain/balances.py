from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, DefaultDict, Literal

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.substrate.types import KusamaAddress, PolkadotAddress
from rotkehlchen.constants.assets import A_BCH, A_BTC
from rotkehlchen.types import BTCAddress, ChecksumEvmAddress, Eth2PubKey, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: 'DBHandler'  # Need this to serialize BTC accounts with xpub mappings
    eth: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    eth2: DefaultDict[Eth2PubKey, BalanceSheet] = field(init=False)
    btc: dict[BTCAddress, Balance] = field(init=False)
    bch: dict[BTCAddress, Balance] = field(init=False)
    ksm: dict[KusamaAddress, BalanceSheet] = field(init=False)
    dot: dict[PolkadotAddress, BalanceSheet] = field(init=False)
    avax: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)

    def copy(self) -> 'BlockchainBalances':
        balances = BlockchainBalances(db=self.db)
        balances.eth = self.eth.copy()
        balances.eth2 = self.eth2.copy()
        balances.btc = self.btc.copy()
        balances.bch = self.bch.copy()
        balances.ksm = self.ksm.copy()
        balances.dot = self.dot.copy()
        balances.avax = self.avax.copy()
        return balances

    def __post_init__(self) -> None:
        self.eth = defaultdict(BalanceSheet)
        self.eth2 = defaultdict(BalanceSheet)
        self.btc = defaultdict(Balance)
        self.bch = defaultdict(Balance)
        self.ksm = defaultdict(BalanceSheet)
        self.dot = defaultdict(BalanceSheet)
        self.avax = defaultdict(BalanceSheet)

    def recalculate_totals(self) -> BalanceSheet:
        """Calculate and return new balance totals based on per-account data"""
        new_totals = BalanceSheet()
        for eth_balances in self.eth.values():
            new_totals += eth_balances
        for eth2_balances in self.eth2.values():
            new_totals += eth2_balances
        for btc_balance in self.btc.values():
            new_totals.assets[A_BTC] += btc_balance
        for bch_balance in self.bch.values():
            new_totals.assets[A_BCH] += bch_balance
        for ksm_balances in self.ksm.values():
            new_totals += ksm_balances
        for dot_balances in self.dot.values():
            new_totals += dot_balances
        for avax_balances in self.avax.values():
            new_totals += avax_balances
        return new_totals

    def serialize(self) -> dict[str, dict]:
        eth_balances = {k: v.serialize() for k, v in self.eth.items()}
        eth2_balances = {k: v.serialize() for k, v in self.eth2.items()}
        btc_balances: dict[str, Any] = {}
        bch_balances: dict[str, Any] = {}
        ksm_balances = {k: v.serialize() for k, v in self.ksm.items()}
        dot_balances = {k: v.serialize() for k, v in self.dot.items()}
        avax_balances = {k: v.serialize() for k, v in self.avax.items()}

        with self.db.conn.read_ctx() as cursor:
            btc_xpub_mappings = self.db.get_addresses_to_xpub_mapping(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN,
                addresses=list(self.btc.keys()),
            )
            bch_xpub_mappings = self.db.get_addresses_to_xpub_mapping(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN_CASH,
                addresses=list(self.bch.keys()),
            )

        self._serialize_bitcoin_balances(
            xpub_mappings=btc_xpub_mappings,
            bitcoin_balances=btc_balances,
            blockchain=SupportedBlockchain.BITCOIN,
        )
        self._serialize_bitcoin_balances(
            xpub_mappings=bch_xpub_mappings,
            bitcoin_balances=bch_balances,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
        )

        blockchain_balances: dict[str, dict] = {}
        if eth_balances != {}:
            blockchain_balances['ETH'] = eth_balances
        if eth2_balances != {}:
            blockchain_balances['ETH2'] = eth2_balances
        if btc_balances != {}:
            blockchain_balances['BTC'] = btc_balances
        if bch_balances != {}:
            blockchain_balances['BCH'] = bch_balances
        if ksm_balances != {}:
            blockchain_balances['KSM'] = ksm_balances
        if dot_balances != {}:
            blockchain_balances['DOT'] = dot_balances
        if avax_balances != {}:
            blockchain_balances['AVAX'] = avax_balances

        return blockchain_balances

    def _serialize_bitcoin_balances(
        self,
        bitcoin_balances: dict[str, Any],
        xpub_mappings: dict[BTCAddress, XpubData],
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """This is a helper function to serialize the balances for BTC & BCH accounts."""
        accounts_balances: dict[BTCAddress, Balance] = getattr(self, blockchain.value.lower())
        for account, balances in accounts_balances.items():
            xpub_result = xpub_mappings.get(account, None)
            if xpub_result is None:
                if 'standalone' not in bitcoin_balances:
                    bitcoin_balances['standalone'] = {}

                addresses_dict = bitcoin_balances['standalone']
            else:
                if 'xpubs' not in bitcoin_balances:
                    bitcoin_balances['xpubs'] = []

                addresses_dict = None
                for xpub_entry in bitcoin_balances['xpubs']:
                    found = (
                        xpub_result.xpub.xpub == xpub_entry['xpub'] and
                        xpub_result.derivation_path == xpub_entry['derivation_path']
                    )
                    if found:
                        addresses_dict = xpub_entry['addresses']
                        break

                if addresses_dict is None:  # new xpub, create the mapping
                    btc_new_entry: dict[str, Any] = {
                        'xpub': xpub_result.xpub.xpub,
                        'derivation_path': xpub_result.derivation_path,
                        'addresses': {},
                    }
                    bitcoin_balances['xpubs'].append(btc_new_entry)
                    addresses_dict = btc_new_entry['addresses']

            addresses_dict[account] = balances.serialize()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class BlockchainBalancesUpdate:
    per_account: BlockchainBalances
    totals: BalanceSheet

    def serialize(self) -> dict[str, dict]:
        return {
            'per_account': self.per_account.serialize(),
            'totals': self.totals.serialize(),
        }
