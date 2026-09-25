import type { AssetBalanceWithPriceAndChains, BigNumber, ProtocolBalance, ProtocolBalanceWithChains } from '@rotki/common';
import type { BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';
import { omit } from 'es-toolkit';
import { isEvmNativeToken } from '@/modules/assets/types';
import { sortDesc } from '@/modules/core/common/data/bignumbers';

export type ProtocolBalancesWithManual = Record<string, BalanceEntry>;

/** Highest value first; equal values fall back to the identifier, so the order never depends on input order. */
export function compareRowsByValue(a: AssetBalanceWithPriceAndChains, b: AssetBalanceWithPriceAndChains): number {
  return sortDesc(a.value, b.value) || a.asset.localeCompare(b.asset);
}

/** An asset while its group is still being assembled, before the group collapses to one row. */
export interface IntermediateGroupRepresentation {
  asset: string;
  isMain?: boolean;
  perProtocol: ProtocolBalancesWithManual;
  value: BigNumber;
  amount: BigNumber;
  price: BigNumber;
}

export function getSortedProtocolBalances(protocolBalances: ProtocolBalancesWithManual): ProtocolBalanceWithChains[] {
  return Object.entries(protocolBalances)
    .filter(([, balance]) => balance.amount.gt(0))
    .map(([protocol, balance]) => {
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

/** The per-asset rows behind a group, keeping only those that actually hold a balance. */
export function protocolBreakdown(groupAssets: IntermediateGroupRepresentation[]): AssetBalanceWithPriceAndChains[] {
  return groupAssets
    .filter(value => value.amount.gt(0))
    .map(value => ({
      ...omit(value, ['isMain']),
      perProtocol: getSortedProtocolBalances(value.perProtocol),
    }))
    .sort(compareRowsByValue);
}

/** A lone asset needs no aggregation; a native token still carries its per-protocol breakdown. */
export function singleAssetEntry(groupAssets: IntermediateGroupRepresentation[]): AssetBalanceWithPriceAndChains {
  const [asset] = groupAssets;
  const filteredAsset = omit(asset, ['isMain']);

  return {
    ...filteredAsset,
    ...(isEvmNativeToken(asset.asset) ? { breakdown: protocolBreakdown(groupAssets) } : {}),
    perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol),
  };
}
