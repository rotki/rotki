import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import {
  type AssetBalanceWithPriceAndChains,
  type BigNumber,
  Zero,
} from '@rotki/common';
import { omit } from 'es-toolkit';
import { pipe } from 'plainfp';
import { fromNullable, match } from 'plainfp/option';
import { addBalanceEntry, type BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';
import {
  getSortedProtocolBalances,
  type IntermediateGroupRepresentation,
  type ProtocolBalancesWithManual,
  protocolBreakdown,
  singleAssetEntry,
} from '@/modules/balances/aggregation/core/balance-grouping';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { perProtocolBalanceSum } from '@/modules/core/common/data/calculation';

export type AssetProtocolBalancesWithChains = Record<string, ProtocolBalancesWithManual>;

/**
 * Converts manual balances to asset protocol balances format
 */
export function manualToAssetProtocolBalances(balances: ManualBalanceWithValue[]): AssetProtocolBalances {
  const protocolBalances: AssetProtocolBalances = {};

  for (const { amount, asset, location, value } of balances)
    addBalanceEntry(protocolBalances[asset] ??= {}, location, { amount, value });

  return protocolBalances;
}

function processAddressBalances(
  chainBalances: BlockchainAssetBalances,
  address: string | undefined,
  key: keyof EthBalance,
  aggregatedProtocolBalances: AssetProtocolBalancesWithChains,
  chainId: string,
): void {
  for (const [balanceAddress, accountBalances] of Object.entries(chainBalances)) {
    if (address && balanceAddress !== address) {
      continue;
    }

    for (const [asset, protocolBalances] of Object.entries(accountBalances[key])) {
      const assetBalances = aggregatedProtocolBalances[asset] ??= {};

      for (const [location, balance] of Object.entries(protocolBalances)) {
        const entry: BalanceEntry = location === 'address'
          ? { ...balance, chains: { [chainId]: balance } }
          : balance;
        addBalanceEntry(assetBalances, location, entry);
      }
    }
  }
}

/**
 * Converts blockchain balances to asset protocol balances format
 */
export function blockchainToAssetProtocolBalances(
  balances: Balances,
  key: keyof EthBalance = 'assets',
  chains?: string[],
  address?: string,
): AssetProtocolBalancesWithChains {
  const aggregatedProtocolBalances: AssetProtocolBalancesWithChains = {};

  for (const [chainId, chainBalances] of Object.entries(balances)) {
    // If chains filter is provided, only include specified chains
    if (chains && !chains.includes(chainId)) {
      continue;
    }
    processAddressBalances(chainBalances, address, key, aggregatedProtocolBalances, chainId);
  }

  return aggregatedProtocolBalances;
}

/**
 * Aggregates balances from different sources
 */
export function aggregateSourceBalances(
  sources: Record<string, AssetProtocolBalances | AssetProtocolBalancesWithChains>,
  resolveIdentifier: (id: string) => string,
  isAssetIgnored: (identifier: string) => boolean,
  hideIgnored: boolean,
): AssetProtocolBalancesWithChains {
  const aggregatedBalances: AssetProtocolBalancesWithChains = {};

  for (const [sourceType, source] of Object.entries(sources)) {
    const isManualSource = sourceType === 'manual';

    for (const asset in source) {
      const identifier = resolveIdentifier(asset);
      if (isAssetIgnored(identifier) && hideIgnored) {
        continue;
      }

      const assetBalances = aggregatedBalances[identifier] ??= {};

      for (const [protocol, balance] of Object.entries(source[asset]))
        addBalanceEntry(assetBalances, protocol, isManualSource ? { ...balance, containsManual: true } : balance);
    }
  }

  return aggregatedBalances;
}

/**
 * Creates an asset balance from aggregated protocol balances
 */
export function createAssetBalanceFromAggregated(
  asset: string,
  protocolBalances: ProtocolBalancesWithManual,
  getAssetPrice: (asset: string) => BigNumber,
): AssetBalanceWithPriceAndChains {
  const assetTotal = perProtocolBalanceSum(zeroBalance(), protocolBalances);
  return {
    asset,
    price: getAssetPrice(asset),
    ...assetTotal,
    perProtocol: getSortedProtocolBalances(protocolBalances),
  };
}

/** A collection's own asset may hold no balance, so it is added to the group to act as its header. */
function addCollectionMainAsset(
  groupId: string,
  groupAssets: IntermediateGroupRepresentation[],
  collectionCache: Map<string, string | undefined>,
  priceOf: (asset: string) => BigNumber,
): void {
  if (!groupId.startsWith('collection-'))
    return;

  const mainAsset = collectionCache.get(groupId.replace('collection-', ''));
  if (!mainAsset || groupAssets.some(value => value.asset === mainAsset))
    return;

  groupAssets.push({
    asset: mainAsset,
    isMain: true,
    perProtocol: {},
    ...zeroBalance(),
    price: priceOf(mainAsset),
  });
}

function chainOf(identifier: string): string {
  return identifier.slice(0, Math.max(0, identifier.indexOf('/')));
}

/**
 * The only member holding a balance, when it sits on a different chain than the main asset.
 *
 * @remarks
 * Such a group shows that member under its own identifier, since heading it with the main asset
 * would name a chain the user holds nothing on.
 */
function soleHolderOnAnotherChain(
  main: IntermediateGroupRepresentation,
  groupAssets: IntermediateGroupRepresentation[],
): IntermediateGroupRepresentation | undefined {
  const holders = groupAssets.filter(value => value.amount.gt(0));
  if (holders.length !== 1 || chainOf(holders[0].asset) === chainOf(main.asset))
    return undefined;

  return holders[0];
}

/** Folds a collection's members into one row headed by its main asset. */
function collapseCollection(
  main: IntermediateGroupRepresentation,
  groupAssets: IntermediateGroupRepresentation[],
): AssetBalanceWithPriceAndChains {
  const soleHolder = soleHolderOnAnotherChain(main, groupAssets);
  if (soleHolder) {
    const filteredAsset = omit(soleHolder, ['isMain']);
    return { ...filteredAsset, perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol) };
  }

  let groupAmount = Zero;
  let groupValue = Zero;
  const groupProtocolBalances: ProtocolBalancesWithManual = {};

  for (const asset of groupAssets) {
    groupAmount = groupAmount.plus(asset.amount);
    groupValue = groupValue.plus(asset.value);

    for (const [protocol, balance] of Object.entries(asset.perProtocol))
      addBalanceEntry(groupProtocolBalances, protocol, balance);
  }

  const filteredAsset = omit(main, ['isMain']);
  return {
    ...filteredAsset,
    amount: groupAmount,
    breakdown: protocolBreakdown(groupAssets),
    perProtocol: getSortedProtocolBalances(groupProtocolBalances),
    value: groupValue,
  };
}

