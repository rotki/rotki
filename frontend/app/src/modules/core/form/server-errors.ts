import type { ValidationErrors } from '@/modules/core/api/types/errors';

/**
 * The api reports a field's errors as either one message or a list of them, while the form core
 * takes a list per path. An empty message carries no information and would only reserve space under
 * the field, so it is dropped.
 */
export function toMessageList(value: ValidationErrors[string] | undefined): string[] {
  if (value === undefined)
    return [];

  return (Array.isArray(value) ? value : [value]).filter(message => message !== '');
}

/** Api validation errors as `setServerErrors` takes them, assuming field names match state keys. */
export function toServerErrors(errors: ValidationErrors): Record<string, string[]> {
  return Object.fromEntries(
    Object.entries(errors).map(([field, messages]) => [field, toMessageList(messages)]),
  );
}
