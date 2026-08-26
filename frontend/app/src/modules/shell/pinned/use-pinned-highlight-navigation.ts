import { startPromise } from '@shared/utils';
import { useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';

export interface UsePinnedHighlightNavigationReturn {
  /** Reset local highlight state, clear shared targets, and strip the highlight query keys. */
  clearHighlight: () => Promise<void>;
}

/**
 * Wires the shared teardown for a pinned panel that drives route-query highlights.
 *
 * @remarks
 * Covers all three pieces a panel needs: `clearHighlight`, a watcher that resets local state once
 * the shared targets are emptied elsewhere, and an unmount cleanup.
 *
 * @param queryKeys - the URL keys this panel owns
 * @param reset - clears the panel's own highlight refs
 * @param isStillPinned - distinguishes a `<KeepAlive>` tab switch, where the highlight has to
 * survive the round-trip, from an actual close
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
