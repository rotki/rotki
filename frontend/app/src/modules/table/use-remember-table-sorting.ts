import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { arrayify } from '@/utils/array';
import { useRefPropVModel } from '@/utils/model';

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
  ORACLE_CACHE_MANAGEMENT = 'ORACLE_CACHE_MANAGEMENT',
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

export function useRememberTableSorting<T>(
  id: TableId,
  sort: WritableComputedRef<DataTableSortData<T>> | Ref<DataTableSortData<T>>,
  headers: ComputedRef<DataTableColumn<T>[]> | Ref<DataTableColumn<T>[]>,
): void {
  const { persistTableSorting } = storeToRefs(useFrontendSettingsStore());

  const rawData = useLocalStorage<Record<string, DataTableSortData<T>>>(`rotki.table_sorting`, {});

  const data = useRefPropVModel(rawData, id);

  onBeforeMount(() => {
    if (get(persistTableSorting)) {
      const sortableColumns = get(headers).filter(item => item.sortable).map(item => item.key);

      const dataVal = get(data);
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
        set(data, sort);
      }
      else {
        set(data, undefined);
      }
    });
  });
}
