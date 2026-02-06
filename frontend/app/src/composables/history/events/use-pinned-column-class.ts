import type { ComputedRef, Ref } from 'vue';

export interface ColumnClassConfig {
  class?: string;
  cellClass?: string;
}

const PINNED_HEADER_CLASS = '[&>span]:!text-xs [&>span]:!leading-3';
const PINNED_COLUMN_CLASS: ColumnClassConfig = { cellClass: '!px-2 !text-xs', class: `!px-2 ${PINNED_HEADER_CLASS}` };
const PINNED_ASSET_COLUMN_CLASS: ColumnClassConfig = { cellClass: '!pl-1 !pr-0', class: `!pl-1 !pr-0 ${PINNED_HEADER_CLASS}` };
const PINNED_SIMPLE_TABLE_CLASS = '!text-xs [&_th]:!px-2 [&_td]:!px-2 [&_td]:!py-1';

export function usePinnedColumnClass(isPinned: Ref<boolean | undefined>): ComputedRef<ColumnClassConfig> {
  return computed<ColumnClassConfig>(() =>
    get(isPinned) ? PINNED_COLUMN_CLASS : {},
  );
}

export function usePinnedAssetColumnClass(isPinned: Ref<boolean | undefined>): ComputedRef<ColumnClassConfig> {
  return computed<ColumnClassConfig>(() =>
    get(isPinned) ? PINNED_ASSET_COLUMN_CLASS : {},
  );
}

export function usePinnedSimpleTableClass(isPinned: Ref<boolean | undefined>): ComputedRef<string> {
  return computed<string>(() =>
    get(isPinned) ? PINNED_SIMPLE_TABLE_CLASS : '',
  );
}
