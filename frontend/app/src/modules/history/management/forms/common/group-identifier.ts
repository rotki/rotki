import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';

/**
 * How every form holds the group identifier.
 *
 * An event that was linked into another group carries that group's identifier, which then wins over
 * its own and locks the field, so the flag travels with the value.
 */
export interface GroupIdentifierFields {
  groupIdentifier: string;
  hasActualGroupIdentifier: boolean;
}

interface GroupIdentifierSource {
  actualGroupIdentifier?: string | null;
  groupIdentifier: string;
}

export function groupIdentifierFields(entry: GroupIdentifierSource): GroupIdentifierFields {
  const actual = entry.actualGroupIdentifier ?? '';

  return {
    groupIdentifier: actual === '' ? entry.groupIdentifier : actual,
    hasActualGroupIdentifier: actual !== '',
  };
}

/** The backend takes null for "no group", not an empty string. */
export function toNullableText(value: string): string | null {
  return value === '' ? null : value;
}

/**
 * @param required - only while editing. A new event may be created without one, and the backend
 * assigns it.
 */
export function groupIdentifierSchema(required: boolean): ZodType {
  if (!required)
    return z.string();

  return z.string().min(1, msg.$t('transactions.events.form.group_identifier.validation.non_empty'));
}
