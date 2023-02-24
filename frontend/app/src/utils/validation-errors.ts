import { type BaseValidation } from '@vuelidate/core';

/**
 * Converts an object of vuelidate's BaseValidation to an array of
 * strings to be passed to the components error-messages
 *
 * @param validation BaseValidation
 * @return string[]
 */
export const toMessages = (validation: BaseValidation): string[] =>
  validation.$errors.map(e => get(e.$message));
