import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AddressStatus, AddressSubtype, type ChainProgress, type DecodingProgress, type LocationProgress, LocationStatus, type ProtocolCacheProgress } from '../types';
import SyncProgressDetails from './SyncProgressDetails.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

const {
  mockChains,
  mockCompletedChains,
  mockCompletedLocations,
  mockDecoding,
  mockLocations,
  mockProtocolCache,
  mockTotalChains,
  mockTotalLocations,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    mockChains: ref<ChainProgress[]>([]),
    mockCompletedChains: ref<number>(0),
    mockCompletedLocations: ref<number>(0),
    mockDecoding: ref<DecodingProgress[]>([]),
    mockLocations: ref<LocationProgress[]>([]),
    mockProtocolCache: ref<ProtocolCacheProgress[]>([]),
    mockTotalChains: ref<number>(0),
    mockTotalLocations: ref<number>(0),
  };
});

vi.mock('../composables/use-sync-progress', () => ({
  useSyncProgress: vi.fn().mockReturnValue({
    chains: mockChains,
    completedChains: mockCompletedChains,
    completedLocations: mockCompletedLocations,
    decoding: mockDecoding,
    locations: mockLocations,
    protocolCache: mockProtocolCache,
    totalChains: mockTotalChains,
    totalLocations: mockTotalLocations,
  }),
}));

describe('modules/sync-progress/components/SyncProgressDetails', () => {
  let wrapper: VueWrapper<InstanceType<typeof SyncProgressDetails>>;
  let pinia: Pinia;

  function createChainProgress(chain: string, completed: number, total: number): ChainProgress {
    return {
      addresses: Array.from({ length: total }, (_, i) => ({
        address: `0x${i.toString().padStart(40, '0')}`,
        status: i < completed ? AddressStatus.COMPLETE : AddressStatus.PENDING,
        subtype: AddressSubtype.EVM,
      })),
      chain,
      completed,
      inProgress: 0,
      pending: total - completed,
      progress: total > 0 ? Math.round((completed / total) * 100) : 0,
      total,
    };
  }

  function createLocationProgress(location: string, name: string, status: LocationStatus): LocationProgress {
    return { location, name, status };
  }

  function createDecodingProgress(chain: string, processed: number, total: number): DecodingProgress {
    return {
      chain,
      processed,
      progress: total > 0 ? Math.round((processed / total) * 100) : 0,
      total,
    };
  }

  function createWrapper(): VueWrapper<InstanceType<typeof SyncProgressDetails>> {
    return mount(SyncProgressDetails, {
      global: {
        plugins: [pinia],
        stubs: {
          ChainProgressList: {
            template: '<div data-testid="chain-list">{{ chains.length }} chains</div>',
            props: ['chains'],
          },
          DecodingProgressList: {
            template: '<div data-testid="decoding-list">{{ decoding.length }} decoding</div>',
            props: ['decoding'],
          },
          LocationProgressList: {
            template: '<div data-testid="location-list">{{ locations.length }} locations</div>',
            props: ['locations'],
          },
          ProtocolCacheProgressList: {
            template: '<div data-testid="protocol-cache-list">{{ protocolCache.length }} protocols</div>',
            props: ['protocolCache'],
          },
          RuiIcon: {
            template: '<span data-testid="icon">{{ name }}</span>',
            props: ['name', 'size'],
          },
        },
      },
    });
  }

  function resetMocks(): void {
    set(mockChains, []);
    set(mockLocations, []);
    set(mockDecoding, []);
    set(mockProtocolCache, []);
    set(mockCompletedChains, 0);
    set(mockTotalChains, 0);
    set(mockCompletedLocations, 0);
    set(mockTotalLocations, 0);
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    resetMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('sections rendering', () => {
    it('should show chains section when there are chains', () => {
      set(mockChains, [createChainProgress('eth', 1, 3)]);
      set(mockTotalChains, 1);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="chain-list"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('sync_progress.transactions');
    });

    it('should not show chains section when there are no chains', () => {
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="chain-list"]').exists()).toBe(false);
    });

    it('should show locations section when there are locations', () => {
      set(mockLocations, [createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING)]);
      set(mockTotalLocations, 1);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="location-list"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('sync_progress.events');
    });

    it('should not show locations section when there are no locations', () => {
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="location-list"]').exists()).toBe(false);
    });

    it('should show decoding section when there is decoding data', () => {
      set(mockDecoding, [createDecodingProgress('eth', 50, 100)]);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="decoding-list"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('sync_progress.decoding');
    });

    it('should not show decoding section when there is no decoding data', () => {
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="decoding-list"]').exists()).toBe(false);
    });
  });

  describe('counts display', () => {
    it('should display chain completion counts', () => {
      set(mockChains, [createChainProgress('eth', 2, 3)]);
      set(mockCompletedChains, 1);
      set(mockTotalChains, 2);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/2');
    });

    it('should display location completion counts', () => {
      set(mockLocations, [createLocationProgress('kraken', 'Kraken', LocationStatus.COMPLETE)]);
      set(mockCompletedLocations, 1);
      set(mockTotalLocations, 2);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/2');
    });

    it('should display decoding completion counts', () => {
      set(mockDecoding, [
        createDecodingProgress('eth', 100, 100),
        createDecodingProgress('optimism', 50, 100),
      ]);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/2');
    });
  });

  describe('completion indicators', () => {
    it('should show check icon when all chains are complete', () => {
      set(mockChains, [createChainProgress('eth', 3, 3)]);
      set(mockCompletedChains, 1);
      set(mockTotalChains, 1);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-check')).toBe(true);
    });

    it('should show check icon when all locations are complete', () => {
      set(mockLocations, [createLocationProgress('kraken', 'Kraken', LocationStatus.COMPLETE)]);
      set(mockCompletedLocations, 1);
      set(mockTotalLocations, 1);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-check')).toBe(true);
    });

    it('should show check icon when all decoding is complete', () => {
      set(mockDecoding, [createDecodingProgress('eth', 100, 100)]);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-check')).toBe(true);
    });
  });

  describe('all sections together', () => {
    it('should render all sections when data is present', () => {
      set(mockChains, [createChainProgress('eth', 1, 3)]);
      set(mockTotalChains, 1);
      set(mockLocations, [createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING)]);
      set(mockTotalLocations, 1);
      set(mockDecoding, [createDecodingProgress('eth', 50, 100)]);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="chain-list"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="location-list"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="decoding-list"]').exists()).toBe(true);
    });
  });
});
