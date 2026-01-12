import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type DecodingProgress, type ProtocolCacheProgress, SyncPhase } from '../types';
import SyncProgressHeader from './SyncProgressHeader.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

const {
  mockCompletedChains,
  mockCompletedLocations,
  mockDecoding,
  mockOverallProgress,
  mockPhase,
  mockProtocolCache,
  mockTotalChains,
  mockTotalLocations,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    mockCompletedChains: ref<number>(0),
    mockCompletedLocations: ref<number>(0),
    mockDecoding: ref<DecodingProgress[]>([]),
    mockOverallProgress: ref<number>(0),
    mockPhase: ref<SyncPhase>('idle'),
    mockProtocolCache: ref<ProtocolCacheProgress[]>([]),
    mockTotalChains: ref<number>(0),
    mockTotalLocations: ref<number>(0),
  };
});

vi.mock('../composables/use-sync-progress', () => ({
  useSyncProgress: vi.fn().mockReturnValue({
    completedChains: mockCompletedChains,
    completedLocations: mockCompletedLocations,
    decoding: mockDecoding,
    overallProgress: mockOverallProgress,
    phase: mockPhase,
    protocolCache: mockProtocolCache,
    totalChains: mockTotalChains,
    totalLocations: mockTotalLocations,
  }),
}));

describe('modules/sync-progress/components/SyncProgressHeader', () => {
  let wrapper: VueWrapper<InstanceType<typeof SyncProgressHeader>>;
  let pinia: Pinia;

  function createWrapper(expanded = false, canDismiss = false): VueWrapper<InstanceType<typeof SyncProgressHeader>> {
    return mount(SyncProgressHeader, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiButton: {
            template: '<button data-testid="button" @click="$emit(\'click\', $event)"><slot /></button>',
          },
          RuiIcon: {
            template: '<span data-testid="icon" :class="[$attrs.class]">{{ name }}</span>',
            props: ['name', 'size'],
          },
          RuiProgress: {
            template: '<div data-testid="progress" :data-value="value"></div>',
            props: ['value', 'color', 'size', 'rounded'],
          },
        },
      },
      props: {
        canDismiss,
        expanded,
      },
    });
  }

  function resetMocks(): void {
    set(mockPhase, SyncPhase.IDLE);
    set(mockOverallProgress, 0);
    set(mockTotalChains, 0);
    set(mockCompletedChains, 0);
    set(mockTotalLocations, 0);
    set(mockCompletedLocations, 0);
    set(mockDecoding, []);
    set(mockProtocolCache, []);
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    resetMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('phase display', () => {
    it('should show syncing title when phase is SYNCING', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('sync_progress.title');
    });

    it('should show complete title when phase is COMPLETE', () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('sync_progress.complete');
    });
  });

  describe('status icons', () => {
    it('should show loader icon when syncing', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-loader-circle')).toBe(true);
    });

    it('should show check icon when complete', () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-circle-check')).toBe(true);
    });

    it('should animate loader when syncing and progress < 100', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockOverallProgress, 50);
      wrapper = createWrapper();

      const icons = wrapper.findAll('[data-testid="icon"]');
      const loaderIcon = icons.find(icon => icon.text() === 'lu-loader-circle');
      expect(loaderIcon?.classes()).toContain('animate-spin');
    });
  });

  describe('progress bar', () => {
    it('should show progress bar when syncing', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockOverallProgress, 50);
      wrapper = createWrapper();

      const progress = wrapper.find('[data-testid="progress"]');
      expect(progress.exists()).toBe(true);
      expect(progress.attributes('data-value')).toBe('50');
    });

    it('should not show progress bar when complete', () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="progress"]').exists()).toBe(false);
    });
  });

  describe('counts display', () => {
    it('should show chain counts when there are chains', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockTotalChains, 3);
      set(mockCompletedChains, 1);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/3');
      expect(wrapper.text()).toContain('sync_progress.chains_label');
    });

    it('should not show chain counts when there are no chains', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper();

      expect(wrapper.text()).not.toContain('sync_progress.chains_label');
    });

    it('should show location counts when there are locations', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockTotalLocations, 2);
      set(mockCompletedLocations, 1);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/2');
      expect(wrapper.text()).toContain('sync_progress.locations_label');
    });

    it('should show decoding counts when there is decoding', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockDecoding, [
        { chain: 'eth', processed: 100, progress: 100, total: 100 },
        { chain: 'optimism', processed: 50, progress: 50, total: 100 },
      ]);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('1/2');
      expect(wrapper.text()).toContain('sync_progress.decoding_label');
    });
  });

  describe('toggle button', () => {
    it('should show chevron down when collapsed', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper(false);

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-chevron-down')).toBe(true);
    });

    it('should show chevron up when expanded', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper(true);

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-chevron-up')).toBe(true);
    });

    it('should emit toggle event when header is clicked', async () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper();

      await wrapper.trigger('click');

      expect(wrapper.emitted('toggle')).toBeTruthy();
    });
  });

  describe('dismiss button', () => {
    it('should not show dismiss button when canDismiss is false', () => {
      set(mockPhase, SyncPhase.SYNCING);
      wrapper = createWrapper(false, false);

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-x')).toBe(false);
    });

    it('should show dismiss button when canDismiss is true', () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper(false, true);

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-x')).toBe(true);
    });

    it('should emit dismiss event when dismiss button is clicked', async () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper(false, true);

      const dismissButton = wrapper.find('[data-testid="button"]');
      await dismissButton.trigger('click');

      expect(wrapper.emitted('dismiss')).toBeTruthy();
    });
  });

  describe('percentage display', () => {
    it('should show percentage when syncing', () => {
      set(mockPhase, SyncPhase.SYNCING);
      set(mockOverallProgress, 75);
      wrapper = createWrapper();

      expect(wrapper.text()).toContain('percentage_display.value');
    });

    it('should not show percentage when complete', () => {
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper();

      expect(wrapper.text()).not.toContain('percentage_display.value');
    });
  });
});
