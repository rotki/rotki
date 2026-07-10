import { z } from 'zod';

export enum GnosisPayError {
  NO_REGISTERED_ACCOUNTS = 'NO_REGISTERED_ACCOUNTS',
  NO_WALLET_CONNECTED = 'NO_WALLET_CONNECTED',
  INVALID_ADDRESS = 'INVALID_ADDRESS',
  SIGNATURE_REJECTED = 'SIGNATURE_REJECTED',
  CONNECTION_FAILED = 'CONNECTION_FAILED',
  OTHER = 'OTHER',
}

export enum AuthStep {
  NOT_READY = 0,
  CONNECT_WALLET = 1,
  VALIDATE_ADDRESS = 2,
  SIGN_MESSAGE = 3,
  COMPLETE = 4,
}

export interface GnosisPayErrorContext {
  adminsMapping?: Record<string, string[]>;
  message?: string;
}

export const GnosisPayAdminsMappingSchema = z.record(z.string(), z.array(z.string()));

export type GnosisPayAdminsMapping = z.infer<typeof GnosisPayAdminsMappingSchema>;

export const GnosisPayUntrackedSafeSchema = z.object({
  address: z.string(),
  type: z.enum(['new', 'old']),
});

export type GnosisPayUntrackedSafe = z.infer<typeof GnosisPayUntrackedSafeSchema>;

export const GnosisPaySafeMigrationSchema = z.object({
  migrationId: z.string(),
  untrackedAddresses: z.array(GnosisPayUntrackedSafeSchema),
});

export type GnosisPaySafeMigration = z.infer<typeof GnosisPaySafeMigrationSchema>;
