from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, DefaultDict, Iterator, Literal, get_args, overload

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.substrate.types import KusamaAddress, PolkadotAddress
from rotkehlchen.constants.assets import A_BCH, A_BTC
from rotkehlchen.types import (
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_EVM_CHAINS,
    SUPPORTED_NON_BITCOIN_CHAINS,
    BTCAddress,
    ChecksumEvmAddress,
    Eth2PubKey,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: 'DBHandler'  # Need this to serialize BTC accounts with xpub mappings
    eth: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    optimism: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    eth2: DefaultDict[Eth2PubKey, BalanceSheet] = field(init=False)
    btc: dict[BTCAddress, Balance] = field(init=False)
    bch: dict[BTCAddress, Balance] = field(init=False)
    ksm: dict[SubstrateAddress, BalanceSheet] = field(init=False)
    dot: dict[SubstrateAddress, BalanceSheet] = field(init=False)
    avax: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)

    @overload
    def get(self, chain: SUPPORTED_EVM_CHAINS) -> DefaultDict[ChecksumEvmAddress, BalanceSheet]:
        ...

    @overload
    def get(self, chain: SUPPORTED_BITCOIN_CHAINS) -> dict[BTCAddress, Balance]:
        ...

    @overload
    def get(self, chain: Literal[SupportedBlockchain.ETHEREUM_BEACONCHAIN]) -> DefaultDict[Eth2PubKey, BalanceSheet]:  # noqa: E501
        ...

    @overload
    def get(self, chain: SUPPORTED_SUBSTRATE_CHAINS) -> dict[SubstrateAddress, BalanceSheet]:
        ...

    @overload
    def get(self, chain: Literal[SupportedBlockchain.POLKADOT]) -> dict[PolkadotAddress, BalanceSheet]:  # noqa: E501
        ...

    def get(self, chain: SupportedBlockchain) -> dict:
        """Get the appropriate balances dict corresponding to the given chain"""
        return getattr(self, chain.get_key())

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        """Easy way to iterate through all chains

        Each iteration returns the chain shortname used in the code and the balances dict
        """
        for supported_chain in SupportedBlockchain:
            chain_key = supported_chain.get_key()
            yield (chain_key, getattr(self, chain_key))

    def chains_with_tokens(self) -> Iterator[tuple[str, dict]]:
        """
        Easy way to iterate through all but the bitcoin based chains

        Each iteration returns the chain shortname used in the code and the balances dict
        """
        for supported_chain in get_args(SUPPORTED_NON_BITCOIN_CHAINS):
            chain_key = supported_chain.get_key()
            yield (chain_key, getattr(self, chain_key))

    def bitcoin_chains(self) -> Iterator[tuple[Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH], dict]]:  # noqa: E501
        """
        Easy way to iterate through all the bitcoin based chains

        Each iteration returns the SupportedChain and the balances dict
        """
        for supported_chain in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            chain_key = supported_chain.get_key()
            # mypy fails to see it
            yield (supported_chain, getattr(self, chain_key))  # type: ignore

    def copy(self) -> 'BlockchainBalances':
        balances = BlockchainBalances(db=self.db)
        for name, attribute in self:
            setattr(balances, name, deepcopy(attribute))

        return balances

    def __post_init__(self) -> None:
        for supported_chain in SupportedBlockchain:
            chain_key = supported_chain.get_key()
            if chain_key in ('btc', 'bch'):
                setattr(self, chain_key, defaultdict(Balance))
            else:
                setattr(self, chain_key, defaultdict(BalanceSheet))

    def recalculate_totals(self) -> BalanceSheet:
        """Calculate and return new balance totals based on per-account data"""
        new_totals = BalanceSheet()
        for _, chain_attribute in self.chains_with_tokens():
            for chain_balances in chain_attribute.values():
                new_totals += chain_balances

        for btc_balance in self.btc.values():
            new_totals.assets[A_BTC] += btc_balance
        for bch_balance in self.bch.values():
            new_totals.assets[A_BCH] += bch_balance

        return new_totals

    def serialize(self) -> dict[str, dict]:
        blockchain_balances: dict[str, dict] = {}
        for chain_name, chain_attribute in self.chains_with_tokens():
            if len(chain_attribute) == 0:
                continue

            blockchain_balances[chain_name.upper()] = {k: v.serialize() for k, v in chain_attribute.items()}  # noqa: E501

        for chain, chain_attribute in self.bitcoin_chains():
            balances: dict[str, Any] = {}
            with self.db.conn.read_ctx() as cursor:
                xpub_mappings = self.db.get_addresses_to_xpub_mapping(
                    cursor=cursor,
                    blockchain=chain,
                    addresses=list(chain_attribute.keys()),
                )
                self._serialize_bitcoin_balances(
                    xpub_mappings=xpub_mappings,
                    bitcoin_balances=balances,
                    blockchain=chain,
                )
                if len(balances) != 0:
                    blockchain_balances[chain.value] = balances

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
