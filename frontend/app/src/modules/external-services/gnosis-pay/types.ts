import { z } from 'zod/v4';

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
