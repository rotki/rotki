import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockCreateOracleCache = vi.fn();
const mockNotify = vi.fn();
const mockGetPriceCache = vi.fn();
const mockDeletePriceCache = vi.fn();
const mockShowConfirm = vi.fn();

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    createOracleCache: (...args: unknown[]) => mockCreateOracleCache(...args),
  }),
}));

vi.mock('@/modules/balances/api/use-price-api', () => ({
  usePriceApi: vi.fn().mockReturnValue({
    deletePriceCache: (...args: unknown[]) => mockDeletePriceCache(...args),
    getPriceCache: (...args: unknown[]) => mockGetPriceCache(...args),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    useIsTaskRunning: vi.fn().mockReturnValue(ref<boolean>(false)),
  }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: (...args: unknown[]) => mockNotify(...args),
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn().mockReturnValue({
    show: (...args: unknown[]) => mockShowConfirm(...args),
  }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    getAssetField: vi.fn().mockImplementation((asset: string) => asset),
  }),
}));

const OracleCacheContent = (await import('@/modules/assets/prices/components/oracle/OracleCacheContent.vue')).default;

interface CacheContentVm {
  loadCaches: () => Promise<void>;
  newFromAsset: string;
  newToAsset: string;
  filterFromAsset: string;
  filterToAsset: string;
  rows: { fromAsset: string; toAsset: string; id: number }[];
  populateCache: () => Promise<void>;
  clearCache: (entry: OracleCacheMeta) => Promise<void>;
  clearFilter: () => void;
}

describe('oracleCacheContent', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockCreateOracleCache.mockClear().mockResolvedValue({ success: true });
    mockNotify.mockClear();
    mockGetPriceCache.mockClear().mockResolvedValue([]);
    mockDeletePriceCache.mockClear().mockResolvedValue(true);
    mockShowConfirm.mockClear();
  });

  function createWrapper(): ReturnType<typeof mount> {
    return mount(OracleCacheContent, { shallow: true });
  }

  it('should load caches on mount', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(mockGetPriceCache).toHaveBeenCalledOnce();
    expect(mockGetPriceCache).toHaveBeenCalledWith('cryptocompare');
    expect(wrapper.exists()).toBe(true);
  });

  it('should call createOracleCache with the new asset pair', async () => {
    mockGetPriceCache.mockResolvedValue([]);
    const wrapper = createWrapper();
    await flushPromises();

    const vm = wrapper.vm as unknown as CacheContentVm;
    vm.newFromAsset = 'ETH';
    vm.newToAsset = 'USD';
    await vm.populateCache();

    expect(mockCreateOracleCache).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      purgeOld: false,
      source: 'cryptocompare',
      toAsset: 'USD',
    });
  });

  it('should notify on populate error and not reload caches', async () => {
    mockCreateOracleCache.mockResolvedValueOnce({ message: 'Rate limited', success: false });
    const wrapper = createWrapper();
    await flushPromises();
    mockGetPriceCache.mockClear();

    const vm = wrapper.vm as unknown as CacheContentVm;
    vm.newFromAsset = 'ETH';
    vm.newToAsset = 'USD';
    await vm.populateCache();

    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'error' }),
    );
    expect(mockGetPriceCache).not.toHaveBeenCalled();
  });

  it('should delete a cache entry and reload', async () => {
    const entries: OracleCacheMeta[] = [{
      fromAsset: 'ETH',
      fromTimestamp: '1700000000',
      toAsset: 'USD',
      toTimestamp: '1700100000',
    }];
    mockGetPriceCache.mockResolvedValueOnce(entries).mockResolvedValueOnce([]);

    const wrapper = createWrapper();
    await flushPromises();

    const vm = wrapper.vm as unknown as CacheContentVm;
    await vm.clearCache(entries[0]);

    expect(mockDeletePriceCache).toHaveBeenCalledWith('cryptocompare', 'ETH', 'USD');
    expect(mockGetPriceCache).toHaveBeenCalledTimes(2);
  });

  it('should notify on delete error', async () => {
    mockDeletePriceCache.mockRejectedValueOnce(new Error('boom'));
    const wrapper = createWrapper();
    await flushPromises();

    const vm = wrapper.vm as unknown as CacheContentVm;
    await vm.clearCache({
      fromAsset: 'ETH',
      fromTimestamp: '1700000000',
      toAsset: 'USD',
      toTimestamp: '1700100000',
    });

    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'error' }),
    );
  });

  it('should filter rows by from/to asset', async () => {
    const entries: OracleCacheMeta[] = [
      { fromAsset: 'ETH', fromTimestamp: '1', toAsset: 'USD', toTimestamp: '2' },
      { fromAsset: 'BTC', fromTimestamp: '3', toAsset: 'USD', toTimestamp: '4' },
      { fromAsset: 'ETH', fromTimestamp: '5', toAsset: 'EUR', toTimestamp: '6' },
    ];
    mockGetPriceCache.mockResolvedValue(entries);

    const wrapper = createWrapper();
    await flushPromises();

    const vm = wrapper.vm as unknown as CacheContentVm;
    expect(vm.rows).toHaveLength(3);

    vm.filterFromAsset = 'ETH';
    await flushPromises();
    expect(vm.rows.map(r => r.fromAsset)).toEqual(['ETH', 'ETH']);

    vm.filterToAsset = 'USD';
    await flushPromises();
    expect(vm.rows).toHaveLength(1);
    expect(vm.rows[0]).toMatchObject({ fromAsset: 'ETH', toAsset: 'USD' });

    vm.clearFilter();
    await flushPromises();
    expect(vm.rows).toHaveLength(3);
  });
});
