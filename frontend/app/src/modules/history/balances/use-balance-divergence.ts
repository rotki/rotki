import type { ComputedRef, Ref } from 'vue';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { err, none, ok, type OptionType as Option, type ResultType as Result, some } from 'plainfp';
import { fromNullable, isSome, map as mapOption } from 'plainfp/option';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import {
  type HistoricalBalanceDivergenceEvent,
  type HistoricalBalanceDivergencePayload,
  HistoricalBalanceDivergenceResponse,
} from '@/modules/history/balances/types';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';

export interface DivergenceBoundaryEvent {
  key: 'last_matching' | 'first_diverged';
  color: 'success' | 'warning';
  event: HistoricalBalanceDivergenceEvent;
}

interface DivergenceError {
  message: string;
}

interface UseBalanceDivergenceReturn {
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string | undefined>>;
  boundaries: ComputedRef<DivergenceBoundaryEvent[]>;
  summary: ComputedRef<string | undefined>;
  find: (payload: HistoricalBalanceDivergencePayload) => Promise<void>;
  navigate: (event: HistoricalBalanceDivergenceEvent, asset: string) => void;
  clear: () => void;
}

/**
 * Runs the balance divergence query as a task and exposes its state plus the derived boundary
 * events used to render (and navigate to) the last matching and first diverged history events.
 */
export function useBalanceDivergence(): UseBalanceDivergenceReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { findHistoricalBalanceDivergence } = useHistoricalBalancesApi();
  const { runTask } = useTaskHandler();
  const { requestNavigation, setHighlightTarget } = useHistoryEventNavigation();

  const loading = shallowRef<boolean>(false);
  const result = ref<HistoricalBalanceDivergenceResponse>();
  const error = ref<string>();

  const boundaries = computed<DivergenceBoundaryEvent[]>(() => {
    const current = get(result);
    if (!current)
      return [];

    const candidates = [
      mapOption(fromNullable(current.lastMatching), (event): DivergenceBoundaryEvent => ({
        color: 'success',
        event,
        key: 'last_matching',
      })),
      mapOption(fromNullable(current.firstDiverged), (event): DivergenceBoundaryEvent => ({
        color: 'warning',
        event,
        key: 'first_diverged',
      })),
    ];
    return candidates.filter(isSome).map(candidate => candidate.value);
  });

  const summary = computed<string | undefined>(() => {
    const current = get(result);
    if (!current)
      return undefined;

    if (current.status === 'no_divergence')
      return t('balance_divergence.no_divergence', { probes: current.probes.length });

    return t('balance_divergence.checked', { probes: current.probes.length });
  });

  function clear(): void {
    set(result, undefined);
    set(error, undefined);
  }

  function navigate(event: HistoricalBalanceDivergenceEvent, asset: string): void {
    if (!event.groupIdentifier || !asset)
      return;

    setHighlightTarget(HighlightTargetTypes.ACCOUNTING_EVENT, {
      groupIdentifier: event.groupIdentifier,
      identifier: event.eventIdentifier,
    });
    requestNavigation({
      assetFilter: asset,
      highlightedAccountingEvent: event.eventIdentifier,
      targetGroupIdentifier: event.groupIdentifier,
    });
  }

  /**
   * Folds the divergence task into a Result: `ok(some)` on a parsed response, `ok(none)` when the
   * task was cancelled or skipped (leave the panel untouched), and `err` for actionable failures
   * or a thrown/unparseable response.
   */
  async function run(
    payload: HistoricalBalanceDivergencePayload,
  ): Promise<Result<Option<HistoricalBalanceDivergenceResponse>, DivergenceError>> {
    try {
      const outcome = await runTask<HistoricalBalanceDivergenceResponse, TaskMeta>(
        async () => findHistoricalBalanceDivergence(payload),
        {
          guard: false,
          meta: { title: t('balance_divergence.task.title', { asset: payload.asset }) },
          type: TaskType.QUERY_HISTORICAL_BALANCE_DIVERGENCE,
          unique: false,
        },
      );

      if (outcome.success)
        return ok(some(HistoricalBalanceDivergenceResponse.parse(outcome.result)));

      if (isActionableFailure(outcome))
        return err({ message: outcome.message });

      return ok(none);
    }
    catch (error_: unknown) {
      return err({ message: getErrorMessage(error_) });
    }
  }

  async function find(payload: HistoricalBalanceDivergencePayload): Promise<void> {
    set(loading, true);
    clear();

    const outcome = await run(payload);
    set(loading, false);

    if (!outcome.ok) {
      set(error, outcome.error.message);
      return;
    }

    const found = outcome.value;
    if (found.some)
      set(result, found.value);
  }

  return {
    boundaries,
    clear,
    error: readonly(error),
    find,
    loading: readonly(loading),
    navigate,
    summary,
  };
}
