import type { Validation, ValidationArgs } from '@vuelidate/core';
import type { MaybeRef } from '@vueuse/core';

interface UseValidationReturn {
  callIfValid: <T = unknown>(value: T, method: (e: T) => void, invalid?: () => boolean) => void;
}

export function useValidation<V extends ValidationArgs>(v$: MaybeRef<Validation<V>>): UseValidationReturn {
  const hasError = (): boolean => {
    const validator = get(v$);
    return validator.$error;
  };

  const callIfValid = <T = unknown>(value: T, method: (e: T) => void, invalid: () => boolean = hasError): void => {
    if (!invalid())
      method(value);
  };

  return {
    callIfValid,
  };
}
