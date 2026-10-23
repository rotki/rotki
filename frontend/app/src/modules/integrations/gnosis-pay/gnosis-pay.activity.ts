import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** Fetching the nonce the sign-in message is built around. */
export const gnosisPayNonceActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.GNOSIS_PAY,
  part: ActivityPart.NONCE,
});

/** Verifying the signed sign-in message. */
export const gnosisPayVerifyActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.GNOSIS_PAY,
  part: ActivityPart.VERIFY,
});
