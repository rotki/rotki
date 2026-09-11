import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { OverlayMode, useAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay';
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
 * Fetches bucket snapshots by event identifier. Gated by
 * VITE_ACCOUNTING_UPDATE (from the backend's ROTKI_ACCOUNTING_UPDATE, see vite.config.ts), so it
 * only appears where the backend serves it.
 *
 * `mode` rides the router query via `useHistoryEventsFilters`' `queryParamsOnly` rather than being
 * clobbered by pagination, and is NOT persisted across sessions: fresh navigation resets it to
 * 'none', back restores it from the history entry. Only the main page syncs.
 *
 * A completed history sync lands new events whose historical balances may have shifted, so the
 * whole overlay is refreshed then; a hidden overlay stays idle.
 */
export function useHistoryEventsOverlay(
  mode: MaybeRefOrGetter<OverlayMode>,
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>,
): UseHistoryEventsOverlayReturn {
  const available = isAccountingUpdateEnabled();

  const enabled = computed<boolean>(() => available && toValue(mode) === OverlayMode.BALANCE);

  const eventIdentifiers = computed<number[]>(() => {
    const events = toValue(groups).data.flatMap(row => Array.isArray(row) ? row : [row]);
    return events.map(event => event.identifier);
  });

  const overlay = useAccountingOverlay({ enabled, eventIdentifiers });

  provideAccountingOverlay({ enabled, overlay });

  const { syncCompleted } = useSyncCompleted();
  watch(syncCompleted, async () => {
    if (get(enabled))
      await overlay.refresh();
  });

  return { available, enabled };
}
