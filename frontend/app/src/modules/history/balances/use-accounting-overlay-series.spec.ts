import type { EffectScope } from 'vue';
import type { HistoricalBalanceSeriesPayload } from './types';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import { err, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { useAccountingOverlaySeries, type UseAccountingOverlaySeriesReturn } from './use-accounting-overlay-series';

const { runTaskMock, fetchSeries } = vi.hoisted(() => ({
  runTaskMock: vi.fn(),
  fetchSeries: vi.fn<(payload: HistoricalBalanceSeriesPayload) => Promise<{ taskId: number }>>(),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { runTask: runTaskMock }));
vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): { fetchHistoricalBalanceSeries: typeof fetchSeries } => ({ fetchHistoricalBalanceSeries: fetchSeries }),
}));

function success(): unknown {
  return ok({ processingRequired: false, entries: [{
    location: 'ethereum',
    locationLabel: '0xA',
    asset: 'ETH',
    protocol: null,
    times: [100, 200],
    values: ['5', '7'],
  }] });
}

let scope: EffectScope;

function create(): UseAccountingOverlaySeriesReturn {
  const series = scope.run(() => useAccountingOverlaySeries());
  assert(series);
  return series;
}

describe('useAccountingOverlaySeries', () => {
  beforeEach(() => {
    scope = effectScope();
    fetchSeries.mockReset().mockResolvedValue({ taskId: 1 });
    runTaskMock.mockReset().mockResolvedValue(success());
  });

  afterEach(() => scope.stop());

  it('should fetch one full series per account and asset and share it between rows', async () => {
    const { seriesFor } = create();
    const [first, second] = await Promise.all([seriesFor('0xA', 'ETH'), seriesFor('0xA', 'ETH')]);

    expect(fetchSeries).toHaveBeenCalledExactlyOnceWith({ asset: 'ETH', locationLabel: '0xA' });
    expect(second).toBe(first);
    expect(first?.[0].values.map(value => value.toString())).toEqual(['5', '7']);

    await seriesFor('0xA', 'DAI');
    expect(fetchSeries).toHaveBeenCalledTimes(2);
  });

  it('should retry a series that failed on the next request', async () => {
    runTaskMock.mockResolvedValueOnce(err(TaskFailed({ message: 'boom' })));
    const { seriesFor } = create();

    expect(await seriesFor('0xA', 'ETH')).toBeUndefined();
    expect(await seriesFor('0xA', 'ETH')).toHaveLength(1);
    expect(fetchSeries).toHaveBeenCalledTimes(2);
  });

  it('should refetch a series after a reset', async () => {
    const { reset, seriesFor } = create();
    await seriesFor('0xA', 'ETH');
    reset();
    await seriesFor('0xA', 'ETH');
    expect(fetchSeries).toHaveBeenCalledTimes(2);
  });
});
