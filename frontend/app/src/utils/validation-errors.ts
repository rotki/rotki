import { ErrorObject } from '@vuelidate/core';

/**
 * Converts an array of vuelidate's ErrorObject to an array of
 * strings to be passed to the components error-messages.
 *
 * @param errors ErrorObject
 * @return string[]
 */
export const toMessages = (errors: ErrorObject[]) =>
  errors.map(e => get(e.$message));
