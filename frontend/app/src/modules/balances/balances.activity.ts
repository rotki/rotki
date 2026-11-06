import type { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { setDigest } from '@/modules/core/common/data/digest';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { BALANCES_LANE, DETECT_LANE_PREFIX, EXCHANGE_LANE, familyLane } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** One chain's balance refresh, and whether it detects tokens first. */
export interface ChainBalancesSubject {
  readonly chain: string;
  readonly detect?: boolean;
  /** Narrows detection to these addresses. Ignored without `detect`. */
  readonly detectAddresses?: readonly string[];
}

/** A refresh over several chains, as the umbrella their jobs run under. */
export interface BalancesRunSubject {
  readonly chains: readonly string[];
  readonly mode: RefreshMode;
}

/** A manual balance being added, identified by where it is and what it holds. */
export interface ManualBalanceAddSubject {
  readonly location: string;
  readonly asset: string;
  readonly label: string;
}

type ChainBalancesKey = readonly [string] | readonly [string, ActivityPart] | readonly [string, ActivityPart, string];

/**
 * One chain's balance refresh.
 *
 * @remarks
 * `detect` and the address narrowing are part of the identity because `submitTask` dedups by it.
 * Share an id and a login sweep joins an in-flight background refresh, or a second addition joins
 * the first, and detection for those addresses silently never happens.
 *
 * Those parts are appended after the chain, never substituted: every reader asks by the chain
 * prefix, so the chain has to stay leading.
 */
export const chainBalancesActivity = defineActivity<ChainBalancesSubject, ChainBalancesKey>({
  key: (subject): ChainBalancesKey => {
    if (!subject.detect)
      return [subject.chain];
    return subject.detectAddresses?.length
      ? [subject.chain, ActivityPart.DETECT, setDigest(subject.detectAddresses)]
      : [subject.chain, ActivityPart.DETECT];
  },
  kind: ActivityKind.BLOCKCHAIN_BALANCES,
  lane: () => BALANCES_LANE,
});

/**
 * The umbrella of a refresh over several chains, keyed by the chain set and the mode, so a user
 * refresh never joins a background one over the same chains. Its leading `run` part keeps it out
 * of every chain's prefix.
 */
export const balancesRunActivity = defineActivity<BalancesRunSubject, readonly [ActivityPart, string, RefreshMode]>({
  key: subject => [ActivityPart.RUN, setDigest(subject.chains), subject.mode],
  kind: ActivityKind.BLOCKCHAIN_BALANCES,
});

/** The all-balances snapshot query. A singleton: its id is the bare kind. */
export const allBalancesActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ALL_BALANCES,
});

/**
 * The snapshot query a login load queues behind its chain jobs. Its own id, so a forced save
 * during the load is a second query rather than a join onto this one.
 */
export const allBalancesLoginActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ALL_BALANCES,
  part: ActivityPart.LOGIN,
});

/** Loading the manual balances. */
export const manualBalancesFetchActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.MANUAL_BALANCES,
  part: ActivityPart.FETCH,
});

/**
 * Adding a manual balance, keyed by location, asset and label so two concurrent saves never
 * share a promise and report each other's outcome.
 */
export const manualBalanceAddActivity = defineActivity<ManualBalanceAddSubject, readonly [string, string, string]>({
  key: subject => [subject.location, subject.asset, subject.label],
  kind: ActivityKind.MANUAL_BALANCES,
  part: ActivityPart.ADD,
});

/** Editing a manual balance, keyed by its identifier for the same reason. */
export const manualBalanceEditActivity = defineActivity<{ identifier: number }, readonly [number]>({
  key: subject => [subject.identifier],
  kind: ActivityKind.MANUAL_BALANCES,
  part: ActivityPart.EDIT,
});

/** Loading the NFT balances. A singleton: its id is the bare kind. */
export const nftBalancesActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.NFT_BALANCES,
});

/** One exchange's balances, one activity per location. */
export const exchangeBalancesActivity = defineActivity<{ location: string }, readonly [string]>({
  key: subject => [subject.location],
  kind: ActivityKind.EXCHANGE_BALANCES,
  lane: () => EXCHANGE_LANE,
});

/** One exchange's savings interest, one activity per location. */
export const exchangeSavingsActivity = defineActivity<{ location: string }, readonly [string]>({
  key: subject => [subject.location],
  kind: ActivityKind.EXCHANGE_SAVINGS,
  lane: () => EXCHANGE_LANE,
});

/**
 * Token detection for one address on one chain.
 *
 * @remarks
 * Per address so progress and cancel can name it. On the chain's own `detect:` family rather than
 * the balances lane: the chain job that awaits it holds a balances slot for its whole body, so
 * sharing that lane would deadlock it against its own children.
 */
export const tokenDetectionActivity = defineActivity<{ chain: string; address: string }, readonly [string, string]>({
  key: subject => [subject.chain, subject.address],
  kind: ActivityKind.TOKEN_DETECTION,
  lane: subject => familyLane(DETECT_LANE_PREFIX, subject.chain),
});
