import type { Balances } from '@/types/blockchain/accounts';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  EthBalance,
} from '@/types/blockchain/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import {
  type AssetBalanceWithPriceAndChains,
  type Balance,
  type BigNumber,
  type ProtocolBalance,
  type ProtocolBalanceWithChains,
  Zero,
} from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEvmNativeToken } from '@/types/asset';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum, perProtocolBalanceSum } from '@/utils/calculation';

type BalanceWithChains = Balance & { chains?: Record<string, Balance> };

type BalanceWithManual = Balance & { containsManual?: boolean; chains?: Record<string, Balance> };

type ProtocolBalancesWithChains = Record<string, BalanceWithChains>;

export type AssetProtocolBalancesWithChains = Record<string, ProtocolBalancesWithChains>;

type ProtocolBalancesWithManual = Record<string, BalanceWithManual>;

type AssetProtocolBalancesWithManual = Record<string, ProtocolBalancesWithManual>;

/**
 * Converts manual balances to asset protocol balances format
 */
export function manualToAssetProtocolBalances(balances: ManualBalanceWithValue[]): AssetProtocolBalances {
  const protocolBalances: AssetProtocolBalances = {};

  for (const { amount, asset, location, usdValue, value } of balances) {
    const balance: Balance = { amount, usdValue, value };

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
    const chains = existing.chains || {};
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
  associatedAssets: Record<string, string>,
  isAssetIgnored: (identifier: string) => boolean,
  hideIgnored: boolean,
): AssetProtocolBalancesWithManual {
  const aggregatedBalances: AssetProtocolBalancesWithManual = {};

  for (const [sourceType, source] of Object.entries(sources)) {
    const isManualSource = sourceType === 'manual';

    for (const asset in source) {
      const identifier = associatedAssets[asset] ?? asset;
      if (isAssetIgnored(identifier) && hideIgnored) {
        continue;
      }

      if (!aggregatedBalances[identifier]) {
        aggregatedBalances[identifier] = {};
      }

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
function getSortedProtocolBalances(protocolBalances: ProtocolBalancesWithManual): ProtocolBalanceWithChains[] {
  return Object.entries(protocolBalances)
    .filter(([, balance]) => balance.amount.gt(0))
    .map(([protocol, balance]) => {
      // Use conditional logic to determine the correct type without casting
      if (protocol === 'address' && balance.chains) {
        const result: ProtocolBalanceWithChains = {
          protocol,
          ...balance,
          chains: balance.chains,
        };
        return result;
      }

      const result: ProtocolBalance = {
        protocol,
        ...balance,
      };
      return result;
    })
    .sort((a, b) => {
      const valueComparison = sortDesc(a.value, b.value);
      if (valueComparison === 0) {
        return a.protocol.localeCompare(b.protocol);
      }
      return valueComparison;
    });
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
    usdPrice: getAssetPrice(asset),
    ...assetTotal,
    perProtocol: getSortedProtocolBalances(protocolBalances),
  };
}

interface IntermediateGroupRepresentation {
  asset: string;
  isMain?: boolean;
  perProtocol: ProtocolBalancesWithManual;
  usdValue: BigNumber;
  value: BigNumber;
  amount: BigNumber;
  usdPrice: BigNumber;
}

/**
 * Processes collection grouping
 */
export function processCollectionGrouping(
  aggregatedBalances: AssetProtocolBalancesWithManual,
  useCollectionId: (asset: string) => { value: string | undefined },
  useCollectionMainAsset: (collectionId: string) => { value: string | undefined },
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
  noPrice: BigNumber,
): AssetBalanceWithPriceAndChains[] {
  const grouped: Record<string, IntermediateGroupRepresentation[]> = {};
  const collectionCache = new Map<string, string | undefined>();

  // Group assets by collection
  for (const [asset, protocolBalances] of Object.entries(aggregatedBalances)) {
    const collectionId = useCollectionId(asset).value;
    const groupId = collectionId ? `collection-${collectionId}` : asset;

    // Cache main asset lookup to avoid repeated get() calls
    let mainAsset: string | undefined;
    if (collectionId) {
      if (!collectionCache.has(collectionId)) {
        collectionCache.set(collectionId, useCollectionMainAsset(collectionId).value);
      }
      mainAsset = collectionCache.get(collectionId);
    }

    if (!grouped[groupId]) {
      grouped[groupId] = [];
    }

    const assetTotal = perProtocolBalanceSum(zeroBalance(), protocolBalances);
    grouped[groupId].push({
      asset,
      perProtocol: protocolBalances,
      ...assetTotal,
      usdPrice: getAssetPrice(asset, noPrice),
      ...(mainAsset === asset ? { isMain: true } : {}),
    });
  }

  return Object.entries(grouped).map(([groupId, groupAssets]) => {
    // Handle collections that need main asset creation
    if (groupId.startsWith('collection-')) {
      const collectionId = groupId.replace('collection-', '');
      const mainAsset = collectionCache.get(collectionId);

      if (mainAsset && !groupAssets.some(value => value.asset === mainAsset)) {
        const zeroBalanceTotal = zeroBalance();
        groupAssets.push({
          asset: mainAsset,
          isMain: true,
          perProtocol: {},
          ...zeroBalanceTotal,
          usdPrice: getAssetPrice(mainAsset, noPrice),
        });
      }
    }

    // Early return for single assets to avoid unnecessary processing
    if (groupAssets.length === 1) {
      const asset = groupAssets[0];
      const filteredAsset = omit(asset, ['isMain']);
      return {
        ...filteredAsset,
        ...(isEvmNativeToken(asset.asset)
          ? { breakdown: groupAssets
              .filter(value => value.amount.gt(0))
              .map(value => ({
                ...omit(value, ['isMain']),
                perProtocol: getSortedProtocolBalances(value.perProtocol),
              })) }
          : {}),
        perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol),
      };
    }

    const main = groupAssets.find(value => value.isMain);
    if (!main) {
      throw new Error('Main asset not found for collection');
    }

    let groupAmount = Zero;
    let groupUsdValue = Zero;
    let groupValue = Zero;
    const groupProtocolBalances: Record<string, BalanceWithManual> = {};

    for (const asset of groupAssets) {
      groupAmount = groupAmount.plus(asset.amount);
      groupUsdValue = groupUsdValue.plus(asset.usdValue);
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
      breakdown: groupAssets
        .filter(value => value.amount.gt(0))
        .map(value => ({
          ...omit(value, ['isMain']),
          perProtocol: getSortedProtocolBalances(value.perProtocol),
        })),
      perProtocol: getSortedProtocolBalances(groupProtocolBalances),
      usdValue: groupUsdValue,
      value: groupValue,
    };
  });
}
