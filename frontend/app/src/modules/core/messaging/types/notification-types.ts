import { z } from 'zod';

export const BalanceSnapshotError = z.object({
  error: z.string(),
  location: z.string(),
});

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;

export const BinancePairsMissingData = z.object({
  identifier: z.string(),
  location: z.string(),
  name: z.string(),
});

export type BinancePairsMissingData = z.infer<typeof BinancePairsMissingData>;

// `not_connected` is sent to a user who never signed in, `expired` to one whose session stopped working
const SessionKeyExpiredReason = z.enum(['expired', 'not_connected']);

/**
 * Whether a session-expired message repeats a known condition.
 *
 * @remarks
 * `true` on the repeat sent on each redecode, `false` at the moment the session is first found
 * to be expired.
 */
const SessionKeyExpiredReminder = z.boolean();

export const GnosisPaySessionKeyExpiredData = z.object({
  error: z.string(),
  reason: SessionKeyExpiredReason,
  reminder: SessionKeyExpiredReminder,
});

export type GnosisPaySessionKeyExpiredData = z.infer<typeof GnosisPaySessionKeyExpiredData>;

export const NoAvailableIndexersData = z.object({
  chain: z.string(),
  reason: z.string().optional(),
});

export type NoAvailableIndexersData = z.infer<typeof NoAvailableIndexersData>;

export const OraclePenalizedData = z.object({
  oracle: z.string(),
  penaltyDuration: z.number(),
  reason: z.enum(['errors', 'timeout']),
});

export type OraclePenalizedData = z.infer<typeof OraclePenalizedData>;

export const MissingApiKey = z.object({
  service: z.string(),
  location: z.string().optional(),
  reason: z.enum(['key_not_usable']).optional(),
});

export type MissingApiKey = z.infer<typeof MissingApiKey>;

export const MoneriumSessionKeyExpiredData = z.object({
  error: z.string(),
  reason: SessionKeyExpiredReason,
  reminder: SessionKeyExpiredReminder,
});

export type MoneriumSessionKeyExpiredData = z.infer<typeof MoneriumSessionKeyExpiredData>;

export const SolanaTokensMigrationData = z.object({
  identifiers: z.array(z.string()),
});

export type SolanaTokensMigrationData = z.infer<typeof SolanaTokensMigrationData>;

export const UnmatchedAssetMovementsData = z.object({
  count: z.number(),
});

export type UnmatchedAssetMovementsData = z.infer<typeof UnmatchedAssetMovementsData>;

export const UnmatchedBridgeTransactionsData = z.object({
  count: z.number(),
});

export type UnmatchedBridgeTransactionsData = z.infer<typeof UnmatchedBridgeTransactionsData>;
