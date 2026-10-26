import type { MaybeRefOrGetter, Ref } from 'vue';
import type { TradeAssetOption } from '@/modules/wallet/send/use-trade-asset-options';
import { useListHighlight } from '@/modules/core/common/use-list-highlight';

interface UseTradeAssetNavigationOptions {
  /** Called when the highlighted option is committed with Enter. */
  onSelect: (option: TradeAssetOption) => void;
  /** Called on Escape, so the dialog can close from the search field. */
  onClose: () => void;
  /** Brings an index into view; the list is virtualized, so moving the highlight is not enough. */
  scrollTo: (index: number) => void;
}

interface UseTradeAssetNavigationReturn {
  highlighted: Readonly<Ref<number>>;
  onKeydown: (event: KeyboardEvent) => void;
  /** Puts the highlight on a given row, or on the first one when it is not in the list. */
  highlight: (identifier: string, chain: string) => void;
  /** Moves the highlight to the hovered row, ignoring rows that slid under a still cursor. */
  onPointerMove: (event: MouseEvent, index: number) => void;
}

/**
 * Identifies an option by asset and chain together.
 *
 * @remarks
 * A native token identifier repeats across chains (ETH is native to ethereum, optimism and base
 * alike), so the identifier alone does not name a row.
 */
function optionKey(option: TradeAssetOption): string {
  return `${option.asset.asset}@${option.asset.chain}`;
}

/** Arrow-key, Enter and pointer handling for the token dialog's search field. */
export function useTradeAssetNavigation(
  options: MaybeRefOrGetter<TradeAssetOption[]>,
  { onClose, onSelect, scrollTo }: UseTradeAssetNavigationOptions,
): UseTradeAssetNavigationReturn {
  const { highlightAt, highlighted, onKeydown, onPointerMove } = useListHighlight(options, {
    keyOf: optionKey,
    onClose,
    onSelect,
    scrollTo,
  });

  /**
   * Highlights the row for one asset on one chain, falling back to the first row when it is absent.
   *
   * @remarks
   * Both halves of the key are required: with the chain filter on "all" the identifier alone lands
   * on the wrong row and Enter commits a different network than the one on screen.
   */
  function highlight(identifier: string, chain: string): void {
    const index = toValue(options)
      .findIndex(option => option.asset.asset === identifier && option.asset.chain === chain);
    highlightAt(index >= 0 ? index : 0);
  }

  return { highlight, highlighted, onKeydown, onPointerMove };
}
