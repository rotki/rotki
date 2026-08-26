import type { Lane } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, type ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

/**
 * Every leading slice of a tuple, including the empty one: `[A, B]` gives `[] | [A] | [A, B]`.
 *
 * Key parts run broadest to narrowest (chain, then what is acted on), so a coarse read supplies a
 * prefix* of the key. Typing it this way stops a reader asking for more key than exists.
 *
 * It does not stop a wrong value of the right shape: where two components are both `string`,
 * passing them in the wrong order is well-typed. That stays a review concern.
 */
type Prefixes<T extends readonly unknown[]> =
  T extends readonly [infer Head, ...infer Rest]
    ? readonly [] | readonly [Head, ...Prefixes<Rest>]
    : readonly [];

type KeyParts = readonly (string | number)[];

/**
 * One kind of work, declared once: how it is identified, which lane it runs in, and how a reader
 * asks about it.
 *
 * The point is that there is no second declaration. Spelling `makeActivityId(...)` at the producer
 * and a matching `useWorkStatus(...)` at each reader is an agreement nothing checks, and both ways
 * it breaks are silent: a key missing a component makes `submitTask` dedup distinct work onto one
 * promise and report it done; a key that *grows* one leaves every exact reader matching nothing, so
 * the spinner never fires.
 */
export interface ActivityDescriptor<TSubject, TKey extends KeyParts> {
  readonly kind: ActivityKind;
  /** The fixed part that follows the kind, before the subject's own key parts. */
  readonly part: ActivityPart;
  /** The subject's identity, broadest component first. */
  readonly keyOf: (subject: TSubject) => TKey;
  /** The full activity id for one subject. */
  readonly id: (subject: TSubject) => ActivityId;
  /**
   * The parts a reader passes to `useWorkStatus*` — `[part, ...key]`. Spread it rather than
   * rebuilding the shape at the call site, which is the drift this type exists to prevent.
   */
  readonly partsOf: (subject: TSubject) => KeyParts;
  /** As {@link partsOf}, for a prefix of the key: the coarse read. */
  readonly partsWithin: (prefix: Prefixes<TKey>) => KeyParts;
  /**
   * The id of the umbrella that parents a fan-out over `prefix` — one row per chain rather than one
   * per address. It sits under the same prefix as its children, so a coarse reader covers both, and
   * ends in a literal that no subject key part can produce.
   */
  readonly batchId: (prefix: Prefixes<TKey>) => ActivityId;
  /** The lane one subject's work runs in, when it declares one. */
  readonly laneOf?: (subject: TSubject) => Lane;
}

interface ActivityDescriptorInput<TSubject, TKey extends KeyParts> {
  readonly kind: ActivityKind;
  readonly part: ActivityPart;
  readonly key: (subject: TSubject) => TKey;
  readonly lane?: (subject: TSubject) => Lane;
}

/**
 * Declare an activity. See {@link ActivityDescriptor} for why the id and the readers must come from
 * one place.
 */
export function defineActivity<TSubject, const TKey extends KeyParts>(
  input: ActivityDescriptorInput<TSubject, TKey>,
): ActivityDescriptor<TSubject, TKey> {
  const partsOf = (subject: TSubject): KeyParts => [input.part, ...input.key(subject)];

  return {
    batchId: (prefix: Prefixes<TKey>): ActivityId =>
      makeActivityId(input.kind, input.part, ...prefix, ActivityPart.BATCH),
    id: (subject: TSubject): ActivityId => makeActivityId(input.kind, ...partsOf(subject)),
    keyOf: input.key,
    kind: input.kind,
    laneOf: input.lane,
    part: input.part,
    partsOf,
    partsWithin: (prefix: Prefixes<TKey>): KeyParts => [input.part, ...prefix],
  };
}
