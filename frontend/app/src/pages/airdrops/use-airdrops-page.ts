import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { airdropParams, useAirdropFields } from '@/modules/airdrops/use-airdrop-fields';
import { useAirdrops } from '@/modules/airdrops/use-airdrops';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { type AirdropWithIndex, toAirdropRows } from '@/pages/airdrops/airdrop-rows';

interface UseAirdropsPageReturn {
  cols: ComputedRef<DataTableColumn<AirdropWithIndex>[]>;
  expand: (item: AirdropWithIndex) => void;
  fetchAirdrops: () => Promise<void>;
  fields: FieldDef[];
  loading: Readonly<Ref<boolean>>;
  modelExpanded: Ref<AirdropWithIndex[]>;
  modelHideUnknownAlert: Ref<boolean>;
  modelPagination: Ref<TablePaginationData | undefined>;
  modelPillParams: WritableComputedRef<PillParams>;
  modelSort: Ref<DataTableSortData<AirdropWithIndex>>;
  pillLabels: ReturnType<typeof usePillBarLabels>;
  refreshTooltip: ComputedRef<string>;
  rows: ComputedRef<AirdropWithIndex[]>;
  status: Readonly<Ref<string>>;
}

export function useAirdropsPage(): UseAirdropsPageReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { airdrops, fetchAirdrops, loading } = useAirdrops();

  const modelHideUnknownAlert = useLocalStorage('rotki.airdrops.hide_unknown_alert', false);
  const modelSort = ref<DataTableSortData<AirdropWithIndex>>([]);
  const modelExpanded = ref<AirdropWithIndex[]>([]);
  const modelPagination = ref<TablePaginationData>();
  const status = shallowRef<string>('');
  const selectedAddresses = ref<string[]>([]);

  const refreshTooltip = computed<string>(() => t('helpers.refresh_header.tooltip', {
    title: t('airdrops.title').toLocaleLowerCase(),
  }));

  const airdropAddresses = computed<string[]>(() => Object.keys(get(airdrops)));

  const fields = useAirdropFields(airdropAddresses);
  const pillLabels = usePillBarLabels();
  const modelPillParams = airdropParams(selectedAddresses, status);

  const rows = computed<AirdropWithIndex[]>(() =>
    toAirdropRows(get(airdrops), get(selectedAddresses), get(status), Date.now() / 1000),
  );

  const cols = computed<DataTableColumn<AirdropWithIndex>[]>(() => [
    {
      key: 'source',
      label: t('airdrops.headers.source'),
      sortable: true,
      width: '200px',
    },
    {
      key: 'address',
      label: t('common.address'),
      sortable: true,
    },
    {
      align: 'end',
      key: 'amount',
      label: t('common.amount'),
      sortable: true,
    },
    {
      key: 'claimed',
      label: t('common.status'),
    },
  ]);

  useRememberTableSorting<AirdropWithIndex>(TableId.AIRDROP, modelSort, cols);

  /** Single-expand: expanding another row replaces the open one, and a repeat click closes it. */
  function expand(item: AirdropWithIndex): void {
    set(modelExpanded, get(modelExpanded).includes(item) ? [] : [item]);
  }

  onMounted(async () => {
    await fetchAirdrops();
  });

  /**
   * Returns to the first page whenever the filter narrows, since the current page can otherwise sit
   * past the end of the shorter result and read as an empty table.
   */
  function resetPageForNarrowedFilter(): void {
    set(modelPagination, { ...get(modelPagination), page: 1 });
  }

  watch([status, selectedAddresses], resetPageForNarrowedFilter);

  return {
    cols,
    expand,
    fetchAirdrops,
    fields,
    loading,
    modelExpanded,
    modelHideUnknownAlert,
    modelPagination,
    modelPillParams,
    modelSort,
    pillLabels,
    refreshTooltip,
    rows,
    status: readonly(status),
  };
}
