import type { Eth2Validator } from '@/modules/balances/types/balances';
import { consistOfNumbers } from '@rotki/common';
import { z, type ZodType } from 'zod';

/**
 * What the form edits. The payload holds the same three fields, but readonly and only once each has
 * a value, so the form cannot edit it in place and keeps its own mutable copy.
 */
export interface Eth2ValidatorFormState {
  ownershipPercentage: string;
  publicKey: string;
  validatorIndex: string;
}

/** An absent field edits as empty text. */
export function toFormState(validator: Eth2Validator): Eth2ValidatorFormState {
  return {
    ownershipPercentage: validator.ownershipPercentage ?? '',
    publicKey: validator.publicKey ?? '',
    validatorIndex: validator.validatorIndex ?? '',
  };
}

export interface Eth2ValidatorMessages {
  ownershipPercentage: string;
  required: string;
  validatorIndex: string;
}

/** Blank means "the default 100%"; anything else has to land inside the range. */
export function isValidOwnershipPercentage(value: string): boolean {
  return !value || (Number(value) > 0 && Number(value) <= 100);
}

interface FieldIssue {
  message: string;
  path: string;
}

/**
 * The index and the public key identify the same validator, so each is required only while the
 * other is blank.
 *
 * The old rule trimmed the field it guarded but read its companion as typed, so a whitespace-only
 * entry counts as filled for the other field while still failing its own check. Kept: the two sides
 * are not interchangeable, and the fields trim on input, so only a seeded payload can get there.
 */
function identifierIssues(validatorIndex: string, publicKey: string, messages: Eth2ValidatorMessages): FieldIssue[] {
  const issues: FieldIssue[] = [];

  // Reported in the order the vuelidate rules were declared: a field renders every message it
  // collects, and the order is what the user reads.
  if (validatorIndex && !consistOfNumbers(validatorIndex))
    issues.push({ message: messages.validatorIndex, path: 'validatorIndex' });

  if (validatorIndex.trim() === '' && publicKey === '')
    issues.push({ message: messages.required, path: 'validatorIndex' });

  if (publicKey.trim() === '' && validatorIndex === '')
    issues.push({ message: messages.required, path: 'publicKey' });

  return issues;
}

/**
 * A validator is identified either by its index or by its public key, so neither field can be
 * required on its own. The pair is checked on the object rather than per field, which is also what
 * keeps the two checks from depending on each other's validity.
 *
 * Each field is optional here because the payload leaves it out until it has a value, and an
 * untouched form must not be reported as holding the wrong type: a structural failure on a field
 * bound to no message would block the save with nothing on screen.
 */
export function eth2ValidatorSchema(messages: Eth2ValidatorMessages): ZodType {
  return z.object({
    ownershipPercentage: z.string().optional(),
    publicKey: z.string().optional(),
    validatorIndex: z.string().optional(),
  }).superRefine((state, ctx) => {
    const ownershipPercentage = state.ownershipPercentage ?? '';
    const issues = identifierIssues(state.validatorIndex ?? '', state.publicKey ?? '', messages);

    if (!isValidOwnershipPercentage(ownershipPercentage))
      issues.push({ message: messages.ownershipPercentage, path: 'ownershipPercentage' });

    for (const { message, path } of issues)
      ctx.addIssue({ code: 'custom', message, path: [path] });
  });
}
