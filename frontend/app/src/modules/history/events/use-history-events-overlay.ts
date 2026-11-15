import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { OverlayMode, useAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay';
import { provideAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';
import { useAccountingOverlaySeries } from '@/modules/history/balances/use-accounting-overlay-series';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import { provideCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay-context';

interface UseHistoryEventsOverlayReturn {
  /** Whether the build serves the overlay at all, i.e. whether to render its toggles. */
  available: boolean;
  enabled: ComputedRef<boolean>;
}

/**
 * The accounting overlays: the known balance after each event, or what each event cost or realized.
 *
 * Fetches by event identifier: bucket snapshots for events that carry an account, and the cost
 * basis for every event. Gated by VITE_ACCOUNTING_UPDATE (from the backend's
 * ROTKI_ACCOUNTING_UPDATE, see vite.config.ts), so it only appears where the backend serves it.
 *
 * `mode` rides the router query via `useHistoryEventsFilters`' `queryParamsOnly` rather than being
 * clobbered by pagination, and is NOT persisted across sessions: fresh navigation resets it to
 * 'none', back restores it from the history entry. Only the main page syncs.
 *
 * Completed processing, which covers the balances and then the cost basis, invalidates the
 * breakdown series and refreshes the visible overlay. A hidden overlay stays idle until enabled.
 */
export function useHistoryEventsOverlay(
  mode: MaybeRefOrGetter<OverlayMode>,
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>,
): UseHistoryEventsOverlayReturn {
  const available = isAccountingUpdateEnabled();

  const enabled = computed<boolean>(() => available && toValue(mode) === OverlayMode.BALANCE);

  const costBasisEnabled = computed<boolean>(() => available && toValue(mode) === OverlayMode.COST_BASIS);

  const events = computed<HistoryEventEntry[]>(() => toValue(groups)
    .data
    .flatMap(row => Array.isArray(row) ? row : [row]));

  const eventIdentifiers = computed<number[]>(() => get(events)
    .filter(event => !!event.locationLabel)
    .map(event => event.identifier));

  const costBasisEventIdentifiers = computed<number[]>(() => get(events).map(event => event.identifier));

  const overlay = useAccountingOverlay({ enabled, eventIdentifiers });
  const series = useAccountingOverlaySeries();

  provideAccountingOverlay({ enabled, overlay, series });

  const costBasis = useCostBasisOverlay({ enabled: costBasisEnabled, eventIdentifiers: costBasisEventIdentifiers });
  provideCostBasisOverlay({ enabled: costBasisEnabled, overlay: costBasis });

  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  watch(historicalBalanceProcessingCompleted, async () => {
    series.reset();
    if (get(enabled))
      await overlay.refresh();
    if (get(costBasisEnabled))
      await costBasis.refresh();
  });

  return { available, enabled };
}
