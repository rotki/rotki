import type { ProgressUpdateResultData, StakingEventsQueryData } from '@/modules/core/messaging/types/status-types';
import { SocketMessageProgressUpdateSubType } from '@/modules/core/messaging/types/base';
import { onlineEventsActivity } from '@/modules/history/events/tx/sync.activity';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { ActivityPart } from '@/modules/task-center/core/types';
import { peekActivityDetail, publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

type StakingQueryProgressData = Extract<ProgressUpdateResultData, {
  subtype: typeof SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY | typeof SocketMessageProgressUpdateSubType.STAKING_EVENTS_QUERY;
}>;

interface UseStakingQueryProgressReturn {
  isStakingQueryProgress: (data: ProgressUpdateResultData) => data is StakingQueryProgressData;
  reportStakingQueryProgress: (data: StakingQueryProgressData) => void;
}

/** Reports the progress frames of staking queries onto the activities that run them. */
export function useStakingQueryProgress(): UseStakingQueryProgressReturn {
  const { reportProgress, statusOf } = useTaskOrchestrator();

  function isStakingQueryProgress(data: ProgressUpdateResultData): data is StakingQueryProgressData {
    return data.subtype === SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY
      || data.subtype === SocketMessageProgressUpdateSubType.STAKING_EVENTS_QUERY;
  }

  /**
   * Report a staking events query onto its online events activity, with the rate limit it waits
   * out, if any.
   *
   * @remarks
   * The backend's periodic withdrawal and block production queries send the same frames with no
   * activity behind them here, so only a running activity is reported on. The detail needs that
   * check: it is only cleaned up for an activity the orchestrator has a record for. It is published
   * only when the wait changes, since every publish re-runs every dock row's detail, and a zero
   * second wait is no wait.
   *
   * The frames carry nothing that tells the two producers apart, so a periodic query that holds
   * the backend's query lock while the user's activity waits for it reports onto that activity:
   * its bar fills, then restarts once the user's own query begins.
   */
  function reportStakingEventsProgress(data: StakingEventsQueryData): void {
    const subject = { queryType: data.queryType };
    if (!statusOf(onlineEventsActivity.kind, ...onlineEventsActivity.partsOf(subject)).running)
      return;

    reportProgress(onlineEventsActivity.id(subject), { current: data.processed, total: data.total });
    const waitingSeconds = data.waitingSeconds !== null && data.waitingSeconds > 0 ? data.waitingSeconds : undefined;
    if (peekActivityDetail(onlineEventsActivity, subject)?.waitingSeconds !== waitingSeconds)
      publishActivityDetail(onlineEventsActivity, subject, { waitingSeconds });
  }

  function reportStakingQueryProgress(data: StakingQueryProgressData): void {
    if (data.subtype === SocketMessageProgressUpdateSubType.STAKING_EVENTS_QUERY)
      reportStakingEventsProgress(data);
    else
      reportProgress(liquityActivity.id({ part: ActivityPart.STAKE }), { current: data.processed, total: data.total });
  }

  return {
    isStakingQueryProgress,
    reportStakingQueryProgress,
  };
}
