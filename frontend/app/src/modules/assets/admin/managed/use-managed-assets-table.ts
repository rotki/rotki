import type { SupportedAsset } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { PillParams } from '@/modules/core/table/param-refs';
import { get, set } from '@vueuse/shared';
import { keyBy } from 'es-toolkit';
import { storeToRefs } from 'pinia';
import { computed, type MaybeRefOrGetter, type Ref, ref, shallowRef, type WritableComputedRef } from 'vue';
import { type Filters, managedAssetStatusParams } from '@/modules/assets/admin/managed/asset-filter-keys';
import { useManagedAssetDeletion, type UseManagedAssetDeletionReturn } from '@/modules/assets/admin/managed/use-managed-asset-deletion';
import { useManagedAssetFields } from '@/modules/assets/admin/managed/use-managed-asset-fields';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { type AssetRequestPayload, IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { fromRequest } from '@/modules/core/api/request-result';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';

interface UseManagedAssetsTableReturn extends UseManagedAssetDeletionReturn {
  /** The page of assets the table renders. */
  assets: Ref<Collection<SupportedAsset>>;
  /** Rows the user expanded. */
  modelExpanded: Ref<SupportedAsset[]>;
  /** The declared filter fields the pill bar reads. */
  fields: ReturnType<typeof useManagedAssetFields>;
  /** The active filters; bound with `v-model:filters`. */
  modelFilter: Ref<Filters>;
  /** How ignored assets are being treated, which the table shows per row. */
  modelIgnoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
  /** True while a page is being fetched. */
  loading: Ref<boolean>;
  /** The pill bar's state. */
  modelPillParams: WritableComputedRef<PillParams>;
  /** Current page and size. */
  pagination: WritableComputedRef<TablePaginationData>;
  /** Refetches the current page. */
  refetch: () => Promise<void>;
  /**
   * The selection, as identifiers.
   *
   * @remarks
   * The table speaks identifiers while the selection holds whole assets, so writing it maps back
   * through the current page. An identifier absent from that page resolves to nothing.
   */
  modelSelectedRows: WritableComputedRef<string[]>;
  /** Jumps to a page. */
  setPage: (page: number) => void;
  /** The active sort. */
  sort: Ref<DataTableSortData<SupportedAsset>>;
}

/**
 * Drives the managed-asset table: the server-side page, the status filters, the selection, and
 * deleting a row.
 *
 * @remarks
 * Deleting an asset is irreversible and is the only destructive path here, so the row asks first
 * and a failure is named above the table rather than silently leaving the row in place.
 *
 * @param mainPage - whether this owns the route, and so may sync its state to the URL
 * @param assetTypes - the types the filter offers, loaded by {@link useManagedAssetForm}
 * @returns the table's bindings; only {@link UseManagedAssetsTableReturn.deleteAsset}
 * deletes anything
 */
export function useManagedAssetsTable(
  mainPage: MaybeRefOrGetter<boolean>,
  assetTypes: MaybeRefOrGetter<string[]>,
): UseManagedAssetsTableReturn {
  const modelIgnoredAssetsHandling = ref<IgnoredAssetsHandlingType>(IgnoredAssetHandlingType.EXCLUDE);
  const onlyShowOwned = shallowRef<boolean>(false);
  const onlyShowWhitelisted = shallowRef<boolean>(false);

  const { queryAllAssets } = useAssetManagementApi();
  const { ignoredAssets } = storeToRefs(useAssetsStore());

  const { pillParams, source: statusSource } = managedAssetStatusParams({
    ignoredAssetsHandling: modelIgnoredAssetsHandling,
    onlyShowOwned,
    onlyShowWhitelisted,
  });

  const { expanded, selected } = useCommonTableProps<SupportedAsset>();
  const fields = useManagedAssetFields(assetTypes, () => get(ignoredAssets).length);

  const {
    collection: assets,
    filter,
    isLoading: loading,
    pagination,
    refetch,
    setPage,
    sort,
  } = useServerTable<SupportedAsset, AssetRequestPayload, Filters>({
    fetch: async payload => fromRequest(async () => queryAllAssets(payload)),
    fields,
    params: [statusSource],
    sort: {
      default: {
        column: 'symbol',
        direction: 'asc',
      },
    },
    urlState: routeWhen(mainPage),
  });

  const { deleteAsset, deleteConfirm, deleteFailure } = useManagedAssetDeletion(refetch);

  const assetsMap = computed(() => keyBy(get(assets).data, item => item.identifier));

  const modelSelectedRows = computed<string[]>({
    get() {
      return get(selected).map(({ identifier }) => identifier);
    },
    set(identifiers: string[]) {
      set(selected, identifiers.map(identifier => get(assetsMap)[identifier]));
    },
  });

  return {
    assets,
    fields,
    loading,
    modelExpanded: expanded,
    modelFilter: filter,
    modelIgnoredAssetsHandling,
    modelPillParams: pillParams,
    modelSelectedRows,
    pagination,
    refetch,
    setPage,
    deleteAsset,
    deleteConfirm,
    deleteFailure,
    sort,
  };
}
