/**
 * Who asked for a balance refresh, which is what decides what happens when the chain is already busy.
 *
 * - `BACKGROUND`: join the run in flight. Two callers wanting the same thing share one query.
 * - `PERIODIC`: settle SKIPPED with a reason. A tick that finds the chain busy has nothing to add,
 *   and recording it as `ok` would mark the chain refreshed when nothing ran.
 * - `USER`: supersede. Someone pressed refresh, so they get a fresh query with *their* parameters
 *   rather than whatever the background run happened to be doing. Also the only mode exempt from
 *   the orchestrator's history-sync pause.
 *
 * Lives apart from `use-blockchain-balances` so a spec mocking that composable keeps the enum.
 */
export const RefreshMode = {
  BACKGROUND: 'background',
  PERIODIC: 'periodic',
  USER: 'user',
} as const;

export type RefreshMode = (typeof RefreshMode)[keyof typeof RefreshMode];
