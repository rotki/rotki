import { type MessageKey, msg } from '@/message-key';
import { type ActivityStatus, ActivityStatus as Status } from './core/types';

/** RUI chip colours, narrowed to the four an outcome can take. */
export type OutcomeColor = 'error' | 'warning' | 'success' | 'grey';

export interface ActivityOutcome {
  readonly color: OutcomeColor;
  readonly key: MessageKey;
}

/**
 * How a non-running status reads on a row.
 *
 * Only RUNNING has no entry: a running row shows progress, which says more than a chip could.
 * Everything else is a state the reader has to be told about — including the two the progress
 * rollup deliberately counts as done (`projection.ts` `percentageOf`), which is exactly why they
 * need saying. A subtree at 100% with two failed chains is otherwise indistinguishable from a
 * clean one.
 *
 * Kept out of the component so the mapping can be asserted without mounting anything, and out of
 * `core/` because it names i18n keys — `msg.$t` is what makes the key-usage lint count them.
 */
const OUTCOME: Partial<Record<ActivityStatus, ActivityOutcome>> = {
  [Status.CANCELLED]: { color: 'grey', key: msg.$t('pending_task.status.cancelled') },
  [Status.COMPLETE]: { color: 'success', key: msg.$t('pending_task.status.done') },
  [Status.FAILED]: { color: 'error', key: msg.$t('pending_task.status.failed') },
  [Status.PENDING]: { color: 'grey', key: msg.$t('pending_task.status.queued') },
  [Status.SKIPPED]: { color: 'warning', key: msg.$t('pending_task.status.skipped') },
};

export function activityOutcome(status: ActivityStatus): ActivityOutcome | undefined {
  return OUTCOME[status];
}
