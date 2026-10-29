import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { Balance } from '@rotki/common';
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
  connector: z.string(),
  displayName: z.string(),
  accessTier: z.string(),
  capabilities: z.array(z.string()),
  authFlow: z.array(BankAuthStep),
  secrets: z.array(BankSecretField),
  maintainer: z.string(),
  version: z.string(),
  docsUrl: z.string(),
  setupNotes: z.array(z.string()),
  /** The connector's logo among the protocol images, or null for the generic bank icon. */
  image: z.string().nullable(),
});

export type BankManifest = z.infer<typeof BankManifest>;

export const BankManifests = z.array(BankManifest);

export type BankManifests = z.infer<typeof BankManifests>;

export const BankAuthChallenge = z.object({
  /** The connection the challenge is answered for, also before a new connection is saved. */
  identifier: z.string().nullish(),
  primitive: z.enum(['otp input', 'app approval poll', 'challenge display']),
  prompt: z.string(),
  challenge: z.string().nullable(),
  challengeHtml: z.string().nullable(),
  challengeData: z.string().nullable(),
  challengeMimeType: z.string().nullable(),
  pollDelaySeconds: z.number().nullable().optional(),
});

export type BankAuthChallenge = z.infer<typeof BankAuthChallenge>;

/** Every challenge but an app approval is answered by typing what the bank generated. */
export function challengeNeedsResponse(challenge: BankAuthChallenge): boolean {
  return challenge.primitive !== 'app approval poll';
}

export const BankSetupSuccess = z.object({
  success: z.literal(true),
  identifier: z.string(),
  historyStartTs: z.number().nullable(),
});

export type BankSetupSuccess = z.infer<typeof BankSetupSuccess>;

export type BankSetupResult = true | BankSetupSuccess | BankAuthChallenge;

export function isBankSetupComplete(result: BankSetupResult): result is true | BankSetupSuccess {
  return result === true || 'success' in result;
}

const BankSyncStatus = z.object({
  authChallenge: BankAuthChallenge.nullable(),
  /** the bank rejected or expired the last challenge; syncing again raises a fresh one */
  authExpired: z.boolean(),
  running: z.boolean(),
  lastSyncTs: z.number().nullable(),
  lastError: z.string().nullable(),
});

export const BankConnection = z.object({
  identifier: z.string(),
  name: z.string(),
  connector: z.string(),
  displayName: z.string(),
  /** The bank code (BLZ) of the institution, for a connector such as FinTS that reaches many banks. */
  bankCode: z.string().nullable(),
  syncStatus: BankSyncStatus,
});

export type BankConnection = z.infer<typeof BankConnection>;

export const BankConnections = z.array(BankConnection);

export type BankConnections = z.infer<typeof BankConnections>;

/** One account of a bank connection and what it holds; an account holds a single currency. */
export const BankAccountBalance = Balance.extend({
  identifier: z.string(),
  name: z.string(),
  iban: z.string().nullable(),
  asset: z.string(),
});

export type BankAccountBalance = z.infer<typeof BankAccountBalance>;

export const BankConnectionBalances = z.object({
  identifier: z.string(),
  connector: z.string(),
  name: z.string(),
  balances: AssetBalances,
  accounts: z.array(BankAccountBalance),
});

export type BankConnectionBalances = z.infer<typeof BankConnectionBalances>;

export const BankBalancesResponse = z.object({
  aggregate: AssetBalances,
  connections: z.array(BankConnectionBalances),
});

export type BankBalancesResponse = z.infer<typeof BankBalancesResponse>;

/**
 * A bank connection as the sync machinery tracks it.
 *
 * @remarks
 * Requests address the connection by its `identifier`, which never changes. The history status
 * frames name its connector as `location`, together with its name, so those travel along to
 * match them.
 */
export interface BankConnectionIdentity {
  readonly identifier: string;
  readonly connector: string;
  readonly name: string;
}

export interface BankAuthenticationRequest extends BankConnectionIdentity {
  readonly challenge: BankAuthChallenge;
}

export interface BankConnectionPayload {
  readonly name: string;
  readonly connector: string;
  /** Credentials keyed by the manifest secret slot they belong to. */
  readonly credentials: Record<string, string>;
}

export interface BankConnectionEditPayload {
  readonly identifier: string;
  readonly credentials: Record<string, string>;
  readonly newName?: string;
}

/**
 * Why the backend refused to add or edit a connection.
 *
 * @remarks
 * `fields` carries errors keyed by payload field, or by credential slot for a credential error.
 * `rejected` is a message for the request as a whole, such as the bank refusing the credentials;
 * an answer refused this way can be sent again. `expired` is an answer to a challenge the bank
 * rejected or let lapse and has dropped: only a new sync, or a new setup, raises another.
 */
export type BankSetupError =
  | { readonly type: 'fields'; readonly errors: ValidationErrors }
  | { readonly type: 'rejected' | 'expired'; readonly message: string };

export interface BankSyncPayload {
  readonly connector?: string;
  readonly identifier?: string;
}

export interface BankFormData {
  mode: 'add' | 'edit';
  /** Set when editing an existing connection. */
  identifier?: string;
  name: string;
  connector: string;
  credentials: Record<string, string>;
  newName: string;
}
