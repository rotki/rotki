import type { EffectScope, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { AccountingOverlayContext } from '@/modules/history/balances/use-accounting-overlay-context';
import type { UseAccountingOverlaySeriesReturn } from '@/modules/history/balances/use-accounting-overlay-series';
import type { UseCostBasisOverlayReturn } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import type { CostBasisOverlayContext } from '@/modules/history/cost-basis/use-cost-basis-overlay-context';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { createHistoricalBalanceProcessingCompletedHandler } from '@/modules/core/messaging/handlers/historical-balance-processing-completed';
import { WebsocketMessage } from '@/modules/core/messaging/messages';
import { HistoricalBalanceProcessingPhase } from '@/modules/core/messaging/types/status-types';
import { OverlayMode, type UseAccountingOverlayReturn } from '@/modules/history/balances/use-accounting-overlay';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useHistoryEventsOverlay } from './use-history-events-overlay';

interface OverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  eventIdentifiers: MaybeRefOrGetter<number[]>;
}

const {
  accountingUpdateEnabled,
  provideCostBasis,
  provideOverlay,
  refresh,
  refreshCostBasis,
  refreshProcessing,
  reset,
  useCostBasis,
  useOverlay,
} = vi.hoisted(() => ({
  accountingUpdateEnabled: vi.fn<() => boolean>(),
  provideCostBasis: vi.fn<(context: CostBasisOverlayContext) => void>(),
  provideOverlay: vi.fn<(context: AccountingOverlayContext) => void>(),
  refresh: vi.fn<() => Promise<void>>(),
  refreshCostBasis: vi.fn<() => Promise<void>>(),
  refreshProcessing: vi.fn<() => Promise<void>>(),
  reset: vi.fn<() => void>(),
  useCostBasis: vi.fn<(params: OverlayParams) => UseCostBasisOverlayReturn>(),
  useOverlay: vi.fn<(params: OverlayParams) => UseAccountingOverlayReturn>(),
}));

const mockSyncCompleted = ref<number>(0);
const mockOverlay = createMock<UseAccountingOverlayReturn>({ refresh });
const mockSeries = createMock<UseAccountingOverlaySeriesReturn>({ reset });
const mockCostBasis = createMock<UseCostBasisOverlayReturn>({ refresh: refreshCostBasis, refreshProcessing });

vi.mock('@/modules/core/common/feature-flags', async importOriginal => ({
  ...await importOriginal<Record<string, unknown>>(),
  isAccountingUpdateEnabled: accountingUpdateEnabled,
}));
vi.mock('@/modules/history/balances/use-accounting-overlay', async importOriginal => ({
  ...await importOriginal<Record<string, unknown>>(),
  useAccountingOverlay: useOverlay,
}));
vi.mock('@/modules/history/balances/use-accounting-overlay-series', () => ({
  useAccountingOverlaySeries: (): UseAccountingOverlaySeriesReturn => mockSeries,
}));
vi.mock('@/modules/history/balances/use-accounting-overlay-context', () => ({
  provideAccountingOverlay: provideOverlay,
}));
vi.mock('@/modules/history/cost-basis/use-cost-basis-overlay', () => ({
  useCostBasisOverlay: useCostBasis,
}));
vi.mock('@/modules/history/cost-basis/use-cost-basis-overlay-context', () => ({
  provideCostBasisOverlay: provideCostBasis,
}));
vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): { syncCompleted: Ref<number> } => ({ syncCompleted: mockSyncCompleted }),
}));

function event(identifier: number, locationLabel: string | null): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ identifier, locationLabel });
}

let scope: EffectScope;

function setup(mode: Ref<OverlayMode>, rows: HistoryEventRow[] = []): { available: boolean; params: OverlayParams } {
  const groups = createMock<Collection<HistoryEventRow>>({ data: rows });
  const result = scope.run(() => useHistoryEventsOverlay(mode, (): Collection<HistoryEventRow> => groups));
  assert(result);
  const call = useOverlay.mock.calls.at(-1);
  assert(call);
  return { available: result.available, params: call[0] };
}

