import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupSyncProgressMocks } from '../test-utils';
import { type LocationProgress, LocationStatus } from '../types';
import LocationProgressItem from './LocationProgressItem.vue';

setupSyncProgressMocks();

describe('modules/sync-progress/components/LocationProgressItem', () => {
  let wrapper: VueWrapper<InstanceType<typeof LocationProgressItem>>;
  let pinia: Pinia;

  function createLocation(
    status: LocationStatus,
    options: Partial<LocationProgress> = {},
  ): LocationProgress {
    return {
      location: 'kraken',
      name: 'Kraken',
      status,
      ...options,
    };
  }

  function createWrapper(location: LocationProgress, compact = false): VueWrapper<InstanceType<typeof LocationProgressItem>> {
    return mount(LocationProgressItem, {
      global: {
        plugins: [pinia],
        stubs: {
          LocationIcon: {
            template: '<span data-testid="location-icon">{{ item }}</span>',
            props: ['item', 'icon', 'size'],
          },
          RuiIcon: {
            template: '<span data-testid="icon" :class="[$attrs.class]">{{ name }}</span>',
            props: ['name', 'size'],
          },
        },
      },
      props: {
        location,
        compact,
      },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('status display', () => {
    it('should display complete status and check icon', () => {
      const location = createLocation(LocationStatus.COMPLETE);
      wrapper = createWrapper(location);

      expect(wrapper.text()).toContain('sync_progress.status.complete');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-check');
    });

    it('should display pending status and circle icon', () => {
      const location = createLocation(LocationStatus.PENDING);
      wrapper = createWrapper(location);

      expect(wrapper.text()).toContain('sync_progress.status.pending');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-circle');
    });

    it('should display querying status and loader icon', () => {
      const location = createLocation(LocationStatus.QUERYING);
      wrapper = createWrapper(location);

      expect(wrapper.text()).toContain('sync_progress.status.querying');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-loader-circle');
    });

    it('should display event type when querying', () => {
      const location = createLocation(LocationStatus.QUERYING, { eventType: 'trade' });
      wrapper = createWrapper(location);

      expect(wrapper.text()).toContain('sync_progress.status.querying_event_type');
    });
  });

  describe('icon styling', () => {
    it('should apply success color for complete status', () => {
      const location = createLocation(LocationStatus.COMPLETE);
      wrapper = createWrapper(location);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-success');
    });

    it('should apply primary color and animation for querying status', () => {
      const location = createLocation(LocationStatus.QUERYING);
      wrapper = createWrapper(location);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-primary');
      expect(icon.classes()).toContain('animate-spin');
    });

    it('should apply disabled color for pending status', () => {
      const location = createLocation(LocationStatus.PENDING);
      wrapper = createWrapper(location);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-text-disabled');
    });
  });

  describe('location display', () => {
    it('should display location name', () => {
      const location = createLocation(LocationStatus.PENDING, { name: 'Binance' });
      wrapper = createWrapper(location);

      expect(wrapper.text()).toContain('Binance');
    });

    it('should display location icon', () => {
      const location = createLocation(LocationStatus.PENDING);
      wrapper = createWrapper(location);

      const locationIcon = wrapper.find('[data-testid="location-icon"]');
      expect(locationIcon.exists()).toBe(true);
      expect(locationIcon.text()).toContain('kraken');
    });
  });

  describe('visual feedback', () => {
    it('should animate for querying locations', () => {
      const location = createLocation(LocationStatus.QUERYING);
      wrapper = createWrapper(location);

      expect(wrapper.classes()).toContain('animate-pulse');
    });

    it('should not animate for complete locations', () => {
      const location = createLocation(LocationStatus.COMPLETE);
      wrapper = createWrapper(location);

      expect(wrapper.classes()).not.toContain('animate-pulse');
    });
  });

  describe('border styling', () => {
    it('should apply success border for complete status', () => {
      const location = createLocation(LocationStatus.COMPLETE);
      wrapper = createWrapper(location);

      expect(wrapper.classes()).toContain('border-l-rui-success');
    });

    it('should apply primary border for querying status', () => {
      const location = createLocation(LocationStatus.QUERYING);
      wrapper = createWrapper(location);

      expect(wrapper.classes()).toContain('border-l-rui-primary');
    });
  });
});
