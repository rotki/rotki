import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { samePriceAssets } from '@/modules/balances/blockchain-types';

/**
 * Every asset held in any source, as reported, plus the assets priced the same as one of them.
 *
 * @remarks
 * The twins are included because the price fetch has to cover them too: holding `ETH` needs the
 * `ETH2` price as well.
 */
export function heldAssets(sources: readonly AssetBalanceEntries[]): string[] {
  const held = new Set<string>();
  for (const source of sources) {
    for (const asset of Object.keys(source)) {
      held.add(asset);
      for (const twin of samePriceAssets[asset] ?? [])
        held.add(twin);
    }
  }
  return [...held];
}
