import type { StaleAfterEdge } from './spec';
import { type ActivityId, activityIdHasPrefix, type ActivityKind, type ActivityStatus, type CompletionRecord, ActivityStatus as Status } from '../types';

/**
 * The completion ledger: durable per-id memory of what finished, when, and how. It is the
 * freshness backbone behind `everCompleted`. Every write to it lives here, along with the
 * `staleAfter` side that decides which consumers a completion invalidates. Pure and lifecycle-free:
 * these functions mutate only the ledger they are handed, which keeps the orchestrator module
 * about scheduling.
 */

/**
 * Write the outcome of a settled run. `lastSuccessAt` is sticky (a later failure keeps the last
 * known success), so `everCompleted` answers "did this ever load" rather than "did the last
 * attempt work".
 */
export function recordSettlement(
  id: ActivityId,
  kind: ActivityKind,
  status: ActivityStatus,
  settledAt: number,
  ledger: Map<ActivityId, CompletionRecord>,
): void {
  const previous = ledger.get(id);
  ledger.set(id, {
    kind,
    lastOutcome: status,
    lastSettledAt: settledAt,
    lastSuccessAt: status === Status.COMPLETE ? settledAt : previous?.lastSuccessAt,
  });
}

/**
 * Assert a completion nobody ran: the data is already here (restored from the DB on unlock), so
 * the ledger should say so. Written exactly like a real success, so a later real run supersedes it
 * on the same sticky terms.
 */
export function recordCompletion(
  id: ActivityId,
  kind: ActivityKind,
  completedAt: number,
  ledger: Map<ActivityId, CompletionRecord>,
): void {
  recordSettlement(id, kind, Status.COMPLETE, completedAt, ledger);
}

/**
 * Forget that anything under `kind:parts` ever completed, returning whether anything changed (so
 * the caller only emits when it did). Prefix-matched on a separator boundary, so dropping
 * `blockchain_balances` takes every chain, while `blockchain_balances:eth` takes only ethereum's.
 */
export function dropCompletions(
  kind: ActivityKind,
  parts: readonly (string | number)[],
  ledger: Map<ActivityId, CompletionRecord>,
): boolean {
  let dropped = false;
  for (const id of ledger.keys()) {
    if (activityIdHasPrefix(id, kind, ...parts)) {
      ledger.delete(id);
      dropped = true;
    }
  }
  return dropped;
}

/** Does `producer` satisfy any of the consumer's declared edges? */
export function edgesMatch(edges: readonly StaleAfterEdge[], producer: ActivityId): boolean {
  return edges.some(edge => activityIdHasPrefix(producer, edge.kind, ...(edge.parts ?? [])));
}

/**
 * Drop the freshness of everything that declared itself stale after `producer`, returning whether
 * anything changed (so the caller only emits when it did).
 *
 * Removing the ledger entry outright is what flips `everCompleted` back to false, which is the
 * whole effect: the consumer's next guarded fetch is admitted. Live records are untouched, so an
 * in-flight consumer keeps running and writes a fresh entry when it settles. A consumer never
 * invalidates itself — its own completion is what freshness means.
 */
export function markStaleAfter(
  producer: ActivityId,
  edgesByConsumer: ReadonlyMap<ActivityId, readonly StaleAfterEdge[]>,
  ledger: Map<ActivityId, CompletionRecord>,
): boolean {
  let marked = false;
  for (const [consumer, edges] of edgesByConsumer) {
    if (consumer === producer || !ledger.has(consumer))
      continue;
    if (edgesMatch(edges, producer)) {
      ledger.delete(consumer);
      marked = true;
    }
  }
  return marked;
}
