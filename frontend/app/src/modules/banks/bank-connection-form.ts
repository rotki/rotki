import type { BankFormData, BankManifest } from '@/modules/banks/types';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';

export interface BankConnectionFormState {
  connector: string;
  location: string;
  name: string;
  newName: string;
  credentials: Record<string, string>;
}

export function isEditing(mode: BankFormData['mode']): boolean {
  return mode === 'edit';
}

export function toBankConnectionFormState(data: BankFormData): BankConnectionFormState {
  return {
    connector: data.connector,
    credentials: { ...data.credentials },
    location: data.location,
    name: data.name,
    newName: data.newName,
  };
}

/** The state a manifest's secrets start from: every slot present and empty. */
export function emptyCredentials(manifest: BankManifest | undefined): Record<string, string> {
  return Object.fromEntries((manifest?.secrets ?? []).map(secret => [secret.slot, '']));
}

/** Whether a connection of the connector chooses the bank its data belongs to. */
export function needsBankLocation(manifest: BankManifest | undefined): boolean {
  return manifest?.fixedLocation === null;
}

function isPresent(value: string | undefined): boolean {
  return value !== undefined && value.trim() !== '';
}

/** The paths of the fields a form in this mode still has to fill. */
function missingFields(mode: BankFormData['mode'], manifest: BankManifest | undefined, state: BankConnectionFormState): string[][] {
  if (isEditing(mode))
    return isPresent(state.newName) ? [] : [['newName']];
  return [
    ...(isPresent(state.name) ? [] : [['name']]),
    ...(isPresent(state.connector) ? [] : [['connector']]),
    ...(needsBankLocation(manifest) && !isPresent(state.location) ? [['location']] : []),
    ...(manifest?.secrets ?? [])
      .filter(secret => !isPresent(state.credentials[secret.slot]))
      .map(secret => ['credentials', secret.slot]),
  ];
}

/**
 * Validation rules of a bank connection form.
 *
 * @remarks
 * Adding needs a connector, a name, every credential the manifest declares, and a bank location
 * when the connector does not fix it. Editing needs the new name; the credentials are optional
 * there, an empty one means "keep the stored one".
 */
export function bankConnectionSchema(mode: BankFormData['mode'], manifest: BankManifest | undefined): ZodType<BankConnectionFormState> {
  return z.object({
    connector: z.string(),
    credentials: z.record(z.string(), z.string()),
    location: z.string(),
    name: z.string(),
    newName: z.string(),
  }).superRefine((state, ctx) => {
    for (const path of missingFields(mode, manifest, state))
      ctx.addIssue({ code: 'custom', message: msg.$t('bank_settings.form.validation.required'), path });
  });
}
