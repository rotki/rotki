import { isEmpty } from 'es-toolkit/compat';
import { camelCaseTransformer } from '@/modules/api/transformers';

/**
 * Converts a stringified JSON returned from the API to JSON.
 *
 * Use {@link ApiValidationError} in the catch clause instead.
 * @param message a stringified json message
 */
function deserializeApiErrorMessage(message: string): Record<string, string[]> | undefined {
  try {
    return JSON.parse(message);
  }
  catch {
    return undefined;
  }
}

export type ValidationErrors = Record<string, string[] | string>;

export class ApiValidationError extends Error {
  readonly errors: ValidationErrors;
  constructor(message: string) {
    super(message);
    this.name = 'ApiValidationError';
    this.errors = camelCaseTransformer(deserializeApiErrorMessage(message)) ?? {};
  }

  getValidationErrors(payload: Record<string, any>): ValidationErrors | string {
    const errors = this.errors;
    const errorKeys = Object.keys(errors);
    const payloadKeys = Object.keys(payload);

    if (Object.keys(payload).length > 0) {
      for (const errorKey of errorKeys) {
        if (!payloadKeys.includes(errorKey)) {
          const entry = errors[errorKey];
          if (typeof entry === 'string')
            return entry;

          return entry[0] || '';
        }
      }
    }

    if (!isEmpty(errors))
      return errors;

    return this.message;
  }
}
