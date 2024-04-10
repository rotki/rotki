import useVuelidate, { type GlobalConfig, type Validation, type ValidationArgs,
} from '@vuelidate/core';
import type { MaybeRef } from '@vueuse/core';

/**
 * Create a common composable for form
 * @template T - T is type of data that return from the submit function.
 */
export function useForm<T = void>() {
  const openDialog: Ref<boolean> = ref(false);
  const valid: Ref<boolean> = ref(true);
  let v$: Ref<Validation> | undefined;
  const submitFunc: Ref<() => Promise<T> | void> = ref(() => {});
  const postSubmitFunc: Ref<(result: T | void) => void> = ref(() => {});
  const submitting: Ref<boolean> = ref(false);

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

    return v$;
  };

  const setSubmitFunc = (func: () => Promise<T> | void) => {
    set(submitFunc, func);
  };

  const setPostSubmitFunc = (func: (result: T) => void) => {
    set(postSubmitFunc, func);
  };

  const setOpenDialog = (dialog: boolean) => {
    set(openDialog, dialog);
  };

  const closeDialog = () => {
    setOpenDialog(false);
    set(valid, true);
  };

  const trySubmit = async (): Promise<T | void> => {
    set(submitting, true);
    const result = await checkBeforeSubmission<T>(get(submitFunc), v$, valid);

    if (result) {
      closeDialog();
      get(postSubmitFunc)(result);
    }

    set(submitting, false);
    return result;
  };

  return {
    submitting,
    openDialog,
    valid,
    v$,
    setOpenDialog,
    closeDialog,
    setSubmitFunc,
    setPostSubmitFunc,
    setValidation,
    trySubmit,
  };
}
