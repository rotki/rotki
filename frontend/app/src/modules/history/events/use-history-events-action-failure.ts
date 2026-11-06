import type { Ref } from 'vue';

/** An action on the history events that failed, worded for a failure strip. */
export interface HistoryEventsActionFailure {
  title: string;
  failure: unknown;
}

interface UseHistoryEventsActionFailureReturn {
  /** The last failed action, shown above the history events table until the next one starts. */
  actionFailure: Readonly<Ref<HistoryEventsActionFailure | undefined>>;
  clearActionFailure: () => void;
  reportActionFailure: (title: string, failure: unknown) => void;
}

/**
 * Where actions started from the history events (the selection toolbar, a row, its menu, the
 * duplicate filter chip) leave a failure for the table to name.
 *
 * @remarks
 * Shared, because those actions run in composables that do not own the table. Each action clears it
 * as it starts, so a strip never outlives the next attempt.
 */
export const useHistoryEventsActionFailure = createSharedComposable((): UseHistoryEventsActionFailureReturn => {
  const actionFailure = shallowRef<HistoryEventsActionFailure>();

  function clearActionFailure(): void {
    set(actionFailure, undefined);
  }

  function reportActionFailure(title: string, failure: unknown): void {
    set(actionFailure, { failure, title });
  }

  return {
    actionFailure: shallowReadonly(actionFailure),
    clearActionFailure,
    reportActionFailure,
  };
});
