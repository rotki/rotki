import type { EChartsOption, LineSeriesOption } from 'echarts';
import type { BucketSeries } from '@/modules/balances/account-history/balance-series';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountBalanceChart from '@/modules/balances/account-history/components/chart/AccountBalanceChart.vue';
import { createRuiPlugin } from '@/plugins/rui';

vi.mock('vue-echarts', () => ({
  default: { name: 'VChart', props: ['option', 'updateOptions', 'autoresize'], template: '<div data-testid="vchart-stub" />' },
}));
vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): Record<string, unknown> => ({
    getLocationData: (id: string): { name: string } | undefined => (id === 'ethereum' ? { name: 'Ethereum' } : undefined),
  }),
}));
vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', async () => {
  const { computed } = await import('vue');
  return {
    useHistoryEventCounterpartyMappings: (): Record<string, unknown> => ({
      getCounterpartyData: (id: string): unknown => computed(() => ({ label: id === 'aave' ? 'Aave' : id })),
    }),
  };
});

function bucket(location: string, protocol: string | undefined): BucketSeries {
  return {
    key: `${location}:${protocol ?? ''}`,
    location,
    points: [{ time: 100, value: bigNumberify(1) }],
    protocol,
  };
}

function createWrapper(slots: Record<string, string> = {}): VueWrapper<InstanceType<typeof AccountBalanceChart>> {
  return mount(AccountBalanceChart, {
    global: { plugins: [createPinia(), createRuiPlugin({})] },
    slots,
    props: {
      buckets: [bucket('ethereum', undefined), bucket('ethereum', 'aave'), bucket('base', undefined)],
      total: [{ time: 100, value: bigNumberify(3) }],
    },
  });
}

function seriesOf(wrapper: VueWrapper<InstanceType<typeof AccountBalanceChart>>): LineSeriesOption[] {
  const option: EChartsOption = wrapper.findComponent({ name: 'VChart' }).props('option');
  assert(Array.isArray(option.series));
  return option.series.filter((item): item is LineSeriesOption => item.type === 'line');
}

describe('account balance chart', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should name each bucket by its location and protocol, or wallet outside one', () => {
    const names = seriesOf(createWrapper()).map(({ name }) => name);

    expect(names).toEqual(['Ethereum · account_history.chart.wallet', 'Ethereum · Aave', 'Base · account_history.chart.wallet']);
  });

  it('should switch from stacked buckets to the single total line', async () => {
    const wrapper = createWrapper();
    expect(seriesOf(wrapper)).toHaveLength(3);

    await wrapper.find('[data-testid=account-balance-chart-mode-total]').trigger('click');

    expect(seriesOf(wrapper)).toHaveLength(1);
  });

  it('should show the placeholder at the chart\'s size in place of the chart, without the mode switch', () => {
    const wrapper = createWrapper({ placeholder: '<span data-testid="message">nothing</span>' });

    expect(wrapper.find('[data-testid=account-balance-chart-placeholder]').classes()).toContain('h-72');
    expect(wrapper.find('[data-testid=message]').exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'VChart' }).exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-balance-chart-mode]').exists()).toBe(false);
  });

  it('should keep the header actions usable over a placeholder', () => {
    const wrapper = createWrapper({
      actions: '<button data-testid="action">range</button>',
      placeholder: '<span>nothing</span>',
    });

    expect(wrapper.find('[data-testid=action]').attributes('disabled')).toBeUndefined();
  });

  it('should offer the mode switch only for more than one bucket', () => {
    const one = mount(AccountBalanceChart, {
      global: { plugins: [createPinia(), createRuiPlugin({})] },
      props: { buckets: [bucket('ethereum', undefined)], total: [{ time: 100, value: bigNumberify(1) }] },
    });

    expect(one.find('[data-testid=account-balance-chart-mode]').exists()).toBe(false);
    expect(createWrapper().find('[data-testid=account-balance-chart-mode]').exists()).toBe(true);
  });
});
