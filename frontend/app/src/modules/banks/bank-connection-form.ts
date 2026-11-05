import type { BankFormData, BankManifest } from '@/modules/banks/types';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';

export interface BankConnectionFormState {
  connector: string;
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
    name: data.name,
    newName: data.newName,
  };
}

/** The state a manifest's secrets start from: every slot present and empty. */
export function emptyCredentials(manifest: BankManifest | undefined): Record<string, string> {
  return Object.fromEntries((manifest?.secrets ?? []).map(secret => [secret.slot, '']));
}

function isPresent(value: string | undefined): boolean {
  return value !== undefined && value.trim() !== '';
}

/**
 * Validation rules of a bank connection form.
 *
 * @remarks
 * Adding needs a connector, a name and every credential the manifest declares. Editing needs
 * the new name; credentials are optional, with empty values keeping the stored ones.
 */
export function bankConnectionSchema(mode: BankFormData['mode'], manifest: BankManifest | undefined): ZodType<BankConnectionFormState> {
  return z.object({
    connector: z.string(),
    credentials: z.record(z.string(), z.string()),
    name: z.string(),
    newName: z.string(),
  }).superRefine((state, ctx) => {
    const required = msg.$t('bank_settings.form.validation.required');
    if (!isPresent(isEditing(mode) ? state.newName : state.name))
      ctx.addIssue({ code: 'custom', message: required, path: [isEditing(mode) ? 'newName' : 'name'] });
    if (isEditing(mode))
      return;
    if (!isPresent(state.connector))
      ctx.addIssue({ code: 'custom', message: required, path: ['connector'] });
    for (const secret of manifest?.secrets ?? []) {
      if (!isPresent(state.credentials[secret.slot]))
        ctx.addIssue({ code: 'custom', message: required, path: ['credentials', secret.slot] });
    }
  });
}

/** A new connection, preselecting the requested connector when available. */
export function createNewBank(available: BankManifest[], requestedConnector?: string): BankFormData {
  const manifest = available.find(manifest => manifest.connector === requestedConnector) ?? available[0];
  return {
    connector: manifest?.connector ?? '',
    credentials: emptyCredentials(manifest),
    mode: 'add',
    name: '',
    newName: '',
  };
}
