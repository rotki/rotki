import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type CountSnapshot, progressSince, snapshotCounts } from '@/modules/core/action-center/progress';

interface UseActionCenterProgressOptions {
  /** every row the center knows about, as presented */
  items: MaybeRefOrGetter<ActionItem[]>;
  /** while true the counts are not trustworthy, so neither compared nor remembered */
  checking: MaybeRefOrGetter<boolean>;
}

interface UseActionCenterProgressReturn {
  /** The count each lower or cleared row had when the user last closed the center, by row id. */
  previousCounts: ComputedRef<Record<string, number>>;
  /** Remembers the current counts, called when the center closes. */
  markClosed: () => void;
}

/**
 * What went down since the user last looked: rows that shrank and rows that cleared.
 *
 * @remarks
 * Kept per user in local storage, apart from the seen watermarks: those are lowered as soon as a count
 * drops, which is exactly the moment this needs the old count. Nothing is compared or remembered
 * before the first scan, when every count still reads zero and would look like everything cleared.
 */
export function useActionCenterProgress(options: UseActionCenterProgressOptions): UseActionCenterProgressReturn {
  const { checking, items } = options;
  const userId = useLoggedUserIdentifier();

  const snapshot: Ref<CountSnapshot> = useLocalStorage<CountSnapshot>(() => `${get(userId)}.rotki_action_center_last_counts`, {});

  const previousCounts = computed<Record<string, number>>(() =>
    toValue(checking) ? {} : progressSince(get(snapshot), toValue(items)),
  );

  function markClosed(): void {
    if (!toValue(checking))
      set(snapshot, snapshotCounts(toValue(items)));
  }

  return { markClosed, previousCounts };
}
