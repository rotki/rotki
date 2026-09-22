import { isTerminalStatus } from '../status';
import { type Activity, ActivityKind, ActivityPart, activityParts, ActivityStatus, type ActivityWaiting, WaitingReason } from '../types';
import { Priority } from './spec';

/**
 * What holds a queued `candidate` back, given a snapshot of `all` activities, or `undefined` when
 * the rule lets it start.
 *
 * @remarks
 * Pure and composable: the orchestrator checks every configured rule after its generic parent and
 * dependency gates, and the first hold found is both why the candidate may not start and the
 * reason the dock shows for it. Rules express domain ordering and blocking (for example, do not
 * query balances mid-sync) without the orchestrator knowing any domain.
 */
export type EligibilityRule = (candidate: Activity, all: readonly Activity[]) => ActivityWaiting | undefined;

function holdBy(reason: WaitingReason, blocker: Activity | undefined): ActivityWaiting | undefined {
  return blocker === undefined ? undefined : { on: blocker.id, reason };
}

const BALANCE_KINDS = new Set<ActivityKind>([
  ActivityKind.BLOCKCHAIN_BALANCES,
  ActivityKind.TOKEN_DETECTION,
  ActivityKind.EXCHANGE_BALANCES,
]);

/**
 * Background balance queries wait for a history refresh to finish. The gate is the `HISTORY_SYNC`
 * umbrella rather than the decodes under it: decoding was only ever a proxy for "a sync is running",
 * and it let balances through during the `TX_SYNC`/`EXCHANGE_EVENTS` stretch that is most of a sync.
 *
 * `Priority.USER` is exempt. The umbrella stays RUNNING for the whole refresh, so without the
 * exemption a user pressing refresh would wait out the entire sync.
 */
export const pauseBalancesDuringHistorySync: EligibilityRule = (candidate, all) => {
  if (!BALANCE_KINDS.has(candidate.kind) || candidate.priority === Priority.USER)
    return undefined;

  return holdBy(
    WaitingReason.HISTORY_SYNC,
    all.find(activity => activity.kind === ActivityKind.HISTORY_SYNC && activity.status === ActivityStatus.RUNNING),
  );
};

/**
 * Work that writes links onto existing history events, keyed by the part that discriminates it
 * within {@link ActivityKind.HISTORY_EVENTS}.
 */
const MATCHING_PARTS = new Set<string>([ActivityPart.MATCH, ActivityPart.BRIDGE]);

function isMatching(activity: Activity): boolean {
  return activity.kind === ActivityKind.HISTORY_EVENTS
    && activityParts(activity.id).some(part => MATCHING_PARTS.has(part));
}

/**
 * Keeps a reset from overlapping matching.
 *
 * A re-decode deletes each location's non-customized events before re-deriving them, while matching
 * writes links onto those same rows. Every other overlap here is at worst duplicate work, so this is
 * the only pair that needs excluding.
 *
 * Asymmetric, which is what keeps it deadlock-free: matching yields to a reset that is merely
 * queued* (so a reset cannot be starved), a reset yields only to matching already *running* (so it
 * never waits on something waiting on it). Ties go to the reset.
 */
export const excludeMatchingDuringReset: EligibilityRule = (candidate, all) => {
  if (isMatching(candidate))
    return holdBy(WaitingReason.REDECODE, all.find(activity => activity.resets === true && !isTerminalStatus(activity.status)));

  if (candidate.resets === true)
    return holdBy(WaitingReason.MATCHING, all.find(activity => isMatching(activity) && activity.status === ActivityStatus.RUNNING));

  return undefined;
};

/** The rule set the reactive orchestrator is configured with by default. */
export const DEFAULT_RULES: readonly EligibilityRule[] = [pauseBalancesDuringHistorySync, excludeMatchingDuringReset];

/** The first hold any rule puts on the candidate, in rule order, or `undefined` when every rule lets it start. */
export function firstRuleHold(rules: readonly EligibilityRule[], candidate: Activity, all: readonly Activity[]): ActivityWaiting | undefined {
  for (const rule of rules) {
    const hold = rule(candidate, all);
    if (hold !== undefined)
      return hold;
  }
  return undefined;
}
