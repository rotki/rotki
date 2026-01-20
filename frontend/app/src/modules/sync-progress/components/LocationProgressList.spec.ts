import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupSyncProgressMocks } from '../test-utils';
import { type LocationProgress, LocationStatus } from '../types';
import LocationProgressList from './LocationProgressList.vue';

setupSyncProgressMocks();

describe('modules/sync-progress/components/LocationProgressList', () => {
  let wrapper: VueWrapper<InstanceType<typeof LocationProgressList>>;
  let pinia: Pinia;

  function createLocationProgress(
    location: string,
    name: string,
    status: LocationStatus,
  ): LocationProgress {
    return {
      location,
      name,
      status,
    };
  }

  function createWrapper(locations: LocationProgress[]): VueWrapper<InstanceType<typeof LocationProgressList>> {
    return mount(LocationProgressList, {
      global: {
        plugins: [pinia],
        stubs: {
          LocationProgressItem: {
            template: '<div data-testid="location-item" :data-location="location.location" :data-compact="String(compact === true)">{{ location.name }}</div>',
            props: {
              location: { type: Object, required: true },
              compact: { type: Boolean, default: false },
            },
          },
          RuiIcon: {
            template: '<span data-testid="icon">{{ name }}</span>',
            props: ['name', 'size'],
          },
        },
      },
      props: {
        locations,
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

  describe('filtering', () => {
    it('should show in-progress locations by default', () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      const items = wrapper.findAll('[data-testid="location-item"]');
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-location')).toBe('kraken');
    });

    it('should show pending locations in in-progress section', () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.PENDING),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      const items = wrapper.findAll('[data-testid="location-item"]');
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-location')).toBe('kraken');
    });

    it('should not show completed locations by default', () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.COMPLETE),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      expect(wrapper.findAll('[data-testid="location-item"]')).toHaveLength(0);
    });
  });

  describe('completed section', () => {
    it('should show completed toggle button when there are completed locations', () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      expect(wrapper.text()).toContain('sync_progress.completed_locations');
    });

    it('should not show completed toggle when no completed locations', () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING),
        createLocationProgress('binance', 'Binance', LocationStatus.PENDING),
      ];
      wrapper = createWrapper(locations);

      expect(wrapper.text()).not.toContain('sync_progress.completed_locations');
    });

    it('should show completed locations when toggle is clicked', async () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_locations'));
      await toggleButton?.trigger('click');

      const items = wrapper.findAll('[data-testid="location-item"]');
      expect(items).toHaveLength(2);
    });

    it('should render completed locations in compact mode', async () => {
      const locations = [
        createLocationProgress('kraken', 'Kraken', LocationStatus.QUERYING),
        createLocationProgress('binance', 'Binance', LocationStatus.COMPLETE),
      ];
      wrapper = createWrapper(locations);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_locations'));
      await toggleButton?.trigger('click');

      const inProgressItem = wrapper.findAll('[data-testid="location-item"]').find(
        item => item.attributes('data-location') === 'kraken',
      );
      const completedItem = wrapper.findAll('[data-testid="location-item"]').find(
        item => item.attributes('data-location') === 'binance',
      );
      // In-progress items are not compact
      expect(inProgressItem?.attributes('data-compact')).toBe('false');
      // Completed items are rendered in compact mode
      expect(completedItem?.attributes('data-compact')).toBe('true');
    });
  });

  describe('empty state', () => {
    it('should render empty list when no locations', () => {
      wrapper = createWrapper([]);

      expect(wrapper.findAll('[data-testid="location-item"]')).toHaveLength(0);
    });
  });
});
