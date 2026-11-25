import type { ProgressUpdateResultData, StakingEventsQueryData } from '@/modules/core/messaging/types/status-types';
import { SocketMessageProgressUpdateSubType } from '@/modules/core/messaging/types/base';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { onlineEventsActivity } from '@/modules/history/events/tx/sync.activity';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { ActivityPart } from '@/modules/task-center/core/types';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

type StakingQueryProgressData = Extract<ProgressUpdateResultData, {
  subtype: typeof SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY | typeof SocketMessageProgressUpdateSubType.STAKING_EVENTS_QUERY;
}>;

interface UseStakingQueryProgressReturn {
  isStakingQueryProgress: (data: ProgressUpdateResultData) => data is StakingQueryProgressData;
  reportStakingQueryProgress: (data: StakingQueryProgressData) => void;
}

const ONLINE_QUERY_TYPES: ReadonlySet<string> = new Set<string>(Object.values(OnlineHistoryEventsQueryType));

function isOnlineQueryType(value: string): value is OnlineHistoryEventsQueryType {
  return ONLINE_QUERY_TYPES.has(value);
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
   * check: it is only cleaned up for an activity the orchestrator has a record for.
   */
  function reportStakingEventsProgress(data: StakingEventsQueryData): void {
    if (!isOnlineQueryType(data.queryType))
      return;

    const subject = { queryType: data.queryType };
    if (!statusOf(onlineEventsActivity.kind, ...onlineEventsActivity.partsOf(subject)).running)
      return;

    reportProgress(onlineEventsActivity.id(subject), { current: data.processed, total: data.total });
    publishActivityDetail(onlineEventsActivity, subject, { waitingSeconds: data.waitingSeconds ?? undefined });
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
