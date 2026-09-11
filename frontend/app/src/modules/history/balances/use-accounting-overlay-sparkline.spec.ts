import type { ComputedRef, EffectScope } from 'vue';
import type { HistoricalBalanceSeriesPayload } from './types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import flushPromises from 'flush-promises';
import { ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingOverlaySparkline } from './use-accounting-overlay-sparkline';

const { runTaskMock, fetchSeries } = vi.hoisted(() => ({
  runTaskMock: vi.fn(),
  fetchSeries: vi.fn<(payload: HistoricalBalanceSeriesPayload) => Promise<{ taskId: number }>>(),
}));

const flags = reactive<{ allowed: boolean; visible: boolean }>({ allowed: true, visible: true });

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { runTask: runTaskMock }));
vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): { fetchHistoricalBalanceSeries: typeof fetchSeries } => ({ fetchHistoricalBalanceSeries: fetchSeries }),
}));
vi.mock('@/modules/premium/use-feature-access', async importOriginal => ({
  ...await importOriginal<Record<string, unknown>>(),
  useFeatureAccess: (): { allowed: ComputedRef<boolean> } => ({ allowed: computed<boolean>(() => flags.allowed) }),
}));
vi.mock('@/modules/assets/amount-display', () => ({
  useAmountDisplaySettings: (): { shouldShowAmount: ComputedRef<boolean> } => ({ shouldShowAmount: computed<boolean>(() => flags.visible) }),
}));

let scope: EffectScope;

describe('useAccountingOverlaySparkline', () => {
  beforeEach(() => {
    scope = effectScope();
    flags.allowed = true;
    flags.visible = true;
    fetchSeries.mockReset().mockResolvedValue({ taskId: 1 });
    runTaskMock.mockReset().mockResolvedValue(ok({ processingRequired: false, entries: [{
      location: 'ethereum',
      locationLabel: '0xA',
      asset: 'ETH',
      protocol: null,
      times: [100, 200, 300],
      values: ['5', '7', '9'],
    }] }));
  });

  afterEach(() => scope.stop());

  it('should defer the series until an eligible visible menu opens and end at the exact snapshot', async () => {
    const open = ref<boolean>(false);
    const event = createMock<HistoryEventEntry>({ identifier: 1, asset: 'ETH', locationLabel: '0xA', timestamp: 250_000 });
    const points = scope.run(() => useAccountingOverlaySparkline(() => event, open, bigNumberify('0')));
    assert(points);
    await flushPromises();
    expect(fetchSeries).not.toHaveBeenCalled();
    flags.allowed = false;
    set(open, true);
    await flushPromises();
    expect(fetchSeries).not.toHaveBeenCalled();
    flags.allowed = true;
    flags.visible = false;
    await flushPromises();
    expect(fetchSeries).not.toHaveBeenCalled();
    flags.visible = true;
    await flushPromises();
    expect(fetchSeries).toHaveBeenCalledExactlyOnceWith({ asset: 'ETH', locationLabel: '0xA', toTimestamp: 250 });
    expect(get(points)).toEqual([{ time: 100, value: 5 }, { time: 200, value: 7 }, { time: 250, value: 0 }]);
    set(open, false);
    await flushPromises();
    set(open, true);
    await flushPromises();
    expect(fetchSeries).toHaveBeenCalledOnce();
  });
});
