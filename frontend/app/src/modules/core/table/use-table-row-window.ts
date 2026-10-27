import type { MaybeElementRef } from '@vueuse/core';
import type { ComputedRef, InjectionKey, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import { clamp, isEqual } from 'es-toolkit';

const TableScrollerKey: InjectionKey<Readonly<Ref<HTMLElement | null | undefined>>> = Symbol('table-scroller');

/** Rows a table renders before it has measured anything, enough to fill a tall panel. */
const INITIAL_ROWS = 30;

/** A dense row's height, used until a rendered row has been measured. */
const ESTIMATED_ROW_HEIGHT = 41;

/** Rows rendered past each edge of the visible area, so a fast scroll does not show blank space. */
const DEFAULT_OVERSCAN = 8;

/** How the rows of a windowed table body are laid out, as last measured. */
export interface RowWindowLayout {
  rowHeight: number;
  /** Index of the expanded row, -1 when no row is expanded. */
  expandedIndex: number;
  /** Height of the details the expanded row opens under itself. */
  expandedHeight: number;
}

/** The rows a table renders: from `start` up to, not including, `end`. */
export interface RowRange {
  start: number;
  end: number;
}

/**
 * @returns the distance from the top of the body to the top of the row at `index`
 */
export function rowOffset(layout: RowWindowLayout, index: number): number {
  const { expandedHeight, expandedIndex, rowHeight } = layout;
  const below = expandedIndex >= 0 && index > expandedIndex;
  return index * rowHeight + (below ? expandedHeight : 0);
}

/**
 * @returns the index of the row covering the body offset `y`, not clamped to the rows that exist
 */
function rowAt(layout: RowWindowLayout, y: number): number {
  const { expandedHeight, expandedIndex, rowHeight } = layout;
  if (expandedIndex < 0 || y < (expandedIndex + 1) * rowHeight)
    return Math.floor(y / rowHeight);

  return Math.max(expandedIndex, Math.floor((y - expandedHeight) / rowHeight));
}

/**
 * Picks the rows to render for the part of the body between `top` and `bottom`.
 *
 * @remarks
 * The range is never empty while there are rows: a table handed no rows shows its empty state, so
 * a body scrolled fully out of view still keeps the row nearest to the visible area.
 *
 * `top` and `bottom` bound the visible area, measured from the top of the body.
 */
export function rowRange(layout: RowWindowLayout, count: number, top: number, bottom: number, overscan: number): RowRange {
  if (count === 0)
    return { end: 0, start: 0 };

  const start = clamp(rowAt(layout, top) - overscan, 0, count - 1);
  const end = clamp(rowAt(layout, bottom) + 1 + overscan, start + 1, count);
  return { end, start };
}

/**
 * Hands the tables inside a panel the element that scrolls them, so a long table renders only the
 * rows in view.
 */
export function provideTableScroller(scroller: Readonly<Ref<HTMLElement | null | undefined>>): void {
  provide(TableScrollerKey, scroller);
}

/**
 * Widens a select-all a windowed table applied to its rendered rows to every row it holds.
 *
 * @remarks
 * A selection that grew means the checkbox was checked, so every row joins; one that shrank means
 * it was cleared, so every row leaves. Ids from other tables sharing the selection are kept.
 *
 * @param previous - the selection before the table changed it
 * @param next - the selection the table applied to its rendered rows
 * @param all - the ids of every row in the table, rendered or not
 */
export function widenToggleAll(previous: string[], next: string[], all: string[]): string[] {
  if (next.length > previous.length)
    return [...new Set([...previous, ...all])];

  const cleared = new Set(all);
  return previous.filter(id => !cleared.has(id));
}

/**
 * The selection after a shift-click from `anchor` to `target`, over every row in display order.
 *
 * @remarks
 * Every row between the two, both included, takes the state the anchor has, as the table does for the
 * rows it renders. A shift-click on the anchor itself toggles it. Either id missing from `all` leaves
 * the selection as it was.
 */
export function rangeSelection(previous: string[], all: string[], anchor: string, target: string): string[] {
  const from = all.indexOf(anchor);
  const to = all.indexOf(target);
  if (from === -1 || to === -1)
    return previous;

  const select = previous.includes(anchor);
  if (from === to)
    return select ? previous.filter(id => id !== target) : [...previous, target];

  const range = all.slice(Math.min(from, to), Math.max(from, to) + 1);
  if (select)
    return [...new Set([...previous, ...range])];

  const cleared = new Set(range);
  return previous.filter(id => !cleared.has(id));
}

interface UseWindowedSelectAllOptions {
  /** Every row's id, in display order. */
  all: MaybeRefOrGetter<string[]>;
  /** The ids of the rows the table renders, in order. */
  rendered: MaybeRefOrGetter<string[]>;
  /** False for a table that renders every row, whose selection then binds as it is. */
  enabled: boolean;
}

interface UseWindowedSelectAllReturn {
  /** The selection to bind the table's `v-model` to. */
  modelSelected: WritableComputedRef<string[] | undefined>;
  /** Bind as the table's `@click.capture`, so clicks on its checkboxes are seen first. */
  onClickCapture: (event: MouseEvent) => void;
}

/** The id of the row whose checkbox cell `target` is in, read off its place among the rendered rows. */
function checkboxRowId(target: Element, rendered: string[]): string | undefined {
  const row = target.closest('tbody > tr[data-id=row]');
  if (!row?.parentElement || !target.closest('td')?.querySelector('input[type=checkbox]'))
    return undefined;
  return rendered[[...row.parentElement.querySelectorAll(':scope > tr[data-id=row]')].indexOf(row)];
}

/**
 * Makes a windowed table's selection work over every row, not only those rendered.
 *
 * @remarks
 * The table only knows the rows it renders, so on its own its header checkbox selects or clears those,
 * and a shift-click range is counted in rendered rows, which goes wrong once the window has moved.
 *
 * A click on the header checkbox is noted as it passes down to it, and the selection change it causes,
 * which the table makes in the same task, is widened with {@link widenToggleAll}. The checkbox still
 * shows the state of the rendered rows: it reads as checked once those are all selected, even while
 * rows out of view are not.
 *
 * A plain click on a row checkbox sets the anchor and goes on to the table. A shift-click is taken over:
 * it stops before the table sees it and applies {@link rangeSelection} from the anchor.
 */
export function useWindowedSelectAll(
  selected: Ref<string[] | undefined>,
  options: UseWindowedSelectAllOptions,
): UseWindowedSelectAllReturn {
  const { all, enabled, rendered } = options;
  let toggleAllClicked = false;
  let anchor: string | undefined;

  const { start: forgetClick } = useTimeoutFn(() => {
    toggleAllClicked = false;
  }, 0, { immediate: false });

  function onHeaderClick(target: Element): void {
    if (!target.closest('label, input[type=checkbox]'))
      return;

    toggleAllClicked = true;
    forgetClick();
  }

  function onRowClick(event: MouseEvent, target: Element): void {
    const id = checkboxRowId(target, toValue(rendered));
    if (id === undefined)
      return;

    if (!event.shiftKey || anchor === undefined) {
      anchor = id;
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    set(selected, rangeSelection(get(selected) ?? [], toValue(all), anchor, id));
    anchor = id;
  }

  function onClickCapture(event: MouseEvent): void {
    const target = event.target;
    if (!enabled || !(target instanceof Element))
      return;

    if (target.closest('thead'))
      onHeaderClick(target);
    else
      onRowClick(event, target);
  }

  const modelSelected = computed<string[] | undefined>({
    get: () => get(selected),
    set: (value) => {
      const widen = toggleAllClicked && value !== undefined;
      toggleAllClicked = false;
      set(selected, widen ? widenToggleAll(get(selected) ?? [], value, toValue(all)) : value);
    },
  });

  return {
    modelSelected,
    onClickCapture,
  };
}

interface UseTableRowWindowOptions {
  /** The table's root element. Its body is what gets windowed. */
  table: MaybeElementRef;
  /** False keeps every row rendered even under a scroller, for a table that is not long. */
  enabled?: boolean;
  /** Index in the rows of the expanded row, -1 when no row is expanded. */
  expandedIndex: MaybeRefOrGetter<number>;
  /** Rows rendered past each edge of the visible area. */
  overscan?: number;
}

interface UseTableRowWindowReturn<T> {
  /** Whether a scroller was provided. Without one every row renders and the paddings stay 0. */
  windowed: boolean;
  /** The rows to hand the table. */
  visibleRows: ComputedRef<T[]>;
  /** Height in pixels standing in for the rows above the rendered ones. */
  paddingTop: ComputedRef<number>;
  /** Height in pixels standing in for the rows below the rendered ones. */
  paddingBottom: ComputedRef<number>;
}

/**
 * Renders only the rows of a table that are in or near view of the provided scroller.
 *
 * @remarks
 * The caller passes `visibleRows` to the table and puts two spacer rows, `paddingTop` and
 * `paddingBottom` tall, at the top and the bottom of its body, so the scroll height stays that of
 * every row. Rows are taken to share the height of the first one rendered, apart from the expanded
 * row, whose details are measured while they render and remembered once they scroll away.
 *
 * Each table measures its own body against the scroller, so several tables stacked in one panel
 * each window themselves; one far out of view renders a single row.
 */
export function useTableRowWindow<T>(
  rows: MaybeRefOrGetter<T[]>,
  options: UseTableRowWindowOptions,
): UseTableRowWindowReturn<T> {
  const { enabled = true, expandedIndex, overscan = DEFAULT_OVERSCAN, table } = options;
  const scroller = inject(TableScrollerKey, undefined);
  const windowed = enabled && scroller !== undefined;

  const rowHeight = shallowRef<number>(ESTIMATED_ROW_HEIGHT);
  const expandedHeight = shallowRef<number>(0);
  const range = shallowRef<RowRange>({ end: INITIAL_ROWS, start: 0 });

  const layout = computed<RowWindowLayout>(() => ({
    expandedHeight: get(expandedHeight),
    expandedIndex: toValue(expandedIndex),
    rowHeight: get(rowHeight),
  }));

  /** The last measured range, cut to the rows there are now, which can be fewer since. */
  const currentRange = computed<RowRange>(() => {
    const count = toValue(rows).length;
    const { end, start } = get(range);
    return { end: Math.min(end, count), start: Math.min(start, count) };
  });

  const visibleRows = computed<T[]>(() => {
    const all = toValue(rows);
    if (!windowed)
      return all;

    const { end, start } = get(currentRange);
    return all.slice(start, end);
  });

  const paddingTop = computed<number>(() => (windowed ? rowOffset(get(layout), get(currentRange).start) : 0));

  const paddingBottom = computed<number>(() => {
    if (!windowed)
      return 0;

    const count = toValue(rows).length;
    return Math.max(0, rowOffset(get(layout), count) - rowOffset(get(layout), get(currentRange).end));
  });

  function measure(): void {
    const container = scroller ? get(scroller) : undefined;
    const body = unrefElement(table)?.querySelector('tbody');
    if (!container || !body)
      return;

    const row = body.querySelector<HTMLElement>(':scope > tr[data-id=row]');
    if (row && row.offsetHeight > 0)
      set(rowHeight, row.offsetHeight);

    const details = body.querySelector<HTMLElement>(':scope > tr[data-id=row-expanded]');
    if (details)
      set(expandedHeight, details.offsetHeight);
    else if (toValue(expandedIndex) < 0)
      set(expandedHeight, 0);

    const view = container.getBoundingClientRect();
    const bodyTop = body.getBoundingClientRect().top;
    const next = rowRange(get(layout), toValue(rows).length, view.top - bodyTop, view.bottom - bodyTop, overscan);
    if (!isEqual(next, get(range)))
      set(range, next);
  }

  let frame = 0;

  /** Measures once per frame, however many scroll events and renders ask for it. */
  function scheduleMeasure(): void {
    if (!windowed || frame !== 0)
      return;

    frame = requestAnimationFrame(() => {
      frame = 0;
      measure();
    });
  }

  if (windowed && scroller) {
    useEventListener(scroller, 'scroll', scheduleMeasure, { passive: true });
    useResizeObserver(scroller, scheduleMeasure);
    watch([(): T[] => toValue(rows), (): number => toValue(expandedIndex)], scheduleMeasure);
    onMounted(scheduleMeasure);
    onUpdated(scheduleMeasure);
    onScopeDispose((): void => cancelAnimationFrame(frame));
  }

  return {
    paddingBottom,
    paddingTop,
    visibleRows,
    windowed,
  };
}
