import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';

/** The count each row had when the user last closed the center, by row id. */
type SeenCounts = Record<string, number>;

interface UseActionCenterSeenOptions {
  /** every row the center knows about, raised or not */
  items: MaybeRefOrGetter<ActionItem[]>;
  /** the rows asking for something, which are the only ones that can be new */
  active: MaybeRefOrGetter<ActionItem[]>;
  /** while true the counts are not trustworthy, so no watermark is lowered */
  checking: MaybeRefOrGetter<boolean>;
}

interface UseActionCenterSeenReturn {
  /** ids of the active rows that appeared, or whose count grew, since the user last looked */
  newIds: ComputedRef<string[]>;
  markSeen: () => void;
}

/**
 * Which rows are new to the user: not there, or smaller, the last time they closed the center.
 *
 * @remarks
 * Kept per user in local storage. Closing the center only raises the watermarks, so a close before
 * the first scan (every count still zero) forgets nothing. A count that drops, because the user
 * resolved part of it elsewhere, lowers its watermark once the counts can be trusted, so the rows
 * that come back later count as new again.
 */
export function useActionCenterSeen(options: UseActionCenterSeenOptions): UseActionCenterSeenReturn {
  const { active, checking, items } = options;
  const userId = useLoggedUserIdentifier();

  const seen: Ref<SeenCounts> = useLocalStorage<SeenCounts>(() => `${get(userId)}.rotki_action_center_seen`, {});

  const newIds = computed<string[]>(() => {
    const counts = get(seen);
    return toValue(active)
      .filter(item => item.count > (counts[item.id] ?? 0))
      .map(item => item.id);
  });

  function markSeen(): void {
    const next: SeenCounts = { ...get(seen) };
    for (const item of toValue(active))
      next[item.id] = Math.max(next[item.id] ?? 0, item.count);
    set(seen, next);
  }

  watchEffect(() => {
    if (toValue(checking))
      return;

    const counts = get(seen);
    const lowered: SeenCounts = { ...counts };
    let changed = false;
    for (const item of toValue(items)) {
      const previous = counts[item.id];
      if (item.loading || previous === undefined || item.count >= previous)
        continue;
      if (item.count === 0)
        delete lowered[item.id];
      else
        lowered[item.id] = item.count;
      changed = true;
    }
    if (changed)
      set(seen, lowered);
  });

  return { markSeen, newIds };
}
