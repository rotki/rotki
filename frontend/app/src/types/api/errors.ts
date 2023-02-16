import isEmpty from 'lodash/isEmpty';
import { deserializeApiErrorMessage } from '@/services/converters';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';

export type ValidationErrors = Record<string, string[] | string>;

export class ApiValidationError extends Error {
  readonly errors: ValidationErrors;
  constructor(message: string) {
    super(message);
    this.name = 'ApiValidationError';
    this.errors =
      axiosCamelCaseTransformer(deserializeApiErrorMessage(message)) ?? {};
  }

  getValidationErrors(payload: Object): ValidationErrors | string {
    const errors = this.errors;
    const errorKeys = Object.keys(errors);
    const payloadKeys = Object.keys(payload);

    for (const errorKey of errorKeys) {
      if (!payloadKeys.includes(errorKey)) {
        const entry = errors[errorKey];
        if (typeof entry === 'string') {
          return entry;
        }
        return entry[0] || '';
      }
    }

    if (!isEmpty(errors)) {
      return errors;
    }
    return this.message;
  }
}
