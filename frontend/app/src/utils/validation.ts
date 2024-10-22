import type { BaseValidation, Validation } from '@vuelidate/core';
import type { MaybeRef } from '@vueuse/core';
import type { Ref } from 'vue';

/**
 * Converts an object of vuelidate's BaseValidation to an array of
 * strings to be passed to the components error-messages
 *
 * @param validation BaseValidation
 * @return string[]
 */
export function toMessages(validation: BaseValidation): string[] {
  return validation.$errors.map(e => get(e.$message));
}

export async function checkBeforeSubmission<T>(
  submit: () => Promise<T> | void,
  v$?: MaybeRef<Validation>,
  validState?: Ref<boolean>,
): Promise<T | void> {
  const validator = get(v$);
  let invalid = false;

  if (validator) {
    await validator.$validate();
    invalid = validator.$invalid;
  }

  if (!invalid)
    return submit();

  if (validState)
    set(validState, !invalid);
}
