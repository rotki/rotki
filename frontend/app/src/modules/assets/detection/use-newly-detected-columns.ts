import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { NewlyDetectedTokenRow } from './use-newly-detected-token-rows';
import { computed, type ComputedRef, type WritableComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';

/**
 * The newly detected tokens table's columns, with the table's sorting remembered across visits.
 *
 * @param sort - the table's sort model, which the remembered sorting is restored into
 */
export function useNewlyDetectedColumns(
  sort: WritableComputedRef<DataTableSortData<NewlyDetectedTokenRow>>,
): ComputedRef<DataTableColumn<NewlyDetectedTokenRow>[]> {
  const { t } = useI18n({ useScope: 'global' });

  const cols = computed<DataTableColumn<NewlyDetectedTokenRow>[]>(() => [
    {
      // `max-w-0`: the asset takes the room left and truncates, keeping the actions on screen
      cellClass: 'py-0 max-w-0',
      class: 'py-0 w-full',
      key: 'tokenIdentifier',
      label: t('common.asset'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      class: 'py-0',
      key: 'address',
      label: t('common.address'),
      sortable: false,
    },
    {
      cellClass: 'py-0',
      class: 'py-0',
      key: 'price',
      label: t('common.price'),
      sortable: false,
    },
    {
      cellClass: 'py-0',
      class: 'py-0',
      key: 'spam',
      label: t('spam_estimate.label'),
      sortable: false,
    },
    {
      cellClass: 'py-0',
      class: 'py-0',
      key: 'detectedAt',
      label: t('asset_table.newly_detected.detected_at'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      class: 'py-0',
      key: 'description',
      label: t('asset_table.newly_detected.seen_during'),
    },
    {
      align: 'end',
      cellClass: 'py-0 w-px',
      class: 'py-0',
      key: 'actions',
      label: t('common.actions_text'),
    },
  ]);

  useRememberTableSorting<NewlyDetectedTokenRow>(TableId.NEWLY_DETECTED_ASSETS, sort, cols);

  return cols;
}
