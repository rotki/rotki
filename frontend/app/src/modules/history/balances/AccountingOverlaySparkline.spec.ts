import type { SparklinePoint } from '@/modules/history/balances/use-accounting-overlay';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, type Ref } from 'vue';
import AccountingOverlaySparkline from '@/modules/history/balances/AccountingOverlaySparkline.vue';

// `mock`-prefixed so they can be read inside the hoisted factories.
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

// Stub the echarts component so no real chart/canvas is initialized in jsdom.
vi.mock('vue-echarts', () => ({
  default: { name: 'VChart', props: ['option'], template: '<div class="vchart" />' },
}));

const twoPoints: SparklinePoint[] = [
  { time: 100, value: 1 },
  { time: 200, value: 3 },
];

function mountSparkline(points: SparklinePoint[]): VueWrapper {
  return mount(AccountingOverlaySparkline, { props: { points } });
}

describe('accountingOverlaySparkline.vue', () => {
  beforeEach(() => {
    mockAllowed = true;
    mockShouldShowAmount = true;
  });

  it('should render the chart for premium users with enough points', () => {
    const wrapper = mountSparkline(twoPoints);
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(true);
    expect(wrapper.find('.vchart').exists()).toBe(true);
  });

  it('should render nothing for non-premium users', () => {
    mockAllowed = false;
    const wrapper = mountSparkline(twoPoints);
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
  });

  it('should render nothing while amounts are hidden (privacy mode)', () => {
    mockShouldShowAmount = false;
    const wrapper = mountSparkline(twoPoints);
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
  });

  it('should render nothing with fewer than two points', () => {
    const wrapper = mountSparkline([{ time: 100, value: 1 }]);
    expect(wrapper.find('[data-testid=overlay-sparkline]').exists()).toBe(false);
  });
});
