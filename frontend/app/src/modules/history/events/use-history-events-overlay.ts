import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { OverlayMode, type OverlayPair, useAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay';
import { provideAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

interface UseHistoryEventsOverlayReturn {
  /** Whether the build serves the overlay at all, i.e. whether to render its toggles. */
  available: boolean;
  enabled: ComputedRef<boolean>;
}

/**
 * The accounting overlay: the known balance after each event.
 *
 * Keys off each event's own (account, asset) pair, so it needs no filter. Gated by
 * VITE_ACCOUNTING_UPDATE (from the backend's ROTKI_ACCOUNTING_UPDATE, see vite.config.ts), so it
 * only appears where the backend serves it.
 *
 * `mode` rides the router query via `useHistoryEventsFilters`' `queryParamsOnly` rather than being
 * clobbered by pagination, and is NOT persisted across sessions: fresh navigation resets it to
 * 'none', back restores it from the history entry. Only the main page syncs.
 */
export function useHistoryEventsOverlay(
  mode: MaybeRefOrGetter<OverlayMode>,
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>,
): UseHistoryEventsOverlayReturn {
  const available = isAccountingUpdateEnabled();

  // The build flag is required too, so the 'balance' choice cannot enable it where the backend
  // would reject every call.
  const enabled = computed<boolean>(() => available && toValue(mode) === OverlayMode.BALANCE);

  const pairs = computed<OverlayPair[]>(() => {
    const events = toValue(groups).data.flatMap(row => Array.isArray(row) ? row : [row]);
    // Map keyed by `${account} ${asset}` dedupes for free; last write wins (identical payload).
    const byKey = new Map<string, OverlayPair>();
    for (const { asset, locationLabel } of events) {
      if (locationLabel)
        byKey.set(`${locationLabel} ${asset}`, { asset, locationLabel });
    }
    return [...byKey.values()];
  });

  const overlay = useAccountingOverlay({ enabled, pairs });

  provideAccountingOverlay({ enabled, overlay });

  // When the history sync (tx query + exchange events + decoding) completes, new events have landed
  // and their historical balances may have shifted, so the whole overlay is refreshed to re-resolve
  // every visible row against the updated series. Guarded so a hidden overlay stays idle.
  const { syncCompleted } = useSyncCompleted();
  watch(syncCompleted, async () => {
    if (get(enabled))
      await overlay.refresh();
  });

  return { available, enabled };
}
