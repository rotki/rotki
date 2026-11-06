import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import { type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';

interface ExchangeIdentity {
  location: string;
  name: string;
}

interface UseExchangeConnectionsTableReturn {
  cols: ComputedRef<DataTableColumn<Exchange>[]>;
  modelSort: Ref<DataTableSortColumn<Exchange>>;
  highlight: (exchange: ExchangeIdentity) => void;
  rowClass: (row: ExchangeIdentity) => string;
  balanceOf: (exchange: Pick<Exchange, 'identifier' | 'location'>) => BigNumber;
}

export function useExchangeConnectionsTable(): UseExchangeConnectionsTableReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { exchangeAccountBalances } = storeToRefs(useBalancesStore());
  const { isAssetIgnored } = useAssetsStore();

  const modelSort = ref<DataTableSortColumn<Exchange>>({
    column: 'name',
    direction: 'asc',
  });

  const cols = computed<DataTableColumn<Exchange>[]>(() => [{
    cellClass: 'py-0 w-48',
    key: 'location',
    label: t('common.exchange'),
    sortable: true,
  }, {
    key: 'name',
    label: t('common.name'),
    sortable: true,
  }, {
    cellClass: 'py-0 w-36',
    key: 'syncEnabled',
    label: t('exchange_settings.header.sync_enabled'),
  }, {
    align: 'end',
    key: 'balance',
    label: t('common.value'),
  }, {
    align: 'end',
    cellClass: 'py-0 w-28',
    key: 'actions',
    label: t('common.actions_text'),
  }]);

  useRememberTableSorting<Exchange>(TableId.EXCHANGE, modelSort, cols);

  const { highlight, rowClass } = useRowHighlight<ExchangeIdentity>(
    ({ location, name }) => `${location}#${name}`,
  );

  const totals = computed<Record<string, Record<string, BigNumber>>>(() => Object.fromEntries(
    Object.entries(get(exchangeAccountBalances)).map(([location, accounts]) => [
      location,
      Object.fromEntries(Object.entries(accounts).map(([identifier, balances]) => [
        identifier,
        exchangeAssetSum(balances, isAssetIgnored),
      ])),
    ]),
  ));

  const balanceOf = (exchange: Pick<Exchange, 'identifier' | 'location'>): BigNumber =>
    get(totals)[exchange.location]?.[exchange.identifier] ?? Zero;

  return {
    balanceOf,
    cols,
    highlight,
    modelSort,
    rowClass,
  };
}
