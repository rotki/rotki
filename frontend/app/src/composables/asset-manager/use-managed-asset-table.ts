import type { SupportedAsset } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { Collection } from '@/types/collection';
import { some } from 'es-toolkit/compat';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

interface UseManagedAssetTableReturn {
  cols: ComputedRef<DataTableColumn<SupportedAsset>[]>;
  data: ComputedRef<SupportedAsset[]>;
  expand: (item: SupportedAsset) => void;
  isExpanded: (identifier: string) => boolean;
}

export function useManagedAssetTable(
  sortModel: Ref<DataTableSortData<SupportedAsset>>,
  paginationModel: Ref<TablePaginationData>,
  expanded: Ref<SupportedAsset[]>,
  collection: Ref<Collection<SupportedAsset>>,
): UseManagedAssetTableReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

  const cols = computed<DataTableColumn<SupportedAsset>[]>(() => [{
    cellClass: 'py-0',
    class: 'w-full',
    key: 'symbol',
    label: t('common.asset'),
    sortable: true,
  }, {
    cellClass: '!text-nowrap py-0',
    key: 'type',
    label: t('common.type'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    class: 'min-w-[11.375rem]',
    key: 'address',
    label: t('common.address'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    class: 'min-w-[10rem]',
    key: 'started',
    label: t('asset_table.headers.started'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    key: 'ignored',
    label: t('assets.action.ignore'),
  }, {
    key: 'actions',
    label: '',
  }]);

  // Collection handler logic integration
  const data = computed<SupportedAsset[]>(() => get(collection, 'data'));
  const found = computed<number>(() => get(collection, 'found'));

  useRememberTableSorting<SupportedAsset>(TableId.SUPPORTED_ASSET, sortModel, cols);

  const setPage = (page: number): void => {
    set(paginationModel, {
      ...get(paginationModel),
      page,
    });
  };

  const isExpanded = (identifier: string): boolean => some(get(expanded), { identifier });

  const expand = (item: SupportedAsset): void => {
    set(expanded, isExpanded(item.identifier) ? [] : [item]);
  };

  watch([data, found, itemsPerPage], ([data, found, itemsPerPage]) => {
    if (data.length === 0 && found > 0) {
      const lastPage = Math.ceil(found / itemsPerPage);
      setPage(lastPage);
    }
  });

  return {
    cols,
    data,
    expand,
    isExpanded,
  };
}
