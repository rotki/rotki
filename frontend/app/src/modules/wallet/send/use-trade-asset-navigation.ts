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

  /**
   * Highlights the row for one asset on one chain, falling back to the first row when it is absent.
   *
   * @remarks
   * Both halves of the key are required. A native token identifier repeats across chains (ETH is
   * native to ethereum, optimism and base alike), so with the chain filter on "all" the identifier
   * alone lands on the wrong row and Enter commits a different network than the one on screen.
   */
  function highlight(identifier: string, chain: string): void {
    const index = toValue(options)
      .findIndex(option => option.asset.asset === identifier && option.asset.chain === chain);
    const target = index >= 0 ? index : 0;
    set(highlighted, target);
    scrollTo(target);
  }

  let lastX = Number.NaN;
  let lastY = Number.NaN;

  /**
   * Highlights the row under the pointer, unless the pointer itself has not moved.
   *
   * @remarks
   * Scrolling slides rows beneath a stationary cursor and the browser reports that as a mousemove
   * at unchanged coordinates, so the last real position is tracked and repeats are dropped.
   * Without that, arrow keys cannot advance more than one row (the row arriving under the pointer
   * hands the highlight straight back) and a wheel scroll drags the highlight along with it. The
   * highlight is not scrolled into view here, since the row is already under the cursor and
   * scrolling would shift the list out from under it.
   *
   * @param event - the raw `mousemove`; its coordinates are what distinguishes a move from a scroll.
   * @param index - position in the current option list; out-of-range values are ignored.
   */
  function onPointerMove(event: MouseEvent, index: number): void {
    if (event.clientX === lastX && event.clientY === lastY)
      return;

    lastX = event.clientX;
    lastY = event.clientY;

    if (index >= 0 && index < toValue(options).length)
      set(highlighted, index);
  }

  /**
   * Identifies the option list by its contents, ignoring their order.
   *
   * @remarks
   * Sorting before joining is what makes it order-independent, and that is the point: picking a
   * value reorders the list without changing what is in it, which must not read as a new list or
   * the highlight jumps off the row the user was on.
   */
  const identifiers = computed<string>(() =>
    [...toValue(options).map(option => option.asset.asset)].sort().join(','));

  /**
   * Highlights the first result whenever the list's contents change, rather than keeping an index
   * that points into the previous list.
   */
  function highlightFirstResult(): void {
    set(highlighted, 0);
    scrollTo(0);
  }

  watch(identifiers, highlightFirstResult);

  function move(delta: number): void {
    const items = toValue(options);
    if (items.length === 0)
      return;
    const next = (get(highlighted) + delta + items.length) % items.length;
    set(highlighted, next);
    scrollTo(next);
  }

  /**
   * Drives the list from the search field, which is where focus sits.
   *
   * @remarks
   * Escape is answered here rather than left to the dialog, ahead of the row check, since an empty
   * list has to be dismissable too. A composing IME is left entirely alone: there, Enter confirms
   * the candidate and the arrows walk the candidate list, so acting on either would commit a row
   * and close the dialog mid-word.
   *
   * @param event - the keydown from the search input
   */
  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      onClose();
      return;
    }

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
