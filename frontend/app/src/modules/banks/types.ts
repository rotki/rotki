import { z } from 'zod';
import { AssetBalances } from '@/modules/balances/types/balances';

/** One credential the bank's manifest asks for, and the slot it is stored in. */
const BankSecretField = z.object({
  slot: z.string(),
  label: z.string(),
  description: z.string(),
});

const BankAuthStep = z.object({
  primitive: z.string(),
  timeoutSeconds: z.number().optional(),
  prompt: z.string().optional(),
});

/** What the backend knows about a bank connector without running it. */
export const BankManifest = z.object({
  location: z.string(),
  displayName: z.string(),
  accessTier: z.string(),
  capabilities: z.array(z.string()),
  authFlow: z.array(BankAuthStep),
  secrets: z.array(BankSecretField),
  maintainer: z.string(),
  version: z.string(),
  docsUrl: z.string(),
  setupNotes: z.array(z.string()),
});

export type BankManifest = z.infer<typeof BankManifest>;

export const BankManifests = z.array(BankManifest);

export type BankManifests = z.infer<typeof BankManifests>;

const BankSyncStatus = z.object({
  running: z.boolean(),
  lastSyncTs: z.number().nullable(),
  lastError: z.string().nullable(),
});

export const BankConnection = z.object({
  name: z.string(),
  location: z.string(),
  displayName: z.string(),
  syncStatus: BankSyncStatus,
});

export type BankConnection = z.infer<typeof BankConnection>;

export const BankConnections = z.array(BankConnection);

export type BankConnections = z.infer<typeof BankConnections>;

export const BankBalancesByLocation = z.record(z.string(), AssetBalances);

export type BankBalancesByLocation = z.infer<typeof BankBalancesByLocation>;

export interface BankConnectionIdentity {
  readonly location: string;
  readonly name: string;
}

export interface BankConnectionPayload extends BankConnectionIdentity {
  /** Credentials keyed by the manifest secret slot they belong to. */
  readonly credentials: Record<string, string>;
}

export interface BankConnectionEditPayload extends BankConnectionPayload {
  readonly newName?: string;
}

export interface BankSyncPayload {
  readonly location?: string;
  readonly name?: string;
}

export interface BankFormData extends BankConnectionPayload {
  mode: 'add' | 'edit';
  newName: string;
}
