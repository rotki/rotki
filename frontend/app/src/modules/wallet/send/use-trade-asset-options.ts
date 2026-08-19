import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { TradableAsset } from '@/modules/wallet/types';
import { Zero } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/**
 * A tradable asset with its symbol and name resolved once, so the row that renders it does not
 * have to resolve them itself.
 */
interface TradeAssetOption {
  asset: TradableAsset;
  symbol: string;
  name: string;
}

interface UseTradeAssetOptionsReturn {
  options: ComputedRef<TradeAssetOption[]>;
}

export const ALL_CHAINS = 'all';

/**
 * Builds the option list the send form's token dialog shows: the owned assets narrowed to a chain,
 * matched against the search box, and ordered for reading.
 *
 * Symbol and name are resolved here, once per asset, rather than in each row. The dialog used to
 * mount two `useAssetField` computeds per row on top of the resolution `AssetDetails` does its own,
 * which is a cost paid for every option whether or not it is on screen.
 */
export function useTradeAssetOptions(
  assets: MaybeRefOrGetter<TradableAsset[]>,
  chain: MaybeRefOrGetter<string>,
  search: MaybeRefOrGetter<string>,
  supportedChains: MaybeRefOrGetter<string[]>,
): UseTradeAssetOptionsReturn {
  const { getAssetField } = useAssetInfoRetrieval();
  const { getNativeAsset } = useSupportedChains();

  const resolved = computed<TradeAssetOption[]>(() => toValue(assets).map(asset => ({
    asset,
    name: getAssetField(asset.asset, 'name', { collectionParent: false }),
    symbol: getAssetField(asset.asset, 'symbol', { collectionParent: false }),
  })));

  const byChain = computed<TradeAssetOption[]>(() => {
    const selected = toValue(chain);
    if (selected === ALL_CHAINS) {
      const allowed = new Set(toValue(supportedChains));
      return get(resolved).filter(option => allowed.has(option.asset.chain));
    }
    return get(resolved).filter(option => option.asset.chain === selected);
  });

  /**
   * The chain's native asset first, then by fiat value, then alphabetically by symbol.
   *
   * The identifier is deliberately not the tiebreak: with no connected address nothing is priced,
   * so the tiebreak becomes the only live comparison, and ordering by `eip155:1/erc20:0x…` puts the
   * list in what reads as a random order. The symbol is what the row actually shows.
   */
  function compareForDisplay(a: TradeAssetOption, b: TradeAssetOption): number {
    const aNative = getNativeAsset(a.asset.chain) === a.asset.asset;
    const bNative = getNativeAsset(b.asset.chain) === b.asset.asset;

    if (aNative !== bNative)
      return aNative ? -1 : 1;

    const byValue = sortDesc(a.asset.fiatValue ?? Zero, b.asset.fiatValue ?? Zero);
    if (byValue !== 0)
      return byValue;

    // Fall back to the identifier when an asset has no resolved symbol yet, so the order stays
    // stable while the asset info is still loading instead of shuffling as names arrive.
    return (a.symbol || a.asset.asset).localeCompare(b.symbol || b.asset.asset);
  }

  const options = computed<TradeAssetOption[]>(() => {
    const query = toValue(search).trim().toLowerCase();
    const matching = query
      ? get(byChain).filter(option =>
          option.symbol.toLowerCase().includes(query)
          || option.name.toLowerCase().includes(query)
          // Matched too, so pasting a contract address finds its token.
          || option.asset.asset.toLowerCase().includes(query),
        )
      : get(byChain);

    return [...matching].sort(compareForDisplay);
  });

  return { options };
}
