import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { AssetProtocolBalances, EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { addBalanceEntry, type BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';

/** The protocol key under which an account's own holdings, as opposed to protocol positions, are reported. */
const ADDRESS_PROTOCOL = 'address';

interface BlockchainSourceFilter {
  /** Whether to read held assets or liabilities. Defaults to assets. */
  readonly key?: keyof EthBalance;
  /** Only these chains; absent or empty means every chain. */
  readonly chains?: readonly string[];
  /** Only this account. */
  readonly address?: string;
}

/** Adds one account's balances on `chain`, keeping the per-chain split for the `address` protocol. */
function addAccountBalances(into: AssetBalanceEntries, chain: string, assets: AssetProtocolBalances): void {
  for (const [asset, protocols] of Object.entries(assets)) {
    const assetEntries = into[asset] ??= {};
    for (const [protocol, balance] of Object.entries(protocols)) {
      const entry: BalanceEntry = protocol === ADDRESS_PROTOCOL
        ? { ...balance, chains: { [chain]: balance } }
        : balance;
      addBalanceEntry(assetEntries, protocol, entry);
    }
  }
}

/**
 * On-chain balances, summed across accounts and chains.
 *
 * @remarks
 * The `address` protocol keeps a per-chain split in `chains`, which the protocol breakdown shows.
 */
export function fromBlockchain(balances: Balances, filter: BlockchainSourceFilter = {}): AssetBalanceEntries {
  const { address, chains = [], key = 'assets' } = filter;
  const entries: AssetBalanceEntries = {};

  for (const [chain, accounts] of Object.entries(balances)) {
    if (chains.length > 0 && !chains.includes(chain))
      continue;

    for (const [accountAddress, accountBalances] of Object.entries(accounts)) {
      if (!address || accountAddress === address)
        addAccountBalances(entries, chain, accountBalances[key]);
    }
  }

  return entries;
}

/** Exchange balances keyed by the exchange's location, optionally narrowed to one exchange. */
export function fromExchanges(exchangeBalances: ExchangeData, exchange?: string): AssetBalanceEntries {
  const entries: AssetBalanceEntries = {};

  for (const [location, assets] of Object.entries(exchangeBalances)) {
    if (exchange && exchange !== location)
      continue;

    for (const [asset, balance] of Object.entries(assets))
      addBalanceEntry(entries[asset] ??= {}, location, balance);
  }

  return entries;
}

/** Manually entered balances keyed by their location, each marked as manual. */
export function fromManual(balances: readonly ManualBalanceWithValue[]): AssetBalanceEntries {
  const entries: AssetBalanceEntries = {};

  for (const { amount, asset, location, value } of balances)
    addBalanceEntry(entries[asset] ??= {}, location, { amount, containsManual: true, value });

  return entries;
}
