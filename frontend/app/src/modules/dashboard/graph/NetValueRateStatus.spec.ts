import type { FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { SnapshotRateStatus } from '@/modules/statistics/pricing/use-snapshot-rate-status';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import NetValueRateStatus from '@/modules/dashboard/graph/NetValueRateStatus.vue';

const { failedDailyPrices, status } = await vi.hoisted(async () => {
  const { shallowRef: createShallowRef } = await import('vue');
  return {
    failedDailyPrices: createShallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({}),
    status: createShallowRef<SnapshotRateStatus>({ pending: 0, rateLimited: false, unavailable: 0 }),
  };
});

vi.mock('@/modules/statistics/pricing/use-snapshot-rate-status', () => ({
  useSnapshotRateStatus: (): { status: typeof status } => ({ status }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): { failedDailyPrices: typeof failedDailyPrices } => ({ failedDailyPrices }),
}));

function createWrapper(): VueWrapper<InstanceType<typeof NetValueRateStatus>> {
  return mount(NetValueRateStatus, {
    global: {
      stubs: {
        MissingDailyPrices: { name: 'MissingDailyPrices', props: ['asset'], template: '<div data-testid="missing-daily-prices" />' },
        RuiButton: { template: '<button v-bind="$attrs"><slot /></button>' },
        RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
      },
    },
  });
}

describe('netValueRateStatus', () => {
  beforeEach(() => {
    set(status, { pending: 0, rateLimited: false, unavailable: 0 });
    set(failedDailyPrices, {});
  });

  it('should show nothing when every snapshot has its own rate', () => {
    expect(createWrapper().find('[data-testid=net-value-rate-status]').exists()).toBe(false);
  });

  it('should say rates are being fetched, or that the oracles are rate limiting instead', async () => {
    set(status, { pending: 3, rateLimited: false, unavailable: 0 });
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=net-value-rate-status-pending]').exists()).toBe(true);

    set(status, { pending: 3, rateLimited: true, unavailable: 0 });
    await nextTick();
    expect(wrapper.find('[data-testid=net-value-rate-status-pending]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=net-value-rate-status-rate-limited]').exists()).toBe(true);
  });

  it('should open the missing rates of USD to add them by hand when the oracles have none', async () => {
    set(status, { pending: 0, rateLimited: false, unavailable: 2 });
    set(failedDailyPrices, { USD: { noPricesTimestamps: [86400], rateLimitedPricesTimestamps: [] } });
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=net-value-rate-status-unavailable]').exists()).toBe(true);

    await wrapper.find('[data-testid=net-value-rate-status-add]').trigger('click');
    expect(wrapper.findComponent({ name: 'MissingDailyPrices' }).props('asset')).toBe('USD');
  });

  it('should not offer to add rates before the backend reported which days lack one', () => {
    set(status, { pending: 0, rateLimited: false, unavailable: 2 });
    expect(createWrapper().find('[data-testid=net-value-rate-status-add]').exists()).toBe(false);
  });
});
