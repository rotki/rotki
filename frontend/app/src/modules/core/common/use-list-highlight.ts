import type { MaybeRefOrGetter, Ref } from 'vue';

interface UseListHighlightOptions<T> {
  /** Identifies a row, so the list can tell new contents from the same rows reordered. */
  keyOf: (item: T) => string;
  /** Called when the highlighted row is committed with Enter. */
  onSelect: (item: T) => void;
  /** Called on Escape, so whatever opened the list can close it. */
  onClose: () => void;
  /** Brings an index into view; the list is virtualized, so moving the highlight is not enough. */
  scrollTo: (index: number) => void;
  /**
   * The first row the highlight may land on when the contents change. Rows before it stay
   * reachable with the arrows; they just never take the initial highlight. Defaults to 0.
   */
  firstSelectable?: MaybeRefOrGetter<number>;
}

interface UseListHighlightReturn {
  highlighted: Readonly<Ref<number>>;
  /** Puts the highlight on a row and scrolls it into view. */
  highlightAt: (index: number) => void;
  onKeydown: (event: KeyboardEvent) => void;
  /** Moves the highlight to the hovered row, ignoring rows that slid under a still cursor. */
  onPointerMove: (event: MouseEvent, index: number) => void;
}

/**
 * Keyboard and pointer highlight for a virtualized pick list driven from a search field.
 *
 * @remarks
 * The list is virtualized, so every keyboard move scrolls as well: leaving the offset where it was
 * would highlight a row that is nowhere on screen. A pointer move does not scroll, since the row is
 * already under the cursor and scrolling would slide the list out from under it.
 */
export function useListHighlight<T>(
  items: MaybeRefOrGetter<T[]>,
  { firstSelectable = 0, keyOf, onClose, onSelect, scrollTo }: UseListHighlightOptions<T>,
): UseListHighlightReturn {
  const highlighted = shallowRef<number>(0);

  function highlightAt(index: number): void {
    set(highlighted, index);
    scrollTo(index);
  }

  /**
   * Identifies the list by its contents, ignoring their order.
   *
   * @remarks
   * Sorting before joining is what makes it order-independent, and that is the point: picking a
   * value can reorder the list (a selection pinned to the top) without changing what is in it,
   * which must not read as a new list or the highlight jumps off the row the user was on.
   */
  const contents = computed<string>(() => [...toValue(items).map(keyOf)].sort().join(','));

  /**
   * Highlights the first selectable result whenever the list's contents change, rather than
   * keeping an index that points into the previous list.
   */
  function highlightFirstResult(): void {
    const count = toValue(items).length;
    const first = toValue(firstSelectable);
    highlightAt(first < count ? first : 0);
  }

  watch(contents, highlightFirstResult);

  function move(delta: number): void {
    const count = toValue(items).length;
    if (count === 0)
      return;
    highlightAt((get(highlighted) + delta + count) % count);
  }

  let lastX = Number.NaN;
  let lastY = Number.NaN;

  /**
   * Highlights the row under the pointer, unless the pointer itself has not moved.
   *
   * @remarks
   * Scrolling slides rows beneath a stationary cursor and the browser reports that as a mousemove
   * at unchanged coordinates, so the last real position is tracked and repeats are dropped.
   * Without that, the arrow keys cannot advance more than one row (the row arriving under the
   * pointer hands the highlight straight back) and a wheel scroll drags the highlight along.
   *
   * @param event - the raw `mousemove`; its coordinates are what distinguishes a move from a scroll.
   * @param index - position in the current list; out-of-range values are ignored.
   */
  function onPointerMove(event: MouseEvent, index: number): void {
    if (event.clientX === lastX && event.clientY === lastY)
      return;

    lastX = event.clientX;
    lastY = event.clientY;

    if (index >= 0 && index < toValue(items).length)
      set(highlighted, index);
  }

  /**
   * Drives the list from the search field, which is where focus sits.
   *
   * @remarks
   * A composing IME is left entirely alone, Escape included: there, Enter confirms the candidate,
   * the arrows walk the candidate list and Escape cancels it, so acting on any of them would commit
   * a row or close the list mid-word. Otherwise Escape is answered ahead of the row check, since an
   * empty list has to be dismissable too.
   *
   * @param event - the keydown from the search field
   */
  function onKeydown(event: KeyboardEvent): void {
    if (event.isComposing)
      return;

    if (event.key === 'Escape') {
      onClose();
      return;
    }

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
      const item = toValue(items)[get(highlighted)];
      if (item !== undefined)
        onSelect(item);
    }
  }

  return { highlightAt, highlighted: readonly(highlighted), onKeydown, onPointerMove };
}
