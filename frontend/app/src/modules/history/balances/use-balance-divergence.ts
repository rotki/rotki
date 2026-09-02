import type { ComputedRef, Ref } from 'vue';
import { err, none, ok, type OptionType as Option, type ResultType as Result, some } from 'plainfp';
import { fromNullable, isSome, map as mapOption } from 'plainfp/option';
import { isErr, map as mapResult } from 'plainfp/result';
import { msg } from '@/message-key';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import {
  type HistoricalBalanceDivergenceEvent,
  type HistoricalBalanceDivergencePayload,
  HistoricalBalanceDivergenceResponse,
} from '@/modules/history/balances/types';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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

/** Runs the balance divergence query as a task, exposing its state and the boundary events. */
export function useBalanceDivergence(): UseBalanceDivergenceReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { findHistoricalBalanceDivergence } = useHistoricalBalancesApi();
  const { submitTask } = useNativeTask();
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
    const outcome = await submitTask<HistoricalBalanceDivergenceResponse>({
      id: makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.DIVERGENCE, payload.asset, payload.address, payload.evmChain, payload.tolerance ?? 0),
      kind: ActivityKind.HISTORICAL_BALANCES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<HistoricalBalanceDivergenceResponse, TaskError>> => mapResult(
        await runTask<HistoricalBalanceDivergenceResponse>(
          async () => findHistoricalBalanceDivergence(payload),
        ),
        value => value,
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.divergence'), { asset: payload.asset }),
      title: t('task_center.group.historical_balances'),
    });

    if (!isErr(outcome)) {
      try {
        return ok(some(HistoricalBalanceDivergenceResponse.parse(outcome.value)));
      }
      catch (error_: unknown) {
        return err({ message: getErrorMessage(error_) });
      }
    }

    if (isActionable(outcome.error))
      return err({ message: outcome.error.message });

    return ok(none);
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
