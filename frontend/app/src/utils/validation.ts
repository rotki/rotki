import { type BaseValidation, type Validation } from '@vuelidate/core';
import { type MaybeRef } from '@vueuse/core';

/**
 * Converts an object of vuelidate's BaseValidation to an array of
 * strings to be passed to the components error-messages
 *
 * @param validation BaseValidation
 * @return string[]
 */
export const toMessages = (validation: BaseValidation): string[] =>
  validation.$errors.map(e => get(e.$message));

export const checkBeforeSubmission = async <T>(
  submit: () => Promise<T> | void,
  v$?: MaybeRef<Validation>,
  validState?: Ref<boolean>
): Promise<T | void> => {
  const validator = get(v$);
  let invalid = false;

  if (validator) {
    await validator.$validate();
    invalid = validator.$invalid;
  }

  if (!invalid) {
    return await submit();
  }

  if (validState) {
    set(validState, !invalid);
  }
};
