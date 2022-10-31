import { Validation } from '@vuelidate/core';
import { MaybeRef } from '@vueuse/core';

export const useValidation = <V>(v$: MaybeRef<Validation<V>>) => {
  const hasError = () => {
    const validator = get(v$);
    return validator.$error;
  };

  const callIfValid = <T = unknown>(
    value: T,
    method: (e: T) => void,
    invalid: () => Boolean = hasError
  ) => {
    if (!invalid()) {
      method(value);
    }
  };

  return {
    callIfValid
  };
};
