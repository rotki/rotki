import type { MessageKey } from '@/message-key';
import type { ActivityId, ActivityKind } from '@/modules/task-center/core/types';

/**
 * What a user-triggerable history flow *is*, as data.
 *
 * A flow is the thing a user asked for ("re-decode everything"), as opposed to the mechanism that
 * carries it out (N per-chain decodes). Declaring it makes four things fall out at once: it is an
 * **activity**, so re-entry dedups by id from every surface — including callers in other modules
 * that button-state guarding can never reach; it is the **parent** of the mechanism activities, so
 * the shape of the work is visible before any of it runs; it is **data**, so its shape can be
 * asserted in a test without mounting anything; and it carries its own **documentation**.
 *
 * Declarations live beside their producers as `*.flow.ts` — co-located rather than in a registry,
 * to avoid a dependency hub that would breach the per-file import cap and pull every producer into
 * anything importing it. Enumerability comes at test time instead, from
 * `import.meta.glob('@/modules/**\/*.flow.ts')`, so a flow cannot be forgotten by failing to
 * register it.
 */
/**
 * One mechanism activity a flow will submit, named before it exists.
 *
 * Identity and kind are what a reader needs to see the shape of the work; `payload` is what the
 * producer needs to actually invoke the mechanism. Keeping the payload on the child is what lets
 * the composable drive the run *from* the declaration, instead of the declaration describing a list
 * the composable rebuilds separately — two lists that agree only by inspection.
 */
export interface FlowChild<Payload = void> {
  /**
   * ⚠️ Must be the id the producer submits under. Build both from one shared constructor rather
   * than composing it here as well: a child whose declared id does not match its submitted one is
   * not gated by its parent, and nothing reports that.
   */
  readonly id: ActivityId;
  readonly kind: ActivityKind;
  /** What the mechanism is invoked with — a chain, an exchange, an online query type. */
  readonly payload: Payload;
}

export interface HistoryFlow<Scope = void, ChildPayload = void> {
  /** The activity kind this flow submits under. */
  readonly kind: ActivityKind;
  /**
   * Stable identity — what makes re-entry a no-op rather than a second run.
   *
   * ⚠️ The identity must encode the flow's **scope**, not just its name. A scoped run sharing the
   * id of an unscoped one is not merely mislabelled: `submitTask` dedups it against the broader run
   * in flight and hands back that promise, so the caller silently gets work it did not ask for.
   * Omitting the scope asks for the flow's widest form, which is also its canonical id.
   */
  readonly id: (scope?: Scope) => ActivityId;
  /**
   * i18n key for the human-readable name, branded via `msg.$t` — a bare string here would be
   * invisible to the unused-key lint rule, since nothing translates it at the declaration site.
   */
  readonly titleKey: MessageKey;
  /**
   * Whether the flow deletes data before re-deriving it. Reset-bearing flows are the only ones
   * needing real exclusion: everything else overlaps harmlessly, because the backend serialises
   * writes, matching holds its own locks and decoding is idempotent. A reset racing a writer is
   * the one case that is not merely wasteful.
   */
  readonly resets?: boolean;
  /**
   * The mechanism activities this flow is made of, derived from its **resolved** scope.
   *
   * Resolved, not requested: what "everything" means is runtime state (which chains are decodable,
   * which exchanges are connected), and a declaration that reached for it would stop being data.
   * The producer resolves, then declares — so the whole shape exists in one synchronous pass,
   * before any of it runs, and a test can assert it without mounting anything or faking a backend.
   *
   * Heterogeneous by design: a refresh's children are per-chain syncs, exchange queries, online
   * event queries and decodes, not one repeated kind. Conditionality belongs in the resolution that
   * produces the scope, never in a child that may or may not turn out to exist.
   *
   * Required, not optional: a flow that declined to say what it is made of would leave the producer
   * as the only description of the work, which is the thing this exists to stop. A flow that really
   * has no mechanisms under it returns an empty list and says so.
   */
  readonly children: (scope: Scope) => readonly FlowChild<ChildPayload>[];
}

/**
 * Any flow, whatever it scopes by — for readers that enumerate declarations rather than invoke one.
 *
 * `never` and not `unknown`: `id` is contravariant in its scope, so the supertype of every
 * `HistoryFlow<S>` is the one whose scope nothing can be passed for.
 */
export type AnyHistoryFlow = HistoryFlow<never, unknown>;
