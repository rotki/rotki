/**
 * What an activity carries *besides* its status: the per-subject shape a producer streams and a
 * panel renders, kept out of the record rather than folded into it.
 *
 * A record is the same shape for all 31 kinds, which is what lets the ledger, the tree and the
 * eligibility rules treat any activity as any other. Detail is per kind and open-ended (a period
 * cursor here, a protocol breakdown there), so folding it in would either widen every record with
 * optional fields no other kind sets, or push an `unknown` through the spine that every reader
 * would have to narrow by hand at the point it is displayed.
 */

/**
 * Fields the {@link Activity} projection already owns.
 *
 * Detail restating one of them is the failure this bans: two sources for one fact, disagreeing
 * whenever a websocket frame lands between the orchestrator settling a record and the panel
 * reading it. Progress belongs in `steps` through `reportProgress`, and terminal state in the
 * record's own status.
 */
type ReservedDetailKey = 'percentage' | 'reason' | 'startedAt' | 'status' | 'steps';

/**
 * The detail a descriptor ends up carrying: the declared type when it names none of
 * {@link ReservedDetailKey}, and `never` when it names any.
 *
 * Applied to `defineActivity`'s return rather than as a bound on its type parameter, because
 * `TDetail extends DetailShape<TDetail>` is a circular constraint and TypeScript rejects it. The
 * consequence is where the error lands: a detail restating a reserved key collapses to `never`, so
 * the declaration itself compiles and every publish against it fails instead.
 */
export type DetailShape<T> = T extends object
  ? Extract<keyof T, ReservedDetailKey> extends never
    ? T
    : never
  : never;
