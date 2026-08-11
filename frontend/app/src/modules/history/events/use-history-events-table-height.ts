import type { ComponentPublicInstance, ComputedRef, ShallowRef } from 'vue';

/** Chrome that does not change height: page header, card padding, the table's own header row. */
const BASE_TABLE_HEIGHT_OFFSET = 252;

/**
 * How much vertical space the virtual table must leave for what sits above it.
 *
 * The regions passed in are the ones that change height while the page is open: the sync panel,
 * the action row and the filter chips. The virtual table needs a pixel offset rather than flex, so
 * they are measured rather than derived from layout.
 *
 * The refs are created by the caller rather than here, even though `useTemplateRef` would resolve
 * against the calling instance either way: a ref this file created would be invisible to the
 * template that declares it, and `vue/no-unused-refs` would report every one of them.
 */
export function useHistoryEventsTableHeight(
  ...regions: ShallowRef<ComponentPublicInstance | null>[]
): ComputedRef<number> {
  const heights = regions.map(region => useElementSize(region).height);

  return computed<number>(() =>
    heights.reduce((total, height) => total + get(height), BASE_TABLE_HEIGHT_OFFSET));
}
