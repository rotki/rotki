import type { MaybeRefOrGetter, Ref } from 'vue';
import type { TradeAssetOption } from '@/modules/wallet/send/use-trade-asset-options';

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
 * Arrow-key and Enter handling for the token dialog's search field.
 *
 * The list is virtualized, so every highlight move has to scroll as well: leaving the offset where
 * it was would highlight a row that is nowhere on screen.
 */
export function useTradeAssetNavigation(
  options: MaybeRefOrGetter<TradeAssetOption[]>,
  { onClose, onSelect, scrollTo }: UseTradeAssetNavigationOptions,
): UseTradeAssetNavigationReturn {
  const highlighted = shallowRef<number>(0);

  // Matched on asset AND chain. A native token id is shared across chains (ETH is the native asset
  // of ethereum, optimism, base and more), so with the chain filter on "all" the identifier alone
  // matches the wrong row and Enter would commit a different network than the one shown.
  function highlight(identifier: string, chain: string): void {
    const index = toValue(options)
      .findIndex(option => option.asset.asset === identifier && option.asset.chain === chain);
    const target = index >= 0 ? index : 0;
    set(highlighted, target);
    scrollTo(target);
  }

  // Last position the pointer was actually at.
  //
  // Any scroll slides rows under a cursor that never moved, and the browser reports that as a
  // mousemove at unchanged coordinates. Taking it at face value breaks both ways of scrolling:
  // arrow keys cannot move more than one row, because the row arriving under the pointer hands the
  // highlight straight back, and a wheel scroll drags the highlight along with it.
  let lastX = Number.NaN;
  let lastY = Number.NaN;

  // Takes the row's index rather than its identifier: the template already knows which row it is,
  // and a native token id is not unique across chains.
  function onPointerMove(event: MouseEvent, index: number): void {
    if (event.clientX === lastX && event.clientY === lastY)
      return;

    lastX = event.clientX;
    lastY = event.clientY;

    // No scrolling: the row is already under the cursor, and scrolling to it would shift the list
    // out from under the pointer.
    if (index >= 0 && index < toValue(options).length)
      set(highlighted, index);
  }

  // Which options the list holds, order-independent: picking a value can reorder the list without
  // changing its contents, and that must not count as a new list or the highlight jumps off the row
  // the user was on.
  const identifiers = computed<string>(() =>
    [...toValue(options).map(option => option.asset.asset)].sort().join(','));

  // A search that returns something different should highlight its first result, not keep an index
  // pointing into the previous list.
  watch(identifiers, () => {
    set(highlighted, 0);
    scrollTo(0);
  });

  function move(delta: number): void {
    const items = toValue(options);
    if (items.length === 0)
      return;
    const next = (get(highlighted) + delta + items.length) % items.length;
    set(highlighted, next);
    scrollTo(next);
  }

  function onKeydown(event: KeyboardEvent): void {
    // Escape is handled here rather than left to the dialog: the search field holds focus, and an
    // empty list has to be dismissable too, so this cannot sit behind the row check.
    if (event.key === 'Escape') {
      onClose();
      return;
    }

    // While an IME is composing, Enter confirms the candidate and the arrows walk the candidate
    // list. Acting on them would commit a row and close the dialog mid-word.
    if (event.isComposing)
      return;

    const items = toValue(options);
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      move(1);
    }
    else if (event.key === 'ArrowUp') {
      event.preventDefault();
      move(-1);
    }
    else if (event.key === 'Enter') {
      event.preventDefault();
      const option = items[get(highlighted)];
      if (option)
        onSelect(option);
    }
  }

  return { highlight, highlighted: readonly(highlighted), onKeydown, onPointerMove };
}
