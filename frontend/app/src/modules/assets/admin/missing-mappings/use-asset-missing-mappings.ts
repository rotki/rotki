import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { Filters } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-filter';
import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { MissingMapping } from '@/modules/user-data/schemas';
import {
  type MissingMappingsRequestPayload,
  useMissingMappingsDB,
} from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { useMissingMappingsFields } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-fields';
import { useServerTable } from '@/modules/core/table/use-server-table';

interface UseAssetMissingMappingsReturn {
  /** The table's columns. */
  cols: ComputedRef<DataTableColumn<MissingMapping>[]>;
  /** The declared filter fields the pill bar reads. */
  fields: ReturnType<typeof useMissingMappingsFields>;
  /** The active filters; bound with `v-model:filters`. */
  modelFilter: Ref<Filters>;
  /**
   * The mapping the dialog is adding, seeded from the row the user picked.
   *
   * @remarks
   * The asset is left empty on purpose: choosing it is the whole point of the dialog.
   */
  modelMapping: Ref<CexMapping | undefined>;
  /** The page of missing mappings the table renders. */
  mappings: Ref<Collection<MissingMapping>>;
  /** Opens the dialog on a mapping seeded from this row. */
  onAddClick: (item: MissingMapping) => void;
  /**
   * Drops the row a mapping has just been added for, then re-reads the page.
   *
   * @remarks
   * A mapping saved for all exchanges carries no location, which the local record stores as an
   * empty string.
   */
  onAddComplete: (item: CexMapping) => Promise<void>;
  /** Current page and size. */
  pagination: WritableComputedRef<TablePaginationData>;
  /** Refetches the current page. */
  refetch: () => Promise<void>;
  /** The table's sort state. */
  sort: WritableComputedRef<DataTableSortData<MissingMapping>>;
}

/**
 * Drives the missing asset mappings page: the table of exchange symbols rotki could not resolve,
 * and adding a mapping for one.
 *
 * @returns the table state and the two ends of the add flow
 */
export function useAssetMissingMappings(): UseAssetMissingMappingsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const modelMapping = ref<CexMapping>();

  const { getData, remove } = useMissingMappingsDB();
  const fields = useMissingMappingsFields();

  const cols = computed<DataTableColumn<MissingMapping>[]>(() => [{
    align: 'center',
    cellClass: 'py-3',
    key: 'location',
    label: t('common.location'),
    sortable: true,
  }, {
    cellClass: 'py-3',
    key: 'identifier',
    label: t('common.asset'),
    sortable: true,
  }, {
    cellClass: 'py-3 border-x border-default',
    class: 'border-x border-default',
    key: 'details',
    label: t('common.details'),
  }, {
    align: 'center',
    cellClass: 'py-3 w-24',
    key: 'actions',
    label: t('common.actions_text'),
  }]);

  const {
    collection: mappings,
    filter,
    pagination,
    refetch,
    sort,
  } = useServerTable<MissingMapping, MissingMappingsRequestPayload, Filters>({
    fetch: getData,
    fields,
    sort: {
      default: {
        column: 'location',
        direction: 'asc',
      },
    },
  });

  function onAddClick(item: MissingMapping): void {
    set(modelMapping, {
      asset: '',
      location: item.location,
      locationSymbol: item.identifier,
    });
  }

  async function onAddComplete(item: CexMapping): Promise<void> {
    await remove({
      identifier: item.locationSymbol,
      location: item.location ?? '',
    });
    await refetch();
  }

  return {
    cols,
    fields,
    mappings,
    modelFilter: filter,
    modelMapping,
    onAddClick,
    onAddComplete,
    pagination,
    refetch,
    sort,
  };
}
