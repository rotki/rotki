import type { EffectScope, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { AccountingOverlayContext } from '@/modules/history/balances/use-accounting-overlay-context';
import type { UseAccountingOverlaySeriesReturn } from '@/modules/history/balances/use-accounting-overlay-series';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { OverlayMode, type UseAccountingOverlayReturn } from '@/modules/history/balances/use-accounting-overlay';
import { useHistoryEventsOverlay } from './use-history-events-overlay';

interface OverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  eventIdentifiers: MaybeRefOrGetter<number[]>;
}

const { accountingUpdateEnabled, provideOverlay, refresh, reset, useOverlay } = vi.hoisted(() => ({
  accountingUpdateEnabled: vi.fn<() => boolean>(),
  provideOverlay: vi.fn<(context: AccountingOverlayContext) => void>(),
  refresh: vi.fn<() => Promise<void>>(),
  reset: vi.fn<() => void>(),
  useOverlay: vi.fn<(params: OverlayParams) => UseAccountingOverlayReturn>(),
}));

const mockSyncCompleted = ref<number>(0);
const mockOverlay = createMock<UseAccountingOverlayReturn>({ refresh });
const mockSeries = createMock<UseAccountingOverlaySeriesReturn>({ reset });

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
    scope = effectScope();
    set(mockSyncCompleted, 0);
    accountingUpdateEnabled.mockReset().mockReturnValue(true);
    refresh.mockReset().mockResolvedValue(undefined);
    reset.mockReset();
    provideOverlay.mockReset();
    useOverlay.mockReset().mockReturnValue(mockOverlay);
  });

  afterEach(() => scope.stop());

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

  it('should drop the series on every completed sync but refresh only a visible overlay', async () => {
    const mode = ref<OverlayMode>(OverlayMode.NONE);
    setup(mode);

    set(mockSyncCompleted, 1);
    await flushPromises();
    expect(reset).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();

    set(mode, OverlayMode.BALANCE);
    set(mockSyncCompleted, 2);
    await flushPromises();
    expect(reset).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenCalledOnce();
  });
});
