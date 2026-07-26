import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import {
  type AssetBalanceWithPriceAndChains,
  type Balance,
  type BigNumber,
  Zero,
} from '@rotki/common';
import { omit } from 'es-toolkit';
import {
  type BalanceWithManual,
  getSortedProtocolBalances,
  type IntermediateGroupRepresentation,
  type ProtocolBalancesWithManual,
  protocolBreakdown,
  singleAssetEntry,
} from '@/modules/balances/balance-grouping';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { balanceSum, perProtocolBalanceSum } from '@/modules/core/common/data/calculation';

type BalanceWithChains = Balance & { chains?: Record<string, Balance> };

type ProtocolBalancesWithChains = Record<string, BalanceWithChains>;

export type AssetProtocolBalancesWithChains = Record<string, ProtocolBalancesWithChains>;

type AssetProtocolBalancesWithManual = Record<string, ProtocolBalancesWithManual>;

/**
 * Converts manual balances to asset protocol balances format
 */
export function manualToAssetProtocolBalances(balances: ManualBalanceWithValue[]): AssetProtocolBalances {
  const protocolBalances: AssetProtocolBalances = {};

  for (const { amount, asset, location, value } of balances) {
    const balance: Balance = { amount, value };

    protocolBalances[asset] ??= {};

    protocolBalances[asset][location] = protocolBalances[asset][location]
      ? balanceSum(protocolBalances[asset][location], balance)
      : balance;
  }
  return protocolBalances;
}

function updateExistingBalance(
  existing: BalanceWithChains,
  balance: Balance,
  location: string,
  chainId?: string,
): BalanceWithChains {
  if (location === 'address' && chainId) {
    const chains = existing.chains ?? {};
    chains[chainId] = chains[chainId] ? balanceSum(chains[chainId], balance) : balance;
    return {
      ...balanceSum(existing, balance),
      chains,
    };
  }
  return balanceSum(existing, balance);
}

function createNewBalance(
  balance: Balance,
  location: string,
  chainId?: string,
): BalanceWithChains {
  if (location === 'address' && chainId) {
    return {
      ...balance,
      chains: { [chainId]: balance },
    };
  }
  return balance;
}

