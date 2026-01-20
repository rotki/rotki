import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SyncPhase } from '../types';
import SyncProgressPanel from './SyncProgressPanel.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

const {
  mockCanDismiss,
  mockIsActive,
  mockPhase,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    mockCanDismiss: ref<boolean>(false),
    mockIsActive: ref<boolean>(false),
    mockPhase: ref<SyncPhase>('idle'),
  };
});

vi.mock('../composables/use-sync-progress', () => ({
  useSyncProgress: vi.fn().mockReturnValue({
    canDismiss: mockCanDismiss,
    isActive: mockIsActive,
    phase: mockPhase,
  }),
}));

describe('modules/sync-progress/components/SyncProgressPanel', () => {
  let wrapper: VueWrapper<InstanceType<typeof SyncProgressPanel>>;
  let pinia: Pinia;

  function createWrapper(): VueWrapper<InstanceType<typeof SyncProgressPanel>> {
    return mount(SyncProgressPanel, {
      global: {
        plugins: [pinia],
        stubs: {
          SyncProgressDetails: {
            template: '<div data-testid="details">Details</div>',
          },
          SyncProgressHeader: {
            template: '<div data-testid="header" @toggle="$emit(\'toggle\')" @dismiss="$emit(\'dismiss\')">Header</div>',
            props: ['expanded', 'canDismiss'],
            emits: ['toggle', 'dismiss'],
          },
          Teleport: {
            template: '<div data-testid="teleport"><slot /></div>',
          },
          Transition: {
            template: '<div><slot /></div>',
          },
        },
      },
    });
  }

  function resetMocks(): void {
    set(mockIsActive, false);
    set(mockPhase, SyncPhase.IDLE);
    set(mockCanDismiss, false);
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    resetMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('visibility', () => {
    it('should not be visible when not active', () => {
      set(mockIsActive, false);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="header"]').exists()).toBe(false);
    });

    it('should be visible when active', () => {
      set(mockIsActive, true);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="header"]').exists()).toBe(true);
    });

    it('should not be visible when dismissed', async () => {
      set(mockIsActive, true);
      set(mockCanDismiss, true);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="header"]').exists()).toBe(true);

      // Trigger dismiss
      await wrapper.find('[data-testid="header"]').trigger('dismiss');

      expect(wrapper.find('[data-testid="header"]').exists()).toBe(false);
    });
  });

  describe('expand/collapse', () => {
    it('should be collapsed by default', () => {
      set(mockIsActive, true);
      wrapper = createWrapper();

      expect(wrapper.find('[data-testid="details"]').exists()).toBe(false);
    });

    it('should expand when toggle is triggered', async () => {
      set(mockIsActive, true);
      wrapper = createWrapper();

      await wrapper.find('[data-testid="header"]').trigger('toggle');

      expect(wrapper.find('[data-testid="details"]').exists()).toBe(true);
    });

    it('should collapse when toggle is triggered again', async () => {
      set(mockIsActive, true);
      wrapper = createWrapper();

      await wrapper.find('[data-testid="header"]').trigger('toggle');
      expect(wrapper.find('[data-testid="details"]').exists()).toBe(true);

      await wrapper.find('[data-testid="header"]').trigger('toggle');
      expect(wrapper.find('[data-testid="details"]').exists()).toBe(false);
    });
  });

  describe('dismiss functionality', () => {
    it('should hide panel when dismiss is triggered', async () => {
      set(mockIsActive, true);
      set(mockCanDismiss, true);
      wrapper = createWrapper();

      await wrapper.find('[data-testid="header"]').trigger('dismiss');

      expect(wrapper.find('[data-testid="header"]').exists()).toBe(false);
    });
  });

  describe('phase change behavior', () => {
    it('should reset dismissed state when new sync starts', async () => {
      set(mockIsActive, true);
      set(mockCanDismiss, true);
      set(mockPhase, SyncPhase.COMPLETE);
      wrapper = createWrapper();

      // Dismiss the panel
      await wrapper.find('[data-testid="header"]').trigger('dismiss');
      expect(wrapper.find('[data-testid="header"]').exists()).toBe(false);

      // Simulate new sync starting
      set(mockPhase, SyncPhase.SYNCING);
      await nextTick();

      // Panel should be visible again
      expect(wrapper.find('[data-testid="header"]').exists()).toBe(true);
    });
  });

  describe('backdrop', () => {
    it('should show backdrop when expanded', async () => {
      set(mockIsActive, true);
      wrapper = createWrapper();

      await wrapper.find('[data-testid="header"]').trigger('toggle');

      const teleport = wrapper.find('[data-testid="teleport"]');
      expect(teleport.exists()).toBe(true);
    });
  });
});
