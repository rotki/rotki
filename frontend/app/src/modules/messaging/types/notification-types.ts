import { z } from 'zod/v4';

export const BalanceSnapshotError = z.object({
  error: z.string(),
  location: z.string(),
});

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;

export const BinancePairsMissingData = z.object({
  location: z.string(),
  name: z.string(),
});

export type BinancePairsMissingData = z.infer<typeof BinancePairsMissingData>;

export const GnosisPaySessionKeyExpiredData = z.object({
  error: z.string(),
});

export type GnosisPaySessionKeyExpiredData = z.infer<typeof GnosisPaySessionKeyExpiredData>;

export const MissingApiKey = z.object({
  service: z.string(),
});

export type MissingApiKey = z.infer<typeof MissingApiKey>;

export const SolanaTokensMigrationData = z.object({
  identifiers: z.array(z.string()),
});

export type SolanaTokensMigrationData = z.infer<typeof SolanaTokensMigrationData>;
