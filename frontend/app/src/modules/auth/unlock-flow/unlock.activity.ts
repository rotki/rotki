import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { SESSION_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** Logging in to an existing account. On the session lane, so it never overlaps a creation. */
export const sessionLoginActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.SESSION,
  lane: () => SESSION_LANE,
  part: ActivityPart.LOGIN,
});

/** Creating an account. Same lane as {@link sessionLoginActivity}. */
export const sessionCreateActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.SESSION,
  lane: () => SESSION_LANE,
  part: ActivityPart.CREATE,
});
