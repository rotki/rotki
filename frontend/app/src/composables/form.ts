import useVuelidate, { type GlobalConfig, type Validation, type ValidationArgs } from '@vuelidate/core';
import type { MaybeRef } from '@vueuse/core';
import type { ModelRef, Ref } from 'vue';

export interface UseFormReturn<T = void> {
  submitting: Ref<boolean>;
  openDialog: Ref<boolean>;
  valid: Ref<boolean>;
  v$: Ref<Validation> | undefined;
  setOpenDialog: (dialog: boolean) => void;
  closeDialog: () => void;
  setSubmitFunc: (func: () => Promise<T> | void) => void;
  setPostSubmitFunc: (func: (result: T) => void) => void;
  setValidation: (validationsArgs: ValidationArgs, states: Record<string, MaybeRef<any>>, config?: GlobalConfig) => Ref<Validation>;
  trySubmit: () => Promise<T | void>;
  stateUpdated: Ref<boolean>;
}

/**
 * Create a common composable for form
 * @template T - T is type of data that return from the submit function.
 * @deprecated replace any usages with a top-down approach.
 */
export function useForm<T = void>(): UseFormReturn<T> {
  const openDialog = ref<boolean>(false);
  const valid = ref<boolean>(true);
  const stateUpdated = ref<boolean>(false);
  let v$: Ref<Validation> | undefined;
  const submitFunc = ref<() => Promise<T> | void>(() => {});
  const postSubmitFunc = ref<(result: T | void) => void>(() => {});
  const submitting = ref<boolean>(false);

  const setValidation = (
    validationsArgs: ValidationArgs,
    states: Record<string, MaybeRef<any>>,
    config?: GlobalConfig,
  ): Ref<Validation> => {
    v$ = useVuelidate(validationsArgs, states, config);

    watch(v$, ({ $invalid, $dirty }) => {
      if ($dirty)
        set(valid, !$invalid);
    });

    setTimeout(() => {
      watch(
        () => states,
        () => {
          set(stateUpdated, true);
        },
        { deep: true, once: true },
      );
    }, 500);

    return v$;
  };

  const setSubmitFunc = (func: () => Promise<T> | void): void => {
    set(submitFunc, func);
  };

  const setPostSubmitFunc = (func: (result: T) => void): void => {
    set(postSubmitFunc, func);
  };

  const setOpenDialog = (dialog: boolean): void => {
    set(openDialog, dialog);
  };

  const closeDialog = (): void => {
    setOpenDialog(false);
    set(valid, true);
    set(stateUpdated, false);
  };

  const trySubmit = async (): Promise<T | void> => {
    set(submitting, true);
    try {
      const result = await checkBeforeSubmission<T>(get(submitFunc), v$, valid);

      if (result) {
        closeDialog();
        get(postSubmitFunc)(result);
      }
      return result;
    }
    catch (error: any) {
      logger.log(error);
    }
    finally {
      set(submitting, false);
    }
  };

  return {
    submitting,
    openDialog,
    valid,
    stateUpdated,
    v$,
    setOpenDialog,
    closeDialog,
    setSubmitFunc,
    setPostSubmitFunc,
    setValidation,
    trySubmit,
  };
}

export function useFormStateWatcher(
  states: Record<string, MaybeRef<any>>,
  stateUpdated: ModelRef<boolean>,
): void {
  setTimeout(() => {
    watch(
      () => states,
      () => {
        set(stateUpdated, true);
      },
      { deep: true, once: true },
    );
  }, 500);

  onUnmounted(() => {
    set(stateUpdated, false);
  });
}
