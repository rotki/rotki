import type { Ref } from 'vue';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { toServerErrors } from '@/modules/core/form/server-errors';

interface UseSaveFailureReturn {
  /** Why the save failed where no field is to blame; shown above the form, which keeps its input. */
  failure: Readonly<Ref<unknown>>;
  /** Errors the backend reported against fields, bound to the form's `error-messages`. */
  modelFieldErrors: Ref<ValidationErrors>;
  /** Files a rejected save under the fields it names, or as the failure when it names none. */
  capture: (error: unknown, payload: Record<string, unknown>) => void;
  clear: () => void;
}

/**
 * The failure of a form dialog's save, kept in the dialog instead of a message over it.
 *
 * @remarks
 * A validation error whose keys are all in the payload goes to the fields; one keyed on anything else
 * (the whole payload, a field the form does not show) has nowhere to sit, so it becomes the failure.
 * Any other error is kept as thrown, so the strip can tell an unreachable backend from a rejection.
 */
export function useSaveFailure(): UseSaveFailureReturn {
  const failure = shallowRef<unknown>();
  const modelFieldErrors = ref<ValidationErrors>({});

  function clear(): void {
    set(failure, undefined);
    set(modelFieldErrors, {});
  }

  function capture(error: unknown, payload: Record<string, unknown>): void {
    clear();
    if (!(error instanceof ApiValidationError)) {
      set(failure, error);
      return;
    }
    const errors = error.getValidationErrors(payload);
    if (typeof errors === 'string')
      set(failure, errors);
    else
      set(modelFieldErrors, toServerErrors(errors));
  }

  return {
    capture,
    clear,
    failure: readonly(failure),
    modelFieldErrors,
  };
}
