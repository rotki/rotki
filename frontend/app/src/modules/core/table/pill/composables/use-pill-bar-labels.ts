import type { ComputedRef } from 'vue';
import type { PillBarLabels } from '@/modules/core/table/pill/core/types';

/**
 * The bar's own copy, which says nothing about the table it filters: "Add filter", "Clear all",
 * and the rest read the same wherever the bar is used. Kept in one place so a second table does
 * not restate seven strings that would then drift apart, and because the pill components
 * deliberately never call `useI18n` themselves.
 */
export function usePillBarLabels(): ComputedRef<PillBarLabels> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<PillBarLabels>(() => ({
    add: t('table_filter.pill.add'),
    clear: t('table_filter.pill.clear'),
    empty: t('table_filter.pill.empty'),
    narrow: t('table_filter.pill.narrow'),
    narrowEmpty: t('table_filter.pill.narrow_empty'),
    remove: t('table_filter.pill.remove'),
    search: t('table_filter.pill.search'),
    syntax: t('table_filter.pill.syntax.label'),
  }));
}
