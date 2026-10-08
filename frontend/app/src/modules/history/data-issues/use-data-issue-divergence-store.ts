import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';

/**
 * Divergence searches started from a data issue, keyed by {@link dataIssueDivergenceKey}.
 *
 * @remarks
 * The search outlives the drawer that started it, so its result, error and running state live here
 * instead of in the component: reopening the issue, or showing it in the pinned rail, picks up
 * the same search rather than starting over.
 */
export const useDataIssueDivergenceStore = defineStore('history/data-issue-divergence', () => {
  const results = shallowRef<Map<string, HistoricalBalanceDivergenceResponse>>(new Map());
  const errors = shallowRef<Map<string, string>>(new Map());
  const running = shallowRef<Set<string>>(new Set());

  function setResult(key: string, result: HistoricalBalanceDivergenceResponse | undefined): void {
    const next = new Map(get(results));
    if (result)
      next.set(key, result);
    else
      next.delete(key);
    set(results, next);
  }

  function setRunning(key: string, value: boolean): void {
    const next = new Set(get(running));
    if (value)
      next.add(key);
    else
      next.delete(key);
    set(running, next);
  }

  function setError(key: string, error: string | undefined): void {
    const next = new Map(get(errors));
    if (error)
      next.set(key, error);
    else
      next.delete(key);
    set(errors, next);
  }

  return { errors, results, running, setError, setResult, setRunning };
});

/** A search is bounded by the issue's end time, so a moved end time is a different search. */
export function dataIssueDivergenceKey(issue: Pick<DataIssue, 'id' | 'tsEnd'>): string {
  return `${issue.id}:${issue.tsEnd}`;
}
