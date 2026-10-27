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
  /** Only these account addresses; absent means every account. */
  readonly addresses?: ReadonlySet<string>;
}

/** One account's balance under `protocol`, with each withdrawal request tagged with the account that owns it. */
function toAccountEntry(protocol: string, balance: BalanceEntry, chain: string, address: string): BalanceEntry {
  if (protocol === ADDRESS_PROTOCOL)
    return { ...balance, chains: { [chain]: balance } };

  if (!balance.claims)
    return balance;

  return { ...balance, claims: balance.claims.map(claim => ({ ...claim, account: { address, chain } })) };
}

/** Adds one account's balances on `chain`, keeping the per-chain split for the `address` protocol. */
function addAccountBalances(
  into: AssetBalanceEntries,
  chain: string,
  address: string,
  assets: AssetProtocolBalances,
): void {
  for (const [asset, protocols] of Object.entries(assets)) {
    const assetEntries = into[asset] ??= {};
    for (const [protocol, balance] of Object.entries(protocols)) {
      addBalanceEntry(assetEntries, protocol, toAccountEntry(protocol, balance, chain, address));
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
  const { addresses, chains = [], key = 'assets' } = filter;
  const entries: AssetBalanceEntries = {};

  for (const [chain, accounts] of Object.entries(balances)) {
    if (chains.length > 0 && !chains.includes(chain))
      continue;

    for (const [accountAddress, accountBalances] of Object.entries(accounts)) {
      if (!addresses || addresses.has(accountAddress))
        addAccountBalances(entries, chain, accountAddress, accountBalances[key]);
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
