import { z } from 'zod';

/**
 * What a backend task manager task works on, as the backend's `BackgroundTaskKind` spells it.
 *
 * @remarks
 * The schemas below read `kind` as a plain string, so a kind a newer backend adds still parses and
 * is treated as {@link BackgroundTaskKind.OTHER}.
 */
export const BackgroundTaskKind = {
  CALENDAR_SYNC: 'calendar_sync',
  DATA_UPDATES: 'data_updates',
  DB_UPLOAD: 'db_upload',
  ETH_STAKING: 'eth_staking',
  EVM_ACCOUNTS_DETECTION: 'evm_accounts_detection',
  EVM_RECEIPTS: 'evm_receipts',
  EVM_TRANSACTIONS: 'evm_transactions',
  EXCHANGE_HISTORY: 'exchange_history',
  HISTORICAL_BALANCES: 'historical_balances',
  OTHER: 'other',
  SNAPSHOT_BALANCES: 'snapshot_balances',
  TRANSACTION_DECODING: 'transaction_decoding',
  XPUB_DERIVATION: 'xpub_derivation',
} as const;

export type BackgroundTaskKind = (typeof BackgroundTaskKind)[keyof typeof BackgroundTaskKind];

const KNOWN_KINDS: ReadonlySet<string> = new Set<string>(Object.values(BackgroundTaskKind));

function isBackgroundTaskKind(kind: string): kind is BackgroundTaskKind {
  return KNOWN_KINDS.has(kind);
}

/** The task's kind, or {@link BackgroundTaskKind.OTHER} for one this build does not know. */
export function backgroundTaskKindOf(kind: string): BackgroundTaskKind {
  return isBackgroundTaskKind(kind) ? kind : BackgroundTaskKind.OTHER;
}

export const BackgroundTaskStatus = {
  CANCELLED: 'cancelled',
  FAILED: 'failed',
  FINISHED: 'finished',
  STARTED: 'started',
} as const;

/**
 * One running task manager task, as the periodic data lists it.
 *
 * @remarks
 * `id` tells two tasks with the same name apart and is only stable within one login. `subject`
 * depends on the kind: `chain` and `address` for EVM transactions, `chain` and `count` for receipts
 * and decoding, `location` and `name` for exchange history, `chain` for xpub derivation.
 */
export const BackgroundTask = z.object({
  id: z.number().int(),
  kind: z.string(),
  name: z.string(),
  startedAt: z.number(),
  subject: z.record(z.string(), z.union([z.string(), z.number()])),
});

export type BackgroundTask = z.infer<typeof BackgroundTask>;

/** A task manager task starting or ending. `error` is set only on a failure treated as an error. */
export const BackgroundTaskStatusData = BackgroundTask.extend({
  error: z.string().optional(),
  status: z.enum([
    BackgroundTaskStatus.CANCELLED,
    BackgroundTaskStatus.FAILED,
    BackgroundTaskStatus.FINISHED,
    BackgroundTaskStatus.STARTED,
  ]),
});

export type BackgroundTaskStatusData = z.infer<typeof BackgroundTaskStatusData>;