export function processCollectionGrouping(
  aggregatedBalances: AssetProtocolBalancesWithChains,
  getCollectionId: (asset: string) => string | undefined,
  getCollectionMainAsset: (collectionId: string) => string | undefined,
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
  noPrice: BigNumber,
): AssetBalanceWithPriceAndChains[] {
  const grouped: Record<string, IntermediateGroupRepresentation[]> = {};
  const collectionCache = new Map<string, string | undefined>();

  for (const [asset, protocolBalances] of Object.entries(aggregatedBalances)) {
    const collectionId = getCollectionId(asset);
    const groupId = collectionId ? `collection-${collectionId}` : asset;

    let mainAsset: string | undefined;
    if (collectionId) {
      if (!collectionCache.has(collectionId)) {
        collectionCache.set(collectionId, getCollectionMainAsset(collectionId));
      }
      mainAsset = collectionCache.get(collectionId);
    }

    grouped[groupId] ??= [];
    grouped[groupId].push({
      asset,
      perProtocol: protocolBalances,
      ...perProtocolBalanceSum(zeroBalance(), protocolBalances),
      price: getAssetPrice(asset, noPrice),
      ...(mainAsset === asset ? { isMain: true } : {}),
    });
  }

  return Object.entries(grouped).flatMap(([groupId, groupAssets]) => {
    addCollectionMainAsset(groupId, groupAssets, collectionCache, asset => getAssetPrice(asset, noPrice));

    // Early return for single assets to avoid unnecessary processing
    if (groupAssets.length === 1)
      return [singleAssetEntry(groupAssets)];

    return pipe(
      fromNullable(groupAssets.find(value => value.isMain)),
      match({
        none: () => groupAssets.map(asset => singleAssetEntry([asset])),
        some: main => [collapseCollection(main, groupAssets)],
      }),
    );
  });
}
