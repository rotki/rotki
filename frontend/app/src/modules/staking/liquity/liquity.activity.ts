import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, type ActivityPart } from '@/modules/task-center/core/types';

/** The four liquity queries, each its own activity. */
export type LiquityPart =
  | typeof ActivityPart.BALANCES
  | typeof ActivityPart.POOLS
  | typeof ActivityPart.STAKE
  | typeof ActivityPart.STATISTICS;

/**
 * One liquity query, keyed by which one.
 *
 * @remarks
 * The components read the same activity for their loading state that the fetch checks before it
 * runs, so there is no second copy of that state. The staking query's progress frames and the
 * statistics query's price backfill both report onto their part's id.
 */
export const liquityActivity = defineActivity<{ part: LiquityPart }, readonly [LiquityPart]>({
  key: subject => [subject.part],
  kind: ActivityKind.LIQUITY,
});
