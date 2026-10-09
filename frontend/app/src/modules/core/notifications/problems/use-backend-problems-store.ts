import { type BackendProblem, foldReport, type ProblemReport } from '@/modules/core/notifications/problems/backend-problem-tree';

/**
 * The backend problems the drawer files: family and location, then the distinct problems under
 * them.
 *
 * @remarks
 * Kept apart from the notifications because a backend problem never pops and is never a single
 * occurrence: it is a tree that repeats fold into, so it has no use for the dispatcher, its
 * cooldowns or its display queue.
 */
export const useBackendProblemsStore = defineStore('notifications/backend-problems', () => {
  const problems = shallowRef<BackendProblem[]>([]);

  const hasUnread = computed<boolean>(() => get(problems).some(problem => !problem.read));

  function record(report: ProblemReport): void {
    set(problems, foldReport(get(problems), report));
  }

  function remove(id: string): void {
    set(problems, get(problems).filter(problem => problem.id !== id));
  }

  function markAllRead(): void {
    if (!get(hasUnread))
      return;

    set(problems, get(problems).map(problem => problem.read ? problem : { ...problem, read: true }));
  }

  return {
    hasUnread,
    markAllRead,
    problems,
    record,
    remove,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBackendProblemsStore, import.meta.hot));
