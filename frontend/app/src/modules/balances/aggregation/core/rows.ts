import type { AssetBalanceWithPriceAndChains, BigNumber, ProtocolBalanceWithChains } from '@rotki/common';
import type { AggregationContext, ProtocolBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { isEvmNativeToken } from '@/modules/assets/types';
import { sortDesc, zeroBalance } from '@/modules/core/common/data/bignumbers';
import { perProtocolBalanceSum } from '@/modules/core/common/data/calculation';

/** One asset's merged balances with its totals and price, before it is shaped into a row. */
export interface AssetHolding {
  readonly asset: string;
  readonly perProtocol: ProtocolBalanceEntries;
  readonly amount: BigNumber;
  readonly value: BigNumber;
  readonly price: BigNumber;
}

export function toHolding(
  asset: string,
  perProtocol: ProtocolBalanceEntries,
  context: Pick<AggregationContext, 'priceOf'>,
): AssetHolding {
  return {
    asset,
    perProtocol,
    ...perProtocolBalanceSum(zeroBalance(), perProtocol),
    price: context.priceOf(asset),
  };
}

/** A collection header the user holds nothing of, added so the group still has its main asset on top. */
export function emptyHolding(asset: string, context: Pick<AggregationContext, 'priceOf'>): AssetHolding {
  return { asset, perProtocol: {}, ...zeroBalance(), price: context.priceOf(asset) };
}

/** Highest value first; equal values fall back to the identifier, so the order never depends on input order. */
export function compareRowsByValue(a: AssetBalanceWithPriceAndChains, b: AssetBalanceWithPriceAndChains): number {
  return sortDesc(a.value, b.value) || a.asset.localeCompare(b.asset);
}

/** The protocols holding a balance, highest value first. Only `address` carries its per-chain split. */
export function sortedProtocols(perProtocol: ProtocolBalanceEntries): ProtocolBalanceWithChains[] {
  return Object.entries(perProtocol)
    .filter(([, balance]) => balance.amount.gt(0))
    .map(([protocol, { chains, ...balance }]): ProtocolBalanceWithChains =>
      protocol === 'address' && chains ? { protocol, ...balance, chains } : { protocol, ...balance })
    .sort((a, b) => sortDesc(a.value, b.value) || a.protocol.localeCompare(b.protocol));
}

export function holdingRow(holding: AssetHolding): AssetBalanceWithPriceAndChains {
  return { ...holding, perProtocol: sortedProtocols(holding.perProtocol) };
}

/** The per-asset rows behind a group, keeping only those that actually hold a balance. */
export function breakdownRows(holdings: readonly AssetHolding[]): AssetBalanceWithPriceAndChains[] {
  return holdings
    .filter(holding => holding.amount.gt(0))
    .map(holdingRow)
    .sort(compareRowsByValue);
}

/** An asset outside any collection. A native token still carries a breakdown, which its detail view expects. */
export function standaloneRow(holding: AssetHolding): AssetBalanceWithPriceAndChains {
  return {
    ...holdingRow(holding),
    ...(isEvmNativeToken(holding.asset) ? { breakdown: breakdownRows([holding]) } : {}),
  };
}
