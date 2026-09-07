import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { Filters } from '@/modules/assets/admin/custom/use-custom-assets-filter';
import type { CustomAsset, CustomAssetRequestPayload } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { useCustomAssetFields } from '@/modules/assets/admin/custom/use-custom-asset-fields';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

interface UseCustomAssetsTableOptions {
  /** Whether this is the standalone page, which owns the url state. */
  mainPage: MaybeRefOrGetter<boolean>;
}

interface UseCustomAssetsTableReturn {
  /** The page of assets the table renders. */
  collection: Ref<Collection<CustomAsset>>;
  /** The declared filter fields the pill bar reads. */
  fields: ReturnType<typeof useCustomAssetFields>;
  /** True while a page is being fetched. */
  loading: Ref<boolean>;
  /** Rows the user expanded. */
  modelExpanded: Ref<CustomAsset[]>;
  /** The active filters; bound with `v-model:filters`. */
  modelFilter: WritableComputedRef<Filters>;
  /** Current page and size. */
  pagination: WritableComputedRef<TablePaginationData>;
  /** Refetches the current page. */
  refetch: () => Promise<void>;
  /** Refetches the page and the custom asset types together. */
  refresh: () => Promise<void>;
  /** Asks for confirmation, then deletes the asset and refreshes. */
  showDeleteConfirmation: (item: CustomAsset) => void;
  /** The table's sort state. */
  sort: WritableComputedRef<DataTableSortData<CustomAsset>>;
  /** The custom asset types, which the form offers as choices. */
  types: Readonly<Ref<string[]>>;
}

/**
 * Drives the custom assets table: the server-paginated page, the types the form offers, and row
 * deletion.
 *
 * @returns the table state, the ways to refresh it, and the delete action its rows offer
 */
export function useCustomAssetsTable(options: UseCustomAssetsTableOptions): UseCustomAssetsTableReturn {
  const { mainPage } = options;

  const { t } = useI18n({ useScope: 'global' });

  const types = ref<string[]>([]);

  const { deleteCustomAsset, getCustomAssetTypes, queryAllCustomAssets } = useAssetManagementApi();
  const { expanded } = useCommonTableProps<CustomAsset>();

  const fields = useCustomAssetFields(types);

  const {
    collection,
    filter,
    isLoading: loading,
    pagination,
    refetch,
    sort,
  } = useServerTable<
    CustomAsset,
    CustomAssetRequestPayload,
    Filters
  >({
    fetch: queryAllCustomAssets,
    fields,
    sort: {
      default: [{
        column: 'name',
        direction: 'desc',
      }],
    },
    urlState: routeWhen(toValue(mainPage)),
  });

  async function refreshTypes(): Promise<void> {
    set(types, await getCustomAssetTypes());
  }

  async function refresh(): Promise<void> {
    await Promise.all([refetch(), refreshTypes()]);
  }

  const { showDeleteConfirmation } = useTableRowDeletion<CustomAsset>({
    confirm: item => ({
      message: t('asset_management.confirm_delete.message', { asset: item.name }),
      title: t('asset_management.confirm_delete.title'),
    }),
    deleteItem: async item => deleteCustomAsset(item.identifier),
    errorMessage: (item, error) => t('asset_management.delete_error', {
      address: item.identifier,
      message: getErrorMessage(error),
    }),
    onDeleted: refresh,
  });

  return {
    collection,
    fields,
    loading,
    modelExpanded: expanded,
    modelFilter: filter,
    pagination,
    refetch,
    refresh,
    showDeleteConfirmation,
    sort,
    types: shallowReadonly(types),
  };
}
