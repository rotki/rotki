import type { AssetBalanceWithPriceAndChains, Balance, BigNumber, ProtocolBalance, ProtocolBalanceWithChains } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEvmNativeToken } from '@/modules/assets/types';
import { sortDesc } from '@/modules/core/common/data/bignumbers';

/** A protocol balance that may have been merged from manual entries, tracking which chains fed it. */
export type BalanceWithManual = Balance & { containsManual?: boolean; chains?: Record<string, Balance> };

export type ProtocolBalancesWithManual = Record<string, BalanceWithManual>;

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

/** The per-asset rows behind a group, keeping only those that actually hold a balance. */
export function protocolBreakdown(groupAssets: IntermediateGroupRepresentation[]): AssetBalanceWithPriceAndChains[] {
  return groupAssets
    .filter(value => value.amount.gt(0))
    .map(value => ({
      ...omit(value, ['isMain']),
      perProtocol: getSortedProtocolBalances(value.perProtocol),
    }));
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
