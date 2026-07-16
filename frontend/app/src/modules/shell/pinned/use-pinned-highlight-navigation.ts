import { startPromise } from '@shared/utils';
import { useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';

export interface UsePinnedHighlightNavigationReturn {
  /** Reset local highlight state, clear shared targets, and strip the highlight query keys. */
  clearHighlight: () => Promise<void>;
}

/**
 * Shared teardown for pinned history panels that drive route-query highlights
 * (asset-movement matching, internal-tx conflicts). Each panel used to duplicate
 * the same three pieces: a `clearHighlight` that resets local state + clears the
 * shared highlight targets + removes its query keys from the URL, a watcher that
 * resets local state once the targets are emptied elsewhere, and an on-unmount
 * cleanup. This centralizes them; `queryKeys` are the URL keys the panel owns and
 * `reset` clears the panel's local highlight refs. `isStillPinned` lets the panel
 * distinguish a `<KeepAlive>` tab-switch (still pinned, keep the highlight so it
 * survives the round-trip) from an actual close (unpinned, clear it).
 */
export function usePinnedHighlightNavigation(
  queryKeys: string[],
  reset: () => void,
  isStillPinned?: () => boolean,
): UsePinnedHighlightNavigationReturn {
  const router = useRouter();
  const route = useRoute();
  const { clearAllHighlightTargets, highlightTargets } = useHistoryEventNavigation();

  async function clearHighlight(): Promise<void> {
    reset();
    clearAllHighlightTargets();
    const query = { ...get(route).query };
    const hadHighlight = queryKeys.some(key => Boolean(query[key]));
    for (const key of queryKeys)
      delete query[key];
    if (hadHighlight)
      await router.replace({ query });
  }

  watch(highlightTargets, (targets) => {
    if (Object.keys(targets).length === 0)
      reset();
  });

  // Clear the highlight when the panel is unpinned, not on <KeepAlive> deactivation.
  // A backgrounded panel keeps its effects live, so this watch still fires when its
  // tab is closed while another tab is in front (onDeactivated would not fire then);
  // a tab-switch leaves the panel pinned, so the highlight survives the round-trip.
  if (isStillPinned) {
    watch(isStillPinned, (pinnedNow, wasPinned) => {
      if (wasPinned && !pinnedNow)
        startPromise(clearHighlight());
    });
  }

  onUnmounted(() => {
    startPromise(clearHighlight());
  });

  return { clearHighlight };
}
