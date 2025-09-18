from collections import defaultdict
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, get_args, overload

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_BCH, A_BTC
from rotkehlchen.types import (
    SUPPORTED_BITCOIN_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_NON_BITCOIN_CHAINS,
    SUPPORTED_SUBSTRATE_CHAINS_TYPE,
    BTCAddress,
    ChecksumEvmAddress,
    Eth2PubKey,
    SolanaAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


ALL_BALANCE_TYPES = (
    defaultdict[ChecksumEvmAddress, BalanceSheet] |
    dict[BTCAddress, Balance] |
    defaultdict[Eth2PubKey, BalanceSheet] |
    dict[SubstrateAddress, BalanceSheet] |
    dict[SolanaAddress, BalanceSheet]
)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: 'DBHandler'  # Need this to serialize BTC accounts with xpub mappings
    eth: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    optimism: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    polygon_pos: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    arbitrum_one: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    base: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    gnosis: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    scroll: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    binance_sc: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    eth2: defaultdict[Eth2PubKey, BalanceSheet] = field(init=False)
    btc: dict[BTCAddress, Balance] = field(init=False)
    bch: dict[BTCAddress, Balance] = field(init=False)
    ksm: dict[SubstrateAddress, BalanceSheet] = field(init=False)
    dot: dict[SubstrateAddress, BalanceSheet] = field(init=False)
    avax: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    zksync_lite: defaultdict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    solana: defaultdict[SolanaAddress, BalanceSheet] = field(init=False)

    @overload
    def get(self, chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE) -> defaultdict[ChecksumEvmAddress, BalanceSheet]:  # noqa: E501
        ...

    @overload
    def get(self, chain: SUPPORTED_BITCOIN_CHAINS_TYPE) -> dict[BTCAddress, Balance]:
        ...

    @overload
    def get(self, chain: Literal[SupportedBlockchain.ETHEREUM_BEACONCHAIN]) -> defaultdict[Eth2PubKey, BalanceSheet]:  # noqa: E501
        ...

    @overload
    def get(self, chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE) -> dict[SubstrateAddress, BalanceSheet]:
        ...

    @overload
    def get(self, chain: Literal[SupportedBlockchain.SOLANA]) -> dict[SolanaAddress, BalanceSheet]:
        ...

    @overload
    def get(self, chain: SupportedBlockchain) -> ALL_BALANCE_TYPES:
        ...

    def get(self, chain: SupportedBlockchain) -> ALL_BALANCE_TYPES:
        """Get the appropriate balances dict corresponding to the given chain"""
        return getattr(self, chain.get_key())

    @overload
    def set(self, chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, balances: defaultdict[ChecksumEvmAddress, BalanceSheet]) -> None:  # noqa: E501
        ...

    @overload
    def set(self, chain: SUPPORTED_BITCOIN_CHAINS_TYPE, balances: dict[BTCAddress, Balance]) -> None:  # noqa: E501
        ...

    @overload
    def set(self, chain: Literal[SupportedBlockchain.ETHEREUM_BEACONCHAIN], balances: defaultdict[Eth2PubKey, BalanceSheet]) -> None:  # noqa: E501
        ...

    @overload
    def set(self, chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE, balances: dict[SubstrateAddress, BalanceSheet]) -> None:  # noqa: E501
        ...

    @overload
    def set(self, chain: Literal[SupportedBlockchain.SOLANA], balances: dict[SolanaAddress, BalanceSheet]) -> None:  # noqa: E501
        ...

    @overload
    def set(self, chain: SupportedBlockchain, balances: ALL_BALANCE_TYPES) -> None:
        ...

    def set(self, chain: SupportedBlockchain, balances: ALL_BALANCE_TYPES) -> None:
        """Set the balances dict for the given chain"""
        return setattr(self, chain.get_key(), balances)

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        """Easy way to iterate through all chains

        Each iteration returns the chain shortname used in the code and the balances dict
        """
        for supported_chain in SupportedBlockchain:
            chain_key = supported_chain.get_key()
            yield (chain_key, getattr(self, chain_key))

    def chains_with_tokens(self) -> Iterator[tuple[SupportedBlockchain, dict]]:
        """
        Easy way to iterate through all but the bitcoin based chains

        Each iteration returns the chain shortname used in the code and the balances dict
        """
        for supported_chain in get_args(SUPPORTED_NON_BITCOIN_CHAINS):
            yield (supported_chain, getattr(self, supported_chain.get_key()))

    def bitcoin_chains(self) -> Iterator[tuple[Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH], dict]]:  # noqa: E501
        """
        Easy way to iterate through all the bitcoin based chains

        Each iteration returns the SupportedChain and the balances dict
        """
        for supported_chain in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            chain_key = supported_chain.get_key()
            yield (supported_chain, getattr(self, chain_key))

    def copy(self) -> 'BlockchainBalances':
        balances = BlockchainBalances(db=self.db)
        for name, attribute in self:
            setattr(balances, name, deepcopy(attribute))

        return balances

    def __post_init__(self) -> None:
        for supported_chain in SupportedBlockchain:
            chain_key = supported_chain.get_key()
            if supported_chain in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
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
            new_totals.assets[A_BTC][DEFAULT_BALANCE_LABEL] += btc_balance
        for bch_balance in self.bch.values():
            new_totals.assets[A_BCH][DEFAULT_BALANCE_LABEL] += bch_balance

        return new_totals

    def serialize(self, given_chain: SupportedBlockchain | None) -> dict[str, dict]:
        """Serializes the blockchain balances to a dict for api consumption.

        If no chain is given then all balances are serialized, while if a chain
        is given the only that chain's balances are"""
        blockchain_balances: dict[str, dict] = {}
        for chain, chain_attribute in self.chains_with_tokens():
            if len(chain_attribute) == 0 or (given_chain is not None and given_chain != chain):
                continue

            blockchain_balances[chain.serialize()] = {k: v.serialize() for k, v in chain_attribute.items()}  # noqa: E501

        for chain, chain_attribute in self.bitcoin_chains():
            if given_chain is not None and given_chain != chain:
                continue

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
                    blockchain_balances[chain.serialize()] = balances

        return blockchain_balances

    def _serialize_bitcoin_balances(
            self,
            bitcoin_balances: dict[str, Any],
            xpub_mappings: dict[BTCAddress, XpubData],
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """This is a helper function to serialize the balances for BTC & BCH accounts."""
        accounts_balances: dict[BTCAddress, Balance] = getattr(self, blockchain.get_key())
        for account, balances in accounts_balances.items():
            xpub_result = xpub_mappings.get(account)
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
    given_chain: SupportedBlockchain | None
    per_account: BlockchainBalances
    totals: BalanceSheet

    def serialize(self) -> dict[str, dict]:
        """
        Serializes a balance update in a state to be consumed by the API.

        If given_chain is None, then it's for all chains, essentially returning all per account
        balances and asset totals across all chain.
        If chain is specified then it's only per account mapping and totals for that chain
        """
        if self.given_chain is None:
            serialized_totals = self.totals.serialize()
        else:
            per_account = self.per_account.get(self.given_chain).copy()
            totals = BalanceSheet()

            if self.given_chain.is_bitcoin():
                asset = A_BTC if self.given_chain == SupportedBlockchain.BITCOIN else A_BCH
                for balance in per_account.values():
                    # we rely on value being same as symbol of chain coin
                    totals.assets[asset][DEFAULT_BALANCE_LABEL] += balance
            else:
                for balances in per_account.values():
                    totals += balances

            serialized_totals = totals.serialize()
        return {
            'per_account': self.per_account.serialize(self.given_chain),
            'totals': serialized_totals,
        }
