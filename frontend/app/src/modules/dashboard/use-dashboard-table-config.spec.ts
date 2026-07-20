import type { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TableColumn } from '@/modules/core/table/table-column';
import { useDashboardTableConfig } from '@/modules/dashboard/use-dashboard-table-config';

const TABLE_TYPE = 'ASSETS' as DashboardTableType;

const mockCurrencySymbol = ref<string>('USD');
const mockVisibleColumns = ref<Record<string, TableColumn[]>>({ [TABLE_TYPE]: [] });

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'currencySymbol' ? mockCurrencySymbol : mockVisibleColumns)),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: vi.fn(),
}));

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

function create(netWorth: BigNumber = bigNumberify(100)): ReturnType<typeof useDashboardTableConfig> {
  return useDashboardTableConfig(TABLE_TYPE, 'My Table', netWorth);
}

describe('useDashboardTableConfig', () => {
  beforeEach(() => {
    set(mockCurrencySymbol, 'USD');
    set(mockVisibleColumns, { [TABLE_TYPE]: [] });
  });

  describe('pagination', () => {
    it('should default to page 1 with 10 items', () => {
      const { pagination } = create();

      expect(get(pagination)).toEqual({ itemsPerPage: 10, page: 1 });
    });

    it('should update the page via setPage', () => {
      const { pagination, setPage } = create();

      setPage(3);

      expect(get(pagination).page).toBe(3);
      expect(get(pagination).itemsPerPage).toBe(10);
    });

    it('should update page and limit from a table pagination event', () => {
      const { pagination, setTablePagination } = create();

      setTablePagination({ limit: 25, page: 2, total: 100 });

      expect(get(pagination)).toEqual({ itemsPerPage: 25, page: 2 });
    });

    it('should ignore an undefined pagination event', () => {
      const { pagination, setTablePagination } = create();

      setTablePagination(undefined);

      expect(get(pagination)).toEqual({ itemsPerPage: 10, page: 1 });
    });
  });

  describe('sort', () => {
    it('should default to sorting by value descending', () => {
      const { modelSort } = create();

      expect(get(modelSort)).toEqual({ column: 'value', direction: 'desc' });
    });
  });

  describe('tableHeaders', () => {
    it('should expose the base columns without the percentage columns', () => {
      const { tableHeaders } = create();
      const keys = get(tableHeaders).map(header => header.key);

      expect(keys).toEqual(['asset', 'protocol', 'price', 'amount', 'value']);
    });

    it('should add the net-value percentage column when enabled', () => {
      set(mockVisibleColumns, { [TABLE_TYPE]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE] });
      const { tableHeaders } = create();
      const keys = get(tableHeaders).map(header => header.key);

      expect(keys).toContain('percentageOfTotalNetValue');
    });

    it('should add the current-group percentage column when enabled', () => {
      set(mockVisibleColumns, { [TABLE_TYPE]: [TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP] });
      const { tableHeaders } = create();
      const keys = get(tableHeaders).map(header => header.key);

      expect(keys).toContain('percentageOfTotalCurrentGroup');
    });

    it('should label the net-value column differently when net worth is positive', () => {
      set(mockVisibleColumns, { [TABLE_TYPE]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE] });
      const { tableHeaders } = create(bigNumberify(500));
      const header = get(tableHeaders).find(h => h.key === 'percentageOfTotalNetValue');

      expect(header?.label).toBe('dashboard_asset_table.headers.percentage_of_total_net_value');
    });

    it('should label the net-value column as total when net worth is zero', () => {
      set(mockVisibleColumns, { [TABLE_TYPE]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE] });
      const { tableHeaders } = create(bigNumberify(0));
      const header = get(tableHeaders).find(h => h.key === 'percentageOfTotalNetValue');

      expect(header?.label).toBe('dashboard_asset_table.headers.percentage_total');
    });

    it('should reflect the currency symbol in the price column label', () => {
      set(mockCurrencySymbol, 'EUR');
      const { tableHeaders } = create();
      const priceHeader = get(tableHeaders).find(h => h.key === 'price');

      expect(priceHeader?.label).toBe('common.price_in_symbol');
    });
  });
});
