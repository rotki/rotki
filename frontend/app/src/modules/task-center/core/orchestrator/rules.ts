import { isTerminalStatus } from '../status';
import { type Activity, ActivityKind, ActivityPart, activityParts, ActivityStatus } from '../types';
import { Priority } from './spec';

/**
 * Decides whether a queued `candidate` may start, given a snapshot of `all` activities. Pure
 * and composable — the orchestrator ANDs every configured rule with its generic dependency
 * gate. Rules express domain ordering/blocking (e.g. don't query balances mid-decode) without
 * the orchestrator knowing any domain.
 */
export type EligibilityRule = (candidate: Activity, all: readonly Activity[]) => boolean;

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
 * ⭐ `Priority.USER` is exempt. The umbrella stays RUNNING for the whole refresh, so without the
 * exemption a user pressing refresh would wait out the entire sync.
 */
export const pauseBalancesDuringHistorySync: EligibilityRule = (candidate, all) => {
  if (!BALANCE_KINDS.has(candidate.kind) || candidate.priority === Priority.USER)
    return true;

  return !all.some(activity => activity.kind === ActivityKind.HISTORY_SYNC && activity.status === ActivityStatus.RUNNING);
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
 * A re-decode deletes each location's non-customized events before re-deriving them, while
 * matching writes links onto those same rows. Every other overlap in this system is at worst
 * duplicate work — the backend serialises writes, matching holds its own locks, decoding is
 * idempotent — so this is the only pair that genuinely needs excluding.
 *
 * ⚠️ Deliberately asymmetric, and that is what keeps it deadlock-free. Matching yields to a reset
 * that is merely *queued*, so a reset cannot be starved by a stream of matching work; a reset only
 * yields to matching that is already *running*, so it never waits on something waiting on it. Ties
 * go to the reset.
 */
export const excludeMatchingDuringReset: EligibilityRule = (candidate, all) => {
  if (isMatching(candidate))
    return !all.some(activity => activity.resets === true && !isTerminalStatus(activity.status));

  if (candidate.resets === true)
    return !all.some(activity => isMatching(activity) && activity.status === ActivityStatus.RUNNING);

  return true;
};

/** The rule set the reactive orchestrator is configured with by default. */
export const DEFAULT_RULES: readonly EligibilityRule[] = [pauseBalancesDuringHistorySync, excludeMatchingDuringReset];

/** True when every rule admits the candidate. */
export function allRulesPass(rules: readonly EligibilityRule[], candidate: Activity, all: readonly Activity[]): boolean {
  return rules.every(rule => rule(candidate, all));
}
