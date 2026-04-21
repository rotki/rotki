import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import { objectOmit } from '@vueuse/shared';
import { arrayify } from '@/modules/core/common/data/array';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

export enum TableId {
  ACCOUNT_ASSET_BALANCES = 'ACCOUNT_ASSET_BALANCES',
  ACCOUNT_BALANCES = 'ACCOUNT_BALANCES',
  ADDRESS_BOOK = 'ADDRESS_BOOK',
  AIRDROP = 'AIRDROP',
  ASSET_BALANCES = 'ASSET_BALANCES',
  ASSET_LOCATION = 'ASSET_LOCATION',
  ASSET_MISSING_MAPPINGS = 'ASSET_MISSING_MAPPINGS',
  BINANCE_RECEIVED_SAVING = 'BINANCE_RECEIVED_SAVING',
  BINANCE_RECEIVED_SAVING_EVENTS = 'BINANCE_RECEIVED_SAVING_EVENTS',
  COST_BASIS = 'COST_BASIS',
  CUSTOM_ASSET = 'CUSTOM_ASSET',
  DASHBOARD_ASSET = 'DASHBOARD_ASSET',
  EDIT_BALANCE_SNAPSHOT = 'EDIT_BALANCE_SNAPSHOT',
  EDIT_LOCATION_DATA_SNAPSHOT = 'EDIT_LOCATION_DATA_SNAPSHOT',
  ETH_STAKING_VALIDATORS = 'ETH_STAKING_VALIDATORS',
  EVM_NATIVE_TOKEN_BREAKDOWN = 'EVM_NATIVE_TOKEN_BREAKDOWN',
  EXCHANGE = 'EXCHANGE',
  HISTORIC_PRICES = 'HISTORIC_PRICES',
  HISTORY = 'HISTORY',
  LATEST_PRICES = 'LATEST_PRICES',
  MANUAL_BALANCES = 'MANUAL_BALANCES',
  MODULES = 'MODULES',
  NEWLY_DETECTED_ASSETS = 'NEWLY_DETECTED_ASSETS',
  NON_FUNGIBLE_BALANCES = 'NON_FUNGIBLE_BALANCES',
  POOL_LIQUIDITY_BALANCE = 'POOL_LIQUIDITY_BALANCE',
  POOL_LIQUIDITY_BALANCE_DETAIL = 'POOL_LIQUIDITY_BALANCE_DETAIL',
  REPORTS = 'REPORTS',
  REPORTS_MISSING_PRICES = 'REPORTS_MISSING_PRICES',
  REPORT_EVENTS = 'REPORT_EVENTS',
  REPORT_MISSING_ACQUISITIONS = 'REPORT_MISSING_ACQUISITIONS',
  REPORT_MISSING_ACQUISITIONS_DETAIL = 'REPORT_MISSING_ACQUISITIONS_DETAIL',
  SUPPORTED_ASSET = 'SUPPORTED_ASSET',
  TAG_MANAGER = 'TAG_MANAGER',
  USER_DB_BACKUP = 'USER_DB_BACKUP',
}

type TableSorting<T> = Partial<Record<TableId, DataTableSortData<T>>>;

function defaultTableSorting<T>(): TableSorting<T> {
  return {};
}

export function useRememberTableSorting<T>(
  id: TableId,
  sort: WritableComputedRef<DataTableSortData<T>> | Ref<DataTableSortData<T>>,
  headers: ComputedRef<DataTableColumn<T>[]> | Ref<DataTableColumn<T>[]>,
): void {
  const { persistTableSorting } = storeToRefs(useFrontendSettingsStore());

  const rawData = useLocalStorage(`rotki.table_sorting`, defaultTableSorting<T>());

  onBeforeMount(() => {
    if (get(persistTableSorting)) {
      const sortableColumns = get(headers).filter(item => item.sortable).map(item => item.key);

      const dataVal = get<TableSorting<T>>(rawData)[id];
      if (dataVal) {
        const isArray = Array.isArray(dataVal);
        const dataInArray = arrayify(dataVal);
        const sortableOnly = dataInArray.filter(item => item.column && sortableColumns.includes(item.column));

        if (sortableOnly.length > 0) {
          set(sort, isArray ? sortableOnly : sortableOnly[0]);
        }
      }
    }

    // The watcher is intentionally placed inside onBeforeMount to prevent it from triggering
    // when the component first loads. If placed outside, it would immediately react to the
    // initial sort value and save it to storage, overriding any previously saved sorting preference.
    watch(sort, (sort) => {
      if (get(persistTableSorting)) {
        set(rawData, { ...get<TableSorting<T>>(rawData), [id]: sort });
      }
      else {
        set(rawData, objectOmit(get<TableSorting<T>>(rawData), [id]));
      }
    });
  });
}
