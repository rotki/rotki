import type {
  RepullingEthStakingPayload,
  RepullingExchangeEventsPayload,
  RepullingTransactionPayload,
} from '@/modules/history/events/event-payloads';
import { setDigest } from '@/modules/core/common/data/digest';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/**
 * Re-pulling transactions, keyed by every field of the request.
 *
 * @remarks
 * An absent bound is still part of the identity, as `0`: "everything before X" is a different
 * request from "X to Y". An absent address or chain is an empty part for the same reason.
 */
export const repullTransactionsActivity = defineActivity<RepullingTransactionPayload, readonly [string, string, number, number]>({
  key: subject => [subject.address ?? '', subject.chain ?? '', subject.fromTimestamp ?? 0, subject.toTimestamp ?? 0],
  kind: ActivityKind.REPULLING,
  part: ActivityPart.TRANSACTIONS,
});

/** Re-pulling one exchange's events over a range, keyed the same way. */
export const repullExchangeEventsActivity = defineActivity<RepullingExchangeEventsPayload, readonly [string, string, number, number]>({
  key: subject => [subject.location, subject.name, subject.fromTimestamp ?? 0, subject.toTimestamp ?? 0],
  kind: ActivityKind.REPULLING,
  part: ActivityPart.EXCHANGE,
});

/**
 * Re-pulling one kind of ETH staking events over a range, for a set of validators and addresses.
 *
 * @remarks
 * The validator and address filters are part of the identity, as digests of each set, so two
 * re-pulls of one kind and range for different validators never share one promise.
 */
export const repullEthStakingActivity = defineActivity<RepullingEthStakingPayload, readonly [string, number, number, string, string]>({
  key: subject => [
    subject.entryType,
    subject.fromTimestamp ?? 0,
    subject.toTimestamp ?? 0,
    setDigest((subject.validatorIndices ?? []).map(String)),
    setDigest(subject.addresses ?? []),
  ],
  kind: ActivityKind.REPULLING,
  part: ActivityPart.STAKE,
});

/**
 * The dock row for a bulk internal-transaction conflict resolution, which carries its progress and
 * parents each conflict's decode.
 *
 * @remarks
 * A re-pull, since that is what resolving does. The `run` part keeps it apart from the other
 * re-pull ids, and one id is enough because the panel runs a single bulk resolution at a time. On
 * the umbrella lane, so waiting for its children never holds one of their slots.
 */
export const conflictResolutionActivity = defineActivity<void, readonly [string]>({
  key: () => ['internal-tx-conflicts'],
  kind: ActivityKind.REPULLING,
  lane: () => UMBRELLA_LANE,
  part: ActivityPart.RUN,
});
