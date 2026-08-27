import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import type { useServerTable } from '@/modules/core/table/use-server-table';
import { bigNumberify } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent, h, ref } from 'vue';
import { TableColumn } from '@/modules/core/table/table-column';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useNftData } from './use-nft-data';

type ServerTableOptions = Parameters<typeof useServerTable>[0];

const {
  collection,
  currencySymbol,
  dashboardTablesVisibleColumns,
  fetchNonFungibleBalances,
  refreshNonFungibleBalances,
  sectionActive,
  setPage,
  totalNetWorth,
  useIsActive,
  useRememberTableSorting,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const { bigNumberify } = await import('@rotki/common');
  return {
    collection: ref<Collection<NonFungibleBalance>>({ data: [], found: 0, limit: -1, total: 0 }),
    currencySymbol: ref<string>('USD'),
    dashboardTablesVisibleColumns: ref<Record<string, string[]>>({}),
    fetchNonFungibleBalances: vi.fn(),
    refreshNonFungibleBalances: vi.fn(),
    sectionActive: ref<boolean>(false),
    setPage: vi.fn(),
    totalNetWorth: ref(bigNumberify(0)),
    useIsActive: vi.fn(),
    useRememberTableSorting: vi.fn(),
  };
});

let serverTableOptions: ServerTableOptions | undefined;

function emptyCollection(): Collection<NonFungibleBalance> {
  return { data: [], found: 0, limit: -1, total: 0 };
}

vi.mock('@/modules/balances/nft/use-nft-balances', () => ({
  useNftBalances: (): Record<string, unknown> => ({ fetchNonFungibleBalances, refreshNonFungibleBalances }),
}));

vi.mock('@/modules/core/table/use-server-table', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-server-table')>(),
  useServerTable: (options: ServerTableOptions): Record<string, unknown> => {
    serverTableOptions = options;
    return {
      collection,
      isLoading: ref(false),
      pagination: computed(() => ({ limit: 10, page: 1, total: 0 })),
      refetch: vi.fn(),
      setPage,
      sort: computed(() => []),
    };
  },
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting,
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (key: string): unknown => key === 'currencySymbol' ? currencySymbol : dashboardTablesVisibleColumns,
}));

vi.mock('@/modules/statistics/use-statistics-store', () => ({
  useStatisticsStore: (): Record<string, unknown> => ({ totalNetWorth }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive }),
}));

const wrappers: VueWrapper[] = [];

function mountNftData(dashboard = false): ReturnType<typeof useNftData> {
  let captured: ReturnType<typeof useNftData> | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useNftData({ dashboard });
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  if (setupError)
    throw setupError;
  return captured!;
}

function columnKeys(dashboard = false): string[] {
  return get(mountNftData(dashboard).cols).map(col => col.key);
}

