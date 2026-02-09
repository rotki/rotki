import type { KrakenStakingEvents } from '@/types/staking';
import { Zero } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Section, Status } from '@/types/status';
import { useKrakenStakingStore } from './kraken';

const mockFetchKrakenStakingEvents = vi.fn();
const mockRefreshKrakenStaking = vi.fn();
const mockNotify = vi.fn();

vi.mock('@/composables/api/staking/kraken', () => ({
  useKrakenApi: vi.fn(() => ({
    fetchKrakenStakingEvents: mockFetchKrakenStakingEvents,
    refreshKrakenStaking: mockRefreshKrakenStaking,
  })),
}));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssociatedAssetIdentifier: vi.fn((asset: string) => computed(() => asset)),
  })),
}));

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn(() => ({
    awaitTask: vi.fn().mockResolvedValue({}),
    isTaskRunning: vi.fn().mockReturnValue(false),
  })),
}));

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn(() => ({
    itemsPerPage: 10,
  })),
}));

function defaultEvents(): KrakenStakingEvents {
  return {
    assets: [],
    entriesFound: 0,
    entriesLimit: 0,
    entriesTotal: 0,
    received: [],
    totalValue: Zero,
  };
}

describe('store/staking/kraken', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('sets status to LOADED on first load error so the UI is not stuck loading', async () => {
    const { useStatusStore } = await import('@/store/status');

    mockFetchKrakenStakingEvents.mockRejectedValueOnce(new Error('Request timeout'));

    const store = useKrakenStakingStore();
    const statusStore = useStatusStore();

    await store.load();

    const status = statusStore.getStatus(Section.STAKING_KRAKEN);
    expect(status).toBe(Status.LOADED);
    expect(mockNotify).toHaveBeenCalledOnce();
  });

  it('loads events successfully on first load', async () => {
    const { useStatusStore } = await import('@/store/status');

    const eventsData = {
      ...defaultEvents(),
      entriesFound: 1,
      entriesTotal: 1,
    };

    mockFetchKrakenStakingEvents.mockResolvedValue(eventsData);
    mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

    const store = useKrakenStakingStore();
    const statusStore = useStatusStore();

    await store.load();

    const status = statusStore.getStatus(Section.STAKING_KRAKEN);
    expect(status).toBe(Status.LOADED);
    expect(mockNotify).not.toHaveBeenCalled();
  });

  it('sets status to LOADED when refresh task fails', async () => {
    const { useStatusStore } = await import('@/store/status');

    mockFetchKrakenStakingEvents.mockResolvedValueOnce(defaultEvents());
    mockRefreshKrakenStaking.mockRejectedValueOnce(new Error('Backend unresponsive'));

    const store = useKrakenStakingStore();
    const statusStore = useStatusStore();

    await store.load();

    const status = statusStore.getStatus(Section.STAKING_KRAKEN);
    expect(status).toBe(Status.LOADED);
    expect(mockNotify).toHaveBeenCalledOnce();
  });
});
