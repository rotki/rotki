import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { z } from 'zod';
import { AssetBalances } from '@/modules/balances/types/balances';

/** One credential the bank's manifest asks for, and the slot it is stored in. */
const BankSecretField = z.object({
  slot: z.string(),
  label: z.string(),
  description: z.string(),
  secret: z.boolean(),
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

export const BankAuthChallenge = z.object({
  primitive: z.enum(['otp input', 'app approval poll', 'challenge display']),
  prompt: z.string(),
  challenge: z.string().nullable(),
  challengeHtml: z.string().nullable(),
  challengeData: z.string().nullable(),
  challengeMimeType: z.string().nullable(),
});

export type BankAuthChallenge = z.infer<typeof BankAuthChallenge>;

/** Every challenge but an app approval is answered by typing what the bank generated. */
export function challengeNeedsResponse(challenge: BankAuthChallenge): boolean {
  return challenge.primitive !== 'app approval poll';
}

export const BankSetupSuccess = z.object({
  success: z.literal(true),
  historyStartTs: z.number().nullable(),
});

export type BankSetupSuccess = z.infer<typeof BankSetupSuccess>;

export type BankSetupResult = true | BankSetupSuccess | BankAuthChallenge;

export function isBankSetupComplete(result: BankSetupResult): result is true | BankSetupSuccess {
  return result === true || 'success' in result;
}

const BankSyncStatus = z.object({
  authChallenge: BankAuthChallenge.nullable(),
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

export interface BankAuthenticationRequest extends BankConnectionIdentity {
  readonly challenge: BankAuthChallenge;
}

export interface BankConnectionPayload extends BankConnectionIdentity {
  /** Credentials keyed by the manifest secret slot they belong to. */
  readonly credentials: Record<string, string>;
}

export interface BankConnectionEditPayload extends BankConnectionPayload {
  readonly newName?: string;
}

/**
 * Why the backend refused to add or edit a connection.
 *
 * @remarks
 * `fields` carries errors keyed by payload field, or by credential slot for a credential error.
 * `rejected` is a message for the request as a whole, such as the bank refusing the credentials.
 */
export type BankSetupError =
  | { readonly type: 'fields'; readonly errors: ValidationErrors }
  | { readonly type: 'rejected'; readonly message: string };

export interface BankSyncPayload {
  readonly location?: string;
  readonly name?: string;
}

export interface BankFormData extends BankConnectionPayload {
  mode: 'add' | 'edit';
  newName: string;
}