describe('modules/balances/non-fungible/useNftData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useIsActive.mockReturnValue(sectionActive);
    set(collection, emptyCollection());
    set(currencySymbol, 'USD');
    set(dashboardTablesVisibleColumns, { [DashboardTableType.NFT]: [] });
    set(totalNetWorth, bigNumberify(0));
    set(sectionActive, false);
    serverTableOptions = undefined;
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('the share of net worth', () => {
    it('should report a holding as a percentage of the whole portfolio', () => {
      set(totalNetWorth, bigNumberify(2000));

      expect(mountNftData().percentageOfTotalNetValue(bigNumberify(500))).toBe('25.00');
    });

    it('should report zero rather than dividing by an empty portfolio', () => {
      expect(mountNftData().percentageOfTotalNetValue(bigNumberify(500))).toBe('0.00');
    });

    it('should always carry two decimals', () => {
      set(totalNetWorth, bigNumberify(3));

      expect(mountNftData().percentageOfTotalNetValue(bigNumberify(1))).toBe('33.33');
    });
  });

  describe('the share of the nft group', () => {
    it('should divide by the value of the whole filtered group, not the page', () => {
      set(collection, { ...emptyCollection(), totalValue: bigNumberify(400) });

      expect(mountNftData().percentageOfCurrentGroup(bigNumberify(100))).toBe('25.00');
    });

    it('should report zero when the group has no value yet', () => {
      set(collection, { ...emptyCollection(), totalValue: undefined });

      expect(mountNftData().percentageOfCurrentGroup(bigNumberify(100))).toBe('0.00');
    });

    it('should treat an unknown group value as zero rather than throwing', () => {
      set(collection, { ...emptyCollection(), totalValue: null });

      expect(mountNftData().percentageOfCurrentGroup(bigNumberify(100))).toBe('0.00');
    });
  });

  describe('the columns of the full page', () => {
    it('should offer the ignore, custom price and action columns a dashboard has no room for', () => {
      expect(columnKeys()).toEqual(['name', 'ignored', 'priceInAsset', 'price', 'manuallyInput', 'actions']);
    });

    it('should name the user currency in the price column', () => {
      set(currencySymbol, 'EUR');

      const price = get(mountNftData().cols).find(col => col.key === 'price');

      expect(price?.label).toBe('common.price_in_symbol::EUR');
    });
  });

  describe('the columns of the dashboard widget', () => {
    it('should show only the three core columns when no percentage is enabled', () => {
      expect(columnKeys(true)).toEqual(['name', 'priceInAsset', 'price']);
    });

    it('should add the net-worth percentage when that column is enabled', () => {
      set(dashboardTablesVisibleColumns, {
        [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      });

      expect(columnKeys(true)).toEqual(['name', 'priceInAsset', 'price', 'percentageOfTotalNetValue']);
    });

    it('should add the group percentage when that column is enabled', () => {
      set(dashboardTablesVisibleColumns, {
        [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP],
      });

      expect(columnKeys(true)).toEqual(['name', 'priceInAsset', 'price', 'percentageOfTotalCurrentGroup']);
    });

    it('should keep net worth ahead of group when both are enabled', () => {
      set(dashboardTablesVisibleColumns, {
        [DashboardTableType.NFT]: [
          TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
        ],
      });

      expect(columnKeys(true)).toEqual([
        'name',
        'priceInAsset',
        'price',
        'percentageOfTotalNetValue',
        'percentageOfTotalCurrentGroup',
      ]);
    });
  });

  describe('the reset to the first page', () => {
    it('should go back to page one when the ignored-assets filter changes', async () => {
      const { modelIgnoredAssetsHandling } = mountNftData();

      set(modelIgnoredAssetsHandling, 'show_all');
      await flushPromises();

      expect(setPage).toHaveBeenCalledWith(1);
    });

    it('should leave the dashboard widget where it is, since it does not own the page', async () => {
      const { modelIgnoredAssetsHandling } = mountNftData(true);

      set(modelIgnoredAssetsHandling, 'show_all');
      await flushPromises();

      expect(setPage).not.toHaveBeenCalled();
    });
  });

  describe('the table it configures', () => {
    it('should sync the full page to the url and keep the widget out of it', () => {
      mountNftData();
      expect(serverTableOptions?.urlState).toEqual({ mode: 'route' });

      mountNftData(true);
      expect(serverTableOptions?.urlState).toEqual({ mode: 'none' });
    });

    it('should sort by price, highest first, before the user picks anything', () => {
      mountNftData();

      expect(serverTableOptions?.sort).toEqual({ default: [{ column: 'price', direction: 'desc' }] });
    });

    it('should hand the table the nft fetcher rather than fetching itself', () => {
      mountNftData();

      expect(serverTableOptions?.fetch).toBe(fetchNonFungibleBalances);
      expect(fetchNonFungibleBalances).not.toHaveBeenCalled();
    });
  });

  describe('what it passes straight through', () => {
    it('should report the section busy while the nft balance activity runs', () => {
      const { sectionLoading } = mountNftData();

      expect(useIsActive).toHaveBeenCalledWith(ActivityKind.NFT_BALANCES);
      set(sectionActive, true);
      expect(get(sectionLoading)).toBe(true);
    });

    it('should expose the refresh without wrapping it', () => {
      expect(mountNftData().refreshNonFungibleBalances).toBe(refreshNonFungibleBalances);
    });

    it('should remember the sorting under the non-fungible table id', () => {
      mountNftData();

      expect(useRememberTableSorting).toHaveBeenCalledWith(
        TableId.NON_FUNGIBLE_BALANCES,
        expect.anything(),
        expect.anything(),
      );
    });
  });
});