describe('useHistoryEventsOverlay', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    set(mockSyncCompleted, 0);
    accountingUpdateEnabled.mockReset().mockReturnValue(true);
    refresh.mockReset().mockResolvedValue(undefined);
    reset.mockReset();
    provideOverlay.mockReset();
    useOverlay.mockReset().mockReturnValue(mockOverlay);
    refreshCostBasis.mockReset().mockResolvedValue(undefined);
    refreshProcessing.mockReset().mockResolvedValue(undefined);
    provideCostBasis.mockReset();
    useCostBasis.mockReset().mockReturnValue(mockCostBasis);
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should request only events that carry an account, including grouped rows', () => {
    const { params } = setup(ref<OverlayMode>(OverlayMode.BALANCE), [
      event(1, '0xA'),
      [event(2, null), event(3, '0xB')],
      event(4, null),
    ]);

    expect(toValue(params.eventIdentifiers)).toEqual([1, 3]);
  });

  it('should enable the overlay only in balance mode on a build that serves it', () => {
    const mode = ref<OverlayMode>(OverlayMode.NONE);
    const { available, params } = setup(mode);
    expect(available).toBe(true);
    expect(toValue(params.enabled)).toBe(false);
    set(mode, OverlayMode.BALANCE);
    expect(toValue(params.enabled)).toBe(true);

    accountingUpdateEnabled.mockReturnValue(false);
    const unavailable = setup(ref<OverlayMode>(OverlayMode.BALANCE));
    expect(unavailable.available).toBe(false);
    expect(toValue(unavailable.params.enabled)).toBe(false);
  });

  it('should provide the overlay and the shared breakdown series to the rows', () => {
    setup(ref<OverlayMode>(OverlayMode.BALANCE));
    const call = provideOverlay.mock.calls.at(-1);
    assert(call);
    expect(call[0].overlay).toBe(mockOverlay);
    expect(call[0].series).toBe(mockSeries);
  });

  it('should refresh visible balances and invalidate series after a processing completion message', async () => {
    const mode = ref<OverlayMode>(OverlayMode.BALANCE);
    setup(mode);
    const message = WebsocketMessage.parse({ type: 'historical_balance_processing_completed', data: {} });
    const handler = createHistoricalBalanceProcessingCompletedHandler();

    await handler.handle(message.data);
    await flushPromises();
    expect(reset).toHaveBeenCalledOnce();
    expect(refresh).toHaveBeenCalledOnce();

    set(mode, OverlayMode.NONE);
    await handler.handle(message.data);
    await flushPromises();
    expect(reset).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it('should refresh once after processing completes following a sync', async () => {
    setup(ref<OverlayMode>(OverlayMode.BALANCE));

    set(mockSyncCompleted, 1);
    await flushPromises();
    expect(reset).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();

    const message = WebsocketMessage.parse({ type: 'historical_balance_processing_completed', data: {} });
    await createHistoricalBalanceProcessingCompletedHandler().handle(message.data);
    await flushPromises();
    expect(reset).toHaveBeenCalledOnce();
    expect(refresh).toHaveBeenCalledOnce();
  });

  describe('the cost basis overlay', () => {
    function costBasisParams(): OverlayParams {
      const call = useCostBasis.mock.calls.at(-1);
      assert(call);
      return call[0];
    }

    it('should request every event of the page, with or without an account', () => {
      setup(ref<OverlayMode>(OverlayMode.COST_BASIS), [
        event(1, '0xA'),
        [event(2, null), event(3, '0xB')],
      ]);
      expect(toValue(costBasisParams().eventIdentifiers)).toEqual([1, 2, 3]);
    });

    it('should be on only in cost basis mode, leaving the balance overlay off', () => {
      const mode = ref<OverlayMode>(OverlayMode.BALANCE);
      const { params } = setup(mode);
      expect(toValue(costBasisParams().enabled)).toBe(false);

      set(mode, OverlayMode.COST_BASIS);
      expect(toValue(costBasisParams().enabled)).toBe(true);
      expect(toValue(params.enabled)).toBe(false);

      accountingUpdateEnabled.mockReturnValue(false);
      setup(ref<OverlayMode>(OverlayMode.COST_BASIS));
      expect(toValue(costBasisParams().enabled)).toBe(false);
    });

    it('should provide itself to the rows', () => {
      setup(ref<OverlayMode>(OverlayMode.COST_BASIS));
      const call = provideCostBasis.mock.calls.at(-1);
      assert(call);
      expect(call[0].overlay).toBe(mockCostBasis);
      expect(get(call[0].enabled)).toBe(true);
    });

    it('should refresh after a processing completion message only while it is the visible overlay', async () => {
      const mode = ref<OverlayMode>(OverlayMode.COST_BASIS);
      setup(mode);
      const message = WebsocketMessage.parse({ type: 'historical_balance_processing_completed', data: {} });
      const handler = createHistoricalBalanceProcessingCompletedHandler();

      await handler.handle(message.data);
      await flushPromises();
      expect(refreshCostBasis).toHaveBeenCalledOnce();
      expect(refresh).not.toHaveBeenCalled();

      set(mode, OverlayMode.BALANCE);
      await handler.handle(message.data);
      await flushPromises();
      expect(refreshCostBasis).toHaveBeenCalledOnce();
    });

    it('should fetch its processing events again as processing progresses, at most every five seconds, only while visible', async () => {
      vi.useFakeTimers();
      const mode = ref<OverlayMode>(OverlayMode.COST_BASIS);
      setup(mode);
      const { notifyHistoricalBalanceProcessingProgressed } = useHistoricalBalanceProcessingStore();
      const progress = (): void => notifyHistoricalBalanceProcessingProgressed(HistoricalBalanceProcessingPhase.COST_BASIS);

      progress();
      await vi.advanceTimersByTimeAsync(0);
      progress();
      await vi.advanceTimersByTimeAsync(0);
      progress();
      await vi.advanceTimersByTimeAsync(0);
      expect(refreshProcessing).toHaveBeenCalledOnce();
      await vi.advanceTimersByTimeAsync(5000);
      expect(refreshProcessing).toHaveBeenCalledTimes(2);

      set(mode, OverlayMode.BALANCE);
      await vi.advanceTimersByTimeAsync(5000);
      progress();
      await vi.advanceTimersByTimeAsync(5000);
      expect(refreshProcessing).toHaveBeenCalledTimes(2);
    });
  });
});
