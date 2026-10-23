import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind } from '@/modules/task-center/core/types';

/** Querying the airdrops of every tracked account, as one request. */
export const airdropsActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.AIRDROPS,
});
