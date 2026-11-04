import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import LocationUsageNotice from '@/modules/locations/components/LocationUsageNotice.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

interface Blocked {
  location: LocationNode;
  usage: Record<string, number>;
}

const luno = node('custom:luno', 'exchanges', 'Luno', { isBuiltin: false });

describe('locationUsageNotice', () => {
  let pinia: Pinia;

  function createWrapper(usage: Record<string, number>): VueWrapper<InstanceType<typeof LocationUsageNotice>> {
    const wrapper: VueWrapper<InstanceType<typeof LocationUsageNotice>> = mount(LocationUsageNotice, {
      global: {
        plugins: [pinia],
        stubs: {
          RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' },
          RuiAlert: { props: ['title'], template: '<div><strong>{{ title }}</strong><slot /></div>' },
        },
      },
      props: {
        'modelValue': { location: luno, usage },
        'onUpdate:modelValue': async (value: Blocked | undefined): Promise<void> => {
          await wrapper.setProps({ modelValue: value });
        },
      },
    });
    return wrapper;
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    useLocationTreeStore().setNodes([node('total', null, 'Total'), node('exchanges', 'total', 'Exchanges'), luno]);
  });

  it('should name the location by its path and each use by its label', () => {
    const wrapper = createWrapper({ historyEvents: 3, manuallyTrackedBalances: 1 });
    expect(wrapper.text()).toContain('location_manager.usage.title::Exchanges › Luno');
    expect(wrapper.findAll('[data-testid=location-usage-entry]').map(entry => entry.text())).toEqual([
      'location_manager.usage.kinds.history_events3',
      'location_manager.usage.kinds.manually_tracked_balances1',
    ]);
  });

  it('should link a use to where the data is and close on the way there', async () => {
    const wrapper = createWrapper({ historyEvents: 3 });
    const link = wrapper.find('[data-testid=location-usage-link]');
    expect(JSON.parse(link.attributes('data-to') ?? '')).toEqual({ name: '/history/events/', query: { location: 'custom:luno' } });

    await link.trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should archive the location from its usage and close', async () => {
    const wrapper = createWrapper({ historyEvents: 3 });
    await wrapper.find('[data-testid=location-usage-archive]').trigger('click');
    expect(wrapper.emitted('archive')).toEqual([[luno]]);
    expect(wrapper.find('[data-testid=location-usage]').exists()).toBe(false);
  });

  it('should close without archiving', async () => {
    const wrapper = createWrapper({ historyEvents: 3 });
    await wrapper.find('[data-testid=location-usage-close]').trigger('click');
    expect(wrapper.emitted('archive')).toBeUndefined();
    expect(wrapper.find('[data-testid=location-usage]').exists()).toBe(false);
  });
});
