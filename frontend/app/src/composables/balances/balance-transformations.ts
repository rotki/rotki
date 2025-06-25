import type { Balances } from '@/types/blockchain/accounts';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  EthBalance,
  ProtocolBalances,
} from '@/types/blockchain/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import { zeroBalance } from '@/utils/bignumbers';
import { balanceSum, perProtocolBalanceSum } from '@/utils/calculation';
import {
  type AssetBalanceWithPrice,
  type Balance,
  type BigNumber,
  type ProtocolBalance,
  Zero,
} from '@rotki/common';
import { omit } from 'es-toolkit';

type BalanceWithManual = Balance & { containsManual?: boolean };

type ProtocolBalancesWithManual = Record<string, BalanceWithManual>;

type AssetProtocolBalancesWithManual = Record<string, ProtocolBalancesWithManual>;

/**
 * Converts manual balances to asset protocol balances format
 */
export function manualToAssetProtocolBalances(balances: ManualBalanceWithValue[]): AssetProtocolBalances {
  const protocolBalances: AssetProtocolBalances = {};

  for (const { amount, asset, location, usdValue } of balances) {
    const balance: Balance = { amount, usdValue };

    protocolBalances[asset] ??= {};

    protocolBalances[asset][location] = protocolBalances[asset][location]
      ? balanceSum(protocolBalances[asset][location], balance)
      : balance;
  }
  return protocolBalances;
}

function processAddressBalances(
  chainBalances: BlockchainAssetBalances,
  address: string | undefined,
  key: keyof EthBalance,
  aggregatedProtocolBalances: AssetProtocolBalances,
): void {
  for (const [balanceAddress, accountBalances] of Object.entries(chainBalances)) {
    if (address && balanceAddress !== address) {
      continue;
    }
    for (const [asset, protocolBalances] of Object.entries(accountBalances[key])) {
      aggregatedProtocolBalances[asset] ??= {};

      for (const [location, balance] of Object.entries(protocolBalances)) {
        aggregatedProtocolBalances[asset][location] = aggregatedProtocolBalances[asset][location]
          ? balanceSum(aggregatedProtocolBalances[asset][location], balance)
          : balance;
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
): AssetProtocolBalances {
  const aggregatedProtocolBalances: AssetProtocolBalances = {};

  for (const [chainId, chainBalances] of Object.entries(balances)) {
    // If chains filter is provided, only include specified chains
    if (chains && !chains.includes(chainId)) {
      continue;
    }
    processAddressBalances(chainBalances, address, key, aggregatedProtocolBalances);
  }

  return aggregatedProtocolBalances;
}

/**
 * Helper function to aggregate balance for a protocol
 */
export function aggregateBalanceForProtocol(
  existingBalance: BalanceWithManual | undefined,
  newBalance: Balance,
  isManualSource: boolean,
): BalanceWithManual {
  if (!existingBalance) {
    return isManualSource
      ? { ...newBalance, containsManual: true }
      : newBalance;
  }

  const summedBalance = balanceSum(existingBalance, newBalance);
  const shouldMarkAsManual = isManualSource || existingBalance.containsManual;

  return shouldMarkAsManual
    ? { ...summedBalance, containsManual: true }
    : summedBalance;
}

/**
 * Aggregates balances from different sources
 */
export function aggregateSourceBalances(
  sources: Record<string, AssetProtocolBalances>,
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
        );
      }
    }
  }

  return aggregatedBalances;
}

/**
 * Gets sorted protocol balances
 */
export function getSortedProtocolBalances(protocolBalances: ProtocolBalancesWithManual): ProtocolBalance[] {
  return Object.entries(protocolBalances)
    .filter(([, balance]) => balance.amount.gt(0))
    .map(([protocol, balance]) => ({
      protocol,
      ...balance,
    }))
    .sort((a, b) => {
      const usdValueComparison = sortDesc(a.usdValue, b.usdValue);
      if (usdValueComparison === 0) {
        return a.protocol.localeCompare(b.protocol);
      }
      return usdValueComparison;
    });
}

/**
 * Creates an asset balance from aggregated protocol balances
 */
export function createAssetBalanceFromAggregated(
  asset: string,
  protocolBalances: ProtocolBalancesWithManual,
  getAssetPrice: (asset: string) => BigNumber,
): AssetBalanceWithPrice {
  const assetTotal = perProtocolBalanceSum(zeroBalance(), protocolBalances);
  return {
    asset,
    usdPrice: getAssetPrice(asset),
    ...assetTotal,
    perProtocol: getSortedProtocolBalances(protocolBalances),
  } satisfies AssetBalanceWithPrice;
}

// Interface for intermediate group representation
interface IntermediateGroupRepresentation {
  asset: string;
  isMain?: boolean;
  perProtocol: ProtocolBalances;
  usdValue: BigNumber;
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
): AssetBalanceWithPrice[] {
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
        perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol),
      };
    }

    // Find main asset for multi-asset groups
    const main = groupAssets.find(value => value.isMain);
    if (!main) {
      throw new Error('Main asset not found for collection');
    }

    // Calculate group totals more efficiently
    let groupAmount = Zero;
    let groupUsdValue = Zero;
    const groupProtocolBalances: Record<string, Balance> = {};

    for (const asset of groupAssets) {
      groupAmount = groupAmount.plus(asset.amount);
      groupUsdValue = groupUsdValue.plus(asset.usdValue);

      for (const [protocol, balance] of Object.entries(asset.perProtocol)) {
        groupProtocolBalances[protocol] = groupProtocolBalances[protocol]
          ? balanceSum(groupProtocolBalances[protocol], balance)
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
    } satisfies AssetBalanceWithPrice;
  });
}

// Helper function for sorting in descending order
export function sortDesc(a: BigNumber, b: BigNumber): number {
  if (a.eq(b)) {
    return 0;
  }
  return a.gt(b) ? -1 : 1;
}
