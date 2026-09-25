import type { AssetBalance } from '@rotki/common';
import type { Accounts, AssetBreakdown, Balances, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { perProtocolBalanceSum } from '@/modules/core/common/data/calculation';
import { groupAssetBreakdown } from '@/modules/core/common/display/balances';

/** The balances a breakdown is read from, as the stores report them. */
export interface BreakdownInputs {
  readonly accounts: Accounts;
  readonly balances: Balances;
  readonly exchanges: ExchangeData;
  /** Manual assets, or manual liabilities for a liability breakdown. */
  readonly manual: readonly ManualBalanceWithValue[];
}

export interface BreakdownPorts {
  readonly resolveIdentifier: (identifier: string) => string;
  /** The label a chain is shown under, such as `ethereum` for `eth`. */
  readonly chainLabel: (chain: string) => string;
}

export interface BreakdownFilters {
  /** Only these chains; empty or absent means every chain with accounts. */
  readonly chains?: readonly string[];
  /** Only this account address. */
  readonly groupId?: string;
  /** Leave exchanges and manual balances out. */
  readonly blockchainOnly?: boolean;
}

/** Tags per account address on one chain, so each address is looked up once instead of scanned for. */
function tagsByAddress(chain: string, accounts: readonly BlockchainAccount[]): Map<string, string[] | undefined> {
  const tags = new Map<string, string[] | undefined>();
  for (const account of accounts) {
    const address = getAccountAddress(account);
    if (account.chain === chain && !tags.has(address))
      tags.set(address, account.tags);
  }
  return tags;
}

/**
 * Whether a balance held as `identifier` belongs in the breakdown of `asset`.
 *
 * @remarks
 * One rule for every source. Asking for `ETH` while `ETH2` is treated as `ETH` takes both, so the rows
 * add up to the merged total; asking for `ETH2` takes only `ETH2`.
 */
function countsAs(identifier: string, asset: string, ports: BreakdownPorts): boolean {
  return identifier === asset || ports.resolveIdentifier(identifier) === asset;
}

/** The account rows for `asset` on-chain, one per address and identifier held. */
function blockchainRows(
  asset: string,
  inputs: Pick<BreakdownInputs, 'accounts' | 'balances'>,
  isLiability: boolean,
  filters: BreakdownFilters,
  ports: BreakdownPorts,
): AssetBreakdown[] {
  const { chains = [], groupId } = filters;
  const key: keyof EthBalance = isLiability ? 'liabilities' : 'assets';

  return (chains.length > 0 ? chains : Object.keys(inputs.accounts)).flatMap((chain) => {
    const tags = tagsByAddress(chain, inputs.accounts[chain] ?? []);
    return Object.entries(inputs.balances[chain] ?? {})
      .filter(([address]) => !groupId || address === groupId)
      .flatMap(([address, accountBalances]) => Object.entries(accountBalances[key])
        .filter(([identifier]) => countsAs(identifier, asset, ports))
        .map(([, protocols]) => ({
          address,
          location: ports.chainLabel(chain),
          ...perProtocolBalanceSum(zeroBalance(), protocols),
          tags: tags.get(address),
        })));
  });
}

function manualRows(asset: string, manual: readonly ManualBalanceWithValue[], ports: BreakdownPorts): AssetBreakdown[] {
  return manual
    .filter(balance => countsAs(balance.asset, asset, ports))
    .map(({ amount, location, tags, value }) => ({
      address: '',
      amount,
      location,
      tags: tags && tags.length > 0 ? tags : undefined,
      value,
    }));
}

function exchangeRows(asset: string, exchanges: ExchangeData, ports: BreakdownPorts): AssetBreakdown[] {
  const rows: AssetBreakdown[] = [];
  for (const [location, assets] of Object.entries(exchanges)) {
    for (const [exchangeAsset, balance] of Object.entries(assets)) {
      if (countsAs(exchangeAsset, asset, ports))
        rows.push({ address: '', location, tags: undefined, ...balance });
    }
  }
  return rows;
}

/**
 * Where `asset` is held: one row per account, exchange and manual location, highest value first.
 *
 * @remarks
 * A chain, account or `blockchainOnly` filter narrows the rows to on-chain accounts. Exchanges never
 * hold liabilities, so a liability breakdown reads only accounts and manual liabilities.
 */
export function assetBreakdown(
  asset: string,
  inputs: BreakdownInputs,
  isLiability: boolean,
  filters: BreakdownFilters,
  ports: BreakdownPorts,
): AssetBreakdown[] {
  const { blockchainOnly = false, chains = [], groupId } = filters;
  const onlyBlockchain = chains.length > 0 || groupId !== undefined || blockchainOnly;

  const rows = [
    ...blockchainRows(asset, inputs, isLiability, filters, ports),
    ...(onlyBlockchain ? [] : manualRows(asset, inputs.manual, ports)),
    ...(onlyBlockchain || isLiability ? [] : exchangeRows(asset, inputs.exchanges, ports)),
  ];

  return groupAssetBreakdown(rows.filter(row => !!row.amount && !row.amount.isZero()));
}

/** The rows of several assets merged per location, where `locationKey` decides which locations are the same. */
export function mergedBreakdown(
  perAsset: Readonly<Record<string, readonly AssetBreakdown[]>>,
  locationKey: (row: AssetBreakdown) => string,
): AssetBreakdown[] {
  return groupAssetBreakdown(Object.values(perAsset).flat(), locationKey);
}

/** What each asset holds at one location, for the assets that hold anything there. */
export function assetsAtLocation(
  perAsset: Readonly<Record<string, readonly AssetBreakdown[]>>,
  location: string,
): AssetBalance[] {
  return Object.entries(perAsset).flatMap(([asset, rows]) => {
    const row = rows.find(entry => entry.location === location);
    return row ? [{ amount: row.amount, asset, value: row.value }] : [];
  });
}
