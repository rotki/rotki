import type { ComponentPublicInstance, ComputedRef, ShallowRef } from 'vue';

/** Chrome that does not change height: page header, card padding, the table's own header row. */
const BASE_TABLE_HEIGHT_OFFSET = 252;

/**
 * How much vertical space the virtual table must leave for what sits above it.
 *
 * The regions passed in are the ones that change height while the page is open (sync panel, action
 * row, filter chips). The virtual table needs a pixel offset rather than flex, so they are measured.
 *
 * The caller creates the refs, not this file: a ref created here would be invisible to the
 * template declaring it, and `vue/no-unused-refs` would report every one.
 */
export function useHistoryEventsTableHeight(
  ...regions: ShallowRef<ComponentPublicInstance | null>[]
): ComputedRef<number> {
  const heights = regions.map(region => useElementSize(region).height);

  return computed<number>(() =>
    heights.reduce((total, height) => total + get(height), BASE_TABLE_HEIGHT_OFFSET));
}
