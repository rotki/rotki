import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { TradableAsset } from '@/modules/wallet/types';
import { getAddressFromEvmIdentifier, isEvmIdentifier, Zero } from '@rotki/common';
import { isNft } from '@/modules/assets/nft-utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/**
 * A tradable asset with its symbol and name resolved once, so the row that renders it does not
 * have to resolve them itself.
 */
export interface TradeAssetOption {
  asset: TradableAsset;
  symbol: string;
  name: string;
  /** True when another option on the same chain shows the same symbol. */
  ambiguous: boolean;
  /** Shortened contract address, used to tell ambiguous rows apart. */
  address: string;
}

interface UseTradeAssetOptionsReturn {
  /** Every tradable option, display-ordered. Drives the default selection. */
  orderedAssets: ComputedRef<TradeAssetOption[]>;
  /** `orderedAssets` narrowed to the chain and the search box. Drives the list. */
  options: ComputedRef<TradeAssetOption[]>;
}

export const ALL_CHAINS = 'all';

/**
 * Collectibles cannot be sent through this form, which moves a fungible amount. The legacy `_nft_`
 * identifiers and the CAIP `eip155:1/erc721:0x…/123` form are both in circulation.
 */
function isCollectible(identifier: string): boolean {
  return isNft(identifier) || identifier.includes('/erc721:') || identifier.includes('/erc1155:');
}

function shortenAddress(identifier: string): string {
  if (!isEvmIdentifier(identifier))
    return '';
  const address = getAddressFromEvmIdentifier(identifier);
  return address ? `${address.slice(0, 6)}…${address.slice(-4)}` : '';
}

/**
 * Builds the option list the send form's token dialog shows: the owned assets narrowed to a chain,
 * matched against the search box, and ordered for reading.
 *
 * @remarks
 * Symbol and name are resolved here, once per asset, rather than per row: a row that mounts its
 * own `useAssetField` pays that cost for every option, on screen or not, on top of the resolution
 * `AssetDetails` already does.
 */
export function useTradeAssetOptions(
  assets: MaybeRefOrGetter<TradableAsset[]>,
  chain: MaybeRefOrGetter<string>,
  search: MaybeRefOrGetter<string>,
  supportedChains: MaybeRefOrGetter<string[]>,
  /**
   * Gate on resolving symbols and names. `getAssetField` resolves through the asset info cache,
   * which **queues a backend fetch for anything it does not hold**, so reading this list eagerly
   * would fire a mapping request for the user's entire holding as soon as the send form mounts,
   * whether or not the token dialog is ever opened. The caller opens the gate when the dialog
   * first opens; until then the list orders by identifier, which needs no resolution.
   */
  resolveNames: MaybeRefOrGetter<boolean> = true,
): UseTradeAssetOptionsReturn {
  const { getAssetField } = useAssetInfoRetrieval();
  const { getNativeAsset } = useSupportedChains();

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

  const orderedAssets = computed<TradeAssetOption[]>(() => {
    const resolve = toValue(resolveNames);
    return toValue(assets)
      .filter(asset => !isCollectible(asset.asset))
      .map(asset => ({
        address: shortenAddress(asset.asset),
        ambiguous: false,
        asset,
        name: resolve ? getAssetField(asset.asset, 'name', { collectionParent: false }) : '',
        symbol: resolve ? getAssetField(asset.asset, 'symbol', { collectionParent: false }) : '',
      }))
      .sort(compareForDisplay);
  });

  const byChain = computed<TradeAssetOption[]>(() => {
    const selected = toValue(chain);
    // Built once, not inside the predicate: a Set per option is a Set per asset on every recompute.
    const allowed = new Set(toValue(supportedChains));
    const narrowed = selected === ALL_CHAINS
      ? get(orderedAssets).filter(option => allowed.has(option.asset.chain))
      : get(orderedAssets).filter(option => option.asset.chain === selected);

    // Flagged against what the list shows rather than the whole holding: two rows reading "ASK /
    // GoAsk" are indistinguishable, and only rows visible together need telling apart.
    const counts = new Map<string, number>();
    for (const option of narrowed) {
      if (option.symbol)
        counts.set(option.symbol, (counts.get(option.symbol) ?? 0) + 1);
    }

    return narrowed.map(option => ({
      ...option,
      ambiguous: (counts.get(option.symbol) ?? 0) > 1,
    }));
  });

  const options = computed<TradeAssetOption[]>(() => {
    const query = toValue(search).trim().toLowerCase();
    if (!query)
      return get(byChain);

    return get(byChain).filter(option =>
      option.symbol.toLowerCase().includes(query)
      || option.name.toLowerCase().includes(query)
      // Matched too, so pasting a contract address finds its token.
      || option.asset.asset.toLowerCase().includes(query),
    );
  });

  return { options, orderedAssets };
}
