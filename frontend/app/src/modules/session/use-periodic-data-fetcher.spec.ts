import type { PeriodicClientQueryResult } from '@/modules/session/types';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionMetadataStore } from '@/store/session/metadata';
import '@test/i18n';

const mockFetchPeriodicData = vi.fn();
const mockNotifyError = vi.fn();

vi.mock('@/composables/api/session', () => ({
  useSessionApi: vi.fn(() => ({
    fetchPeriodicData: mockFetchPeriodicData,
  })),
}));

vi.mock('@/modules/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
  })),
}));

vi.mock('@shared/utils', () => ({
  backoff: vi.fn(async (_retries: number, fn: () => Promise<unknown>): Promise<unknown> => fn()),
}));

describe('usePeriodicDataFetcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-periodic-data-fetcher')> {
    return import('./use-periodic-data-fetcher');
  }

  it('should update store with fetched periodic data', async () => {
    const result: PeriodicClientQueryResult = {
      connectedNodes: { eth: ['node1'] },
      coolingDownNodes: { eth: ['node3'] },
      failedToConnect: { bsc: ['node2'] },
      lastBalanceSave: 1234,
      lastDataUploadTs: 5678,
    };
    mockFetchPeriodicData.mockResolvedValue(result);

    const { usePeriodicDataFetcher } = await importModule();
    const { check } = usePeriodicDataFetcher();
    await check();

    const store = useSessionMetadataStore();
    expect(get(store.lastBalanceSave)).toBe(1234);
    expect(get(store.lastDataUpload)).toBe(5678);
    expect(get(store.connectedNodes)).toEqual({ eth: ['node1'] });
    expect(get(store.coolingDownNodes)).toEqual({ eth: ['node3'] });
    expect(get(store.failedToConnect)).toEqual({ bsc: ['node2'] });
  });

  it('should skip update when result is empty (user not logged in)', async () => {
    mockFetchPeriodicData.mockResolvedValue({});

    const { usePeriodicDataFetcher } = await importModule();
    const { check } = usePeriodicDataFetcher();
    await check();

    const store = useSessionMetadataStore();
    expect(get(store.lastBalanceSave)).toBe(0);
    expect(get(store.lastDataUpload)).toBe(0);
  });

  it('should clear optional node state maps when backend omits them', async () => {
    const store = useSessionMetadataStore();
    const { coolingDownNodes, failedToConnect } = storeToRefs(store);
    set(coolingDownNodes, { eth: ['cooling'] });
    set(failedToConnect, { eth: ['failed'] });

    const result: PeriodicClientQueryResult = {
      connectedNodes: {},
      lastBalanceSave: 1234,
      lastDataUploadTs: 9999,
    };
    mockFetchPeriodicData.mockResolvedValue(result);

    const { usePeriodicDataFetcher } = await importModule();
    const { check } = usePeriodicDataFetcher();
    await check();

    expect(get(store.coolingDownNodes)).toEqual({});
    expect(get(store.failedToConnect)).toEqual({});
  });

  it('should notify error on fetch failure', async () => {
    mockFetchPeriodicData.mockRejectedValue(new Error('network error'));

    const { usePeriodicDataFetcher } = await importModule();
    const { check } = usePeriodicDataFetcher();
    await check();

    expect(mockNotifyError).toHaveBeenCalledOnce();
  });

  it('should prevent concurrent executions', async () => {
    let resolveFirst: (value: PeriodicClientQueryResult) => void;
    const firstPromise = new Promise<PeriodicClientQueryResult>((resolve) => {
      resolveFirst = resolve;
    });
    mockFetchPeriodicData.mockReturnValueOnce(firstPromise);

    const { usePeriodicDataFetcher } = await importModule();
    const { check } = usePeriodicDataFetcher();

    const call1 = check();
    const call2 = check();

    resolveFirst!({
      connectedNodes: {},
      lastBalanceSave: 100,
      lastDataUploadTs: 200,
    });

    await Promise.all([call1, call2]);

    expect(mockFetchPeriodicData).toHaveBeenCalledOnce();
  });
});
