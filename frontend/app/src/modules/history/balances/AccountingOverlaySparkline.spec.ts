import type { PreparedBucket } from '@/modules/history/balances/accounting-overlay-helpers';
import type { UseAccountingOverlayReturn } from '@/modules/history/balances/use-accounting-overlay';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type Ref, type VNode } from 'vue';
import AccountingOverlaySparkline from '@/modules/history/balances/AccountingOverlaySparkline.vue';
import { provideAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';

let mockAllowed = true;
let mockShouldShowAmount = true;

vi.mock('@/modules/premium/use-feature-access', () => ({
  PremiumFeature: { GRAPHS_VIEW: 'graphsView' },
  useFeatureAccess: (): { allowed: Ref<boolean> } => ({ allowed: ref(mockAllowed) }),
}));

vi.mock('@/modules/assets/amount-display', () => ({
  useAmountDisplaySettings: (): { shouldShowAmount: Ref<boolean> } => ({ shouldShowAmount: ref(mockShouldShowAmount) }),
}));

vi.mock('@/modules/statistics/use-graph', () => ({
  useGraph: (): { baseColor: Ref<string>; gradient: Ref<object> } => ({ baseColor: ref('#000000'), gradient: ref({}) }),
}));

vi.mock('vue-echarts', () => ({
  default: { name: 'VChart', props: ['option'], template: '<div class="vchart" />' },
}));

const seriesFor = vi.fn<(locationLabel: string, asset: string) => Promise<PreparedBucket[] | undefined>>();

function series(times: number[]): PreparedBucket[] {
  return [{ location: 'ethereum', protocol: null, times, values: times.map(() => bigNumberify('1')) }];
}

function mountSparkline(): VueWrapper {
  const host = defineComponent({
    setup() {
      provideAccountingOverlay({
        enabled: ref(true),
        overlay: createMock<UseAccountingOverlayReturn>(),
        series: { reset: () => {}, seriesFor },
      });
      return (): VNode => h(AccountingOverlaySparkline, {
        balance: bigNumberify('3'),
        event: createMock<HistoryEventEntry>({ asset: 'ETH', identifier: 1, locationLabel: '0xA', timestamp: 250_000 }),
      });
    },
  });
  return mount(host, { global: { stubs: { RuiSkeletonLoader: { template: '<div class="skeleton" />' } } } });
}

describe('accountingOverlaySparkline.vue', () => {
  beforeEach(() => {
    mockAllowed = true;
    mockShouldShowAmount = true;
    seriesFor.mockReset().mockResolvedValue(series([100, 200]));
  });

  it('should render the chart from the account series for premium users', async () => {
    const wrapper = mountSparkline();
    await flushPromises();
    expect(seriesFor).toHaveBeenCalledExactlyOnceWith('0xA', 'ETH');
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(true);
    expect(wrapper.find('.vchart').exists()).toBe(true);
  });

  it('should hold the chart space with a skeleton while the series loads', async () => {
    seriesFor.mockReturnValue(new Promise<PreparedBucket[]>(() => {}));
    const wrapper = mountSparkline();
    await flushPromises();
    expect(wrapper.find('[data-testid=overlay-sparkline-loading]').exists()).toBe(true);
    expect(wrapper.find('.vchart').exists()).toBe(false);
  });

  it('should render nothing and fetch nothing for non-premium users', async () => {
    mockAllowed = false;
    const wrapper = mountSparkline();
    await flushPromises();
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
    expect(seriesFor).not.toHaveBeenCalled();
  });

  it('should render nothing and fetch nothing while amounts are hidden (privacy mode)', async () => {
    mockShouldShowAmount = false;
    const wrapper = mountSparkline();
    await flushPromises();
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
    expect(seriesFor).not.toHaveBeenCalled();
  });

  it('should render nothing when the series has no point before the event', async () => {
    seriesFor.mockResolvedValue(series([300]));
    const wrapper = mountSparkline();
    await flushPromises();
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
  });
});