function processAddressBalances(
  chainBalances: BlockchainAssetBalances,
  address: string | undefined,
  key: keyof EthBalance,
  aggregatedProtocolBalances: AssetProtocolBalancesWithChains,
  chainId?: string,
): void {
  for (const [balanceAddress, accountBalances] of Object.entries(chainBalances)) {
    if (address && balanceAddress !== address) {
      continue;
    }

    for (const [asset, protocolBalances] of Object.entries(accountBalances[key])) {
      aggregatedProtocolBalances[asset] ??= {};

      for (const [location, balance] of Object.entries(protocolBalances)) {
        const existing = aggregatedProtocolBalances[asset][location];

        aggregatedProtocolBalances[asset][location] = existing
          ? updateExistingBalance(existing, balance, location, chainId)
          : createNewBalance(balance, location, chainId);
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

function mergeChains(
  existingChains: Record<string, Balance>,
  newChains: Record<string, Balance>,
): Record<string, Balance> {
  const mergedChains = { ...existingChains };
  for (const [chainId, chainBalance] of Object.entries(newChains)) {
    mergedChains[chainId] = mergedChains[chainId]
      ? balanceSum(mergedChains[chainId], chainBalance)
      : chainBalance;
  }
  return mergedChains;
}

function aggregateAddressProtocol(
  existingBalance: BalanceWithManual,
  newBalance: Balance,
  summedBalance: Balance,
  shouldMarkAsManual: boolean,
): BalanceWithManual {
  const result = shouldMarkAsManual
    ? { ...summedBalance, chains: existingBalance.chains, containsManual: true }
    : { ...summedBalance, chains: existingBalance.chains };

  const newBalanceChains = (newBalance as BalanceWithManual).chains;
  if (newBalanceChains && existingBalance.chains) {
    result.chains = mergeChains(existingBalance.chains, newBalanceChains);
  }

  return result;
}

/**
 * Helper function to aggregate balance for a protocol
 */
function aggregateBalanceForProtocol(
  existingBalance: BalanceWithManual | undefined,
  newBalance: Balance,
  isManualSource: boolean,
  protocol?: string,
): BalanceWithManual {
  if (!existingBalance) {
    return isManualSource
      ? { ...newBalance, containsManual: true }
      : newBalance;
  }

  const summedBalance = balanceSum(existingBalance, newBalance);
  const shouldMarkAsManual = isManualSource || Boolean(existingBalance.containsManual);

  if (protocol === 'address' && existingBalance.chains) {
    return aggregateAddressProtocol(existingBalance, newBalance, summedBalance, shouldMarkAsManual);
  }

  return shouldMarkAsManual
    ? { ...summedBalance, containsManual: true }
    : summedBalance;
}

/**
 * Aggregates balances from different sources
 */
export function aggregateSourceBalances(
  sources: Record<string, AssetProtocolBalances | AssetProtocolBalancesWithChains>,
  resolveIdentifier: (id: string) => string,
  isAssetIgnored: (identifier: string) => boolean,
  hideIgnored: boolean,
): AssetProtocolBalancesWithManual {
  const aggregatedBalances: AssetProtocolBalancesWithManual = {};

  for (const [sourceType, source] of Object.entries(sources)) {
    const isManualSource = sourceType === 'manual';

    for (const asset in source) {
      const identifier = resolveIdentifier(asset);
      if (isAssetIgnored(identifier) && hideIgnored) {
        continue;
      }

      aggregatedBalances[identifier] ??= {};

      for (const [protocol, balance] of Object.entries(source[asset])) {
        aggregatedBalances[identifier][protocol] = aggregateBalanceForProtocol(
          aggregatedBalances[identifier][protocol],
          balance,
          isManualSource,
          protocol,
        );
      }
    }
  }

  return aggregatedBalances;
}

/**
 * Gets sorted protocol balances
 */
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

/**
 * Processes collection grouping
 */
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

export function processCollectionGrouping(
  aggregatedBalances: AssetProtocolBalancesWithManual,
  getCollectionId: (asset: string) => string | undefined,
  getCollectionMainAsset: (collectionId: string) => string | undefined,
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
  noPrice: BigNumber,
): AssetBalanceWithPriceAndChains[] {
  const grouped: Record<string, IntermediateGroupRepresentation[]> = {};
  const collectionCache = new Map<string, string | undefined>();

  // Group assets by collection
  for (const [asset, protocolBalances] of Object.entries(aggregatedBalances)) {
    const collectionId = getCollectionId(asset);
    const groupId = collectionId ? `collection-${collectionId}` : asset;

    // Cache main asset lookup to avoid repeated calls
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

  return Object.entries(grouped).map(([groupId, groupAssets]) => {
    addCollectionMainAsset(groupId, groupAssets, collectionCache, asset => getAssetPrice(asset, noPrice));

    // Early return for single assets to avoid unnecessary processing
    if (groupAssets.length === 1)
      return singleAssetEntry(groupAssets);

    const main = groupAssets.find(value => value.isMain);
    if (!main) {
      throw new Error('Main asset not found for collection');
    }

    // When only one asset has balance from a different chain, use its real identifier
    const assetsWithBalance = groupAssets.filter(value => value.amount.gt(0));
    if (assetsWithBalance.length === 1) {
      const actualAsset = assetsWithBalance[0];
      const chainOf = (id: string): string => id.slice(0, Math.max(0, id.indexOf('/')));
      if (chainOf(actualAsset.asset) !== chainOf(main.asset)) {
        const filteredAsset = omit(actualAsset, ['isMain']);
        return { ...filteredAsset, perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol) };
      }
    }

    let groupAmount = Zero;
    let groupValue = Zero;
    const groupProtocolBalances: Record<string, BalanceWithManual> = {};

    for (const asset of groupAssets) {
      groupAmount = groupAmount.plus(asset.amount);
      groupValue = groupValue.plus(asset.value);

      for (const [protocol, balance] of Object.entries(asset.perProtocol)) {
        const existing = groupProtocolBalances[protocol];
        groupProtocolBalances[protocol] = existing
          ? aggregateBalanceForProtocol(existing, balance, false, protocol)
          : balance;
      }
    }

    const filteredAsset = omit(main, ['isMain']);
    return {
      ...filteredAsset,
      amount: groupAmount,
      breakdown: protocolBreakdown(groupAssets),
      perProtocol: getSortedProtocolBalances(groupProtocolBalances),
      value: groupValue,
    };
  });
}
