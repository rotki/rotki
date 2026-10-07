import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import HistoricalBalancesFilters from '@/modules/statistics/historical-balances/components/HistoricalBalancesFilters.vue';
import { HistoricalBalancesMode } from '@/modules/statistics/historical-balances/historical-balances-view';
import { createRuiPlugin } from '@/plugins/rui';

vi.mock('@/modules/statistics/historical-balances/use-historical-balances-fields', async () => {
  const { computed } = await import('vue');
  return {
    useHistoricalBalancesFields: (): unknown => computed<Partial<FieldDef>[]>(() => [{ key: 'location' }, { key: 'account' }, { key: 'search' }]),
  };
});

let wrapper: VueWrapper<InstanceType<typeof HistoricalBalancesFilters>>;

function createWrapper(): VueWrapper<InstanceType<typeof HistoricalBalancesFilters>> {
  return mount(HistoricalBalancesFilters, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: { PillFilterBar: true },
    },
    props: {
      'accountOptions': [],
      'accounts': [],
      'locationOptions': [],
      'locations': [],
      'mode': HistoricalBalancesMode.COLLECTION,
      'onUpdate:accounts': (value: string[]): unknown => wrapper.setProps({ accounts: value }),
      'onUpdate:locations': (value: string[]): unknown => wrapper.setProps({ locations: value }),
      'onUpdate:mode': (value: HistoricalBalancesMode): unknown => wrapper.setProps({ mode: value }),
      'onUpdate:search': (value: string): unknown => wrapper.setProps({ search: value }),
      'search': '',
    },
  });
}

describe('historical balances filters', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    wrapper = createWrapper();
  });

  it('should filter through one pill bar holding every field', () => {
    const bars = wrapper.findAllComponents(PillFilterBar);

    expect(bars).toHaveLength(1);
    expect(bars[0].props('fields').map(({ key }: FieldDef) => key)).toEqual(['location', 'account', 'search']);
  });

  it('should hand what the bar holds to the page\'s filter models', async () => {
    wrapper.findComponent(PillFilterBar).vm.$emit('update:params', { accounts: ['0xA'], locations: ['optimism'], search: 'usdc' });
    await wrapper.vm.$nextTick();

    expect(wrapper.props()).toMatchObject({ accounts: ['0xA'], locations: ['optimism'], search: 'usdc' });
  });

  it('should switch to one row per asset', async () => {
    await wrapper.find('[data-testid=historical-balances-mode-flat]').trigger('click');

    expect(wrapper.props('mode')).toBe(HistoricalBalancesMode.FLAT);
  });
});
