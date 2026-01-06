import type { ComputedRef, MaybeRef, ModelRef, Ref } from 'vue';
import useVuelidate, { type ValidationArgs } from '@vuelidate/core';
import { isEmpty } from 'es-toolkit/compat';
import { useFormStateWatcher } from '@/composables/form';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { toMessages } from '@/utils/validation';

export { toMessages };

export type CommonRules = ReturnType<ReturnType<typeof useEventFormValidation>['createCommonRules']>;

type RulesInput<TRules extends ValidationArgs> =
  | TRules
  | Ref<TRules>
  | ComputedRef<TRules>
  | ((commonRules: CommonRules) => TRules | Ref<TRules> | ComputedRef<TRules>);

type StatesInput<TState extends object> = TState | Ref<TState> | ComputedRef<TState>;

interface UseEventFormBaseOptions<
  TState extends object,
  TRules extends ValidationArgs,
> {
  rules: RulesInput<TRules>;
  states: StatesInput<TState>;
  errorMessages: Ref<Record<string, string[]>>;
  stateUpdated: ModelRef<boolean>;
  /** Optional: states to use for form state watcher (defaults to states if not provided) */
  formStates?: Record<string, MaybeRef<unknown>>;
}

interface UseEventFormBaseReturn {
  v$: ReturnType<typeof useVuelidate>;
  commonRules: CommonRules;
  captureEditModeState: ReturnType<typeof useEditModeStateTracker>['captureEditModeState'];
  captureEditModeStateFromRefs: ReturnType<typeof useEditModeStateTracker>['captureEditModeStateFromRefs'];
  shouldSkipSave: ReturnType<typeof useEditModeStateTracker>['shouldSkipSave'];
  shouldSkipSaveFromRefs: ReturnType<typeof useEditModeStateTracker>['shouldSkipSaveFromRefs'];
}

/**
 * Base composable for event forms that sets up:
 * - Vuelidate with standard configuration ($autoDirty, $externalResults)
 * - Error messages watcher for validation
 * - Form state watcher for tracking changes
 * - Edit mode state tracking
 * - Common validation rules
 *
 * @param options.rules - Can be a rules object, a Ref to rules, or a function that receives commonRules and returns rules
 * @param options.formStates - Optional: states to use for form state watcher (defaults to states if not provided)
 */
export function useEventFormBase<
  TState extends object,
  TRules extends ValidationArgs,
>(options: UseEventFormBaseOptions<TState, TRules>): UseEventFormBaseReturn {
  const { rules: rulesOption, states, errorMessages, stateUpdated, formStates } = options;

  const { createCommonRules } = useEventFormValidation();
  const commonRules = createCommonRules();

  const {
    captureEditModeState,
    captureEditModeStateFromRefs,
    shouldSkipSave,
    shouldSkipSaveFromRefs,
  } = useEditModeStateTracker();

  const rules = typeof rulesOption === 'function' ? rulesOption(commonRules) : rulesOption;

  // Type assertion needed due to complex vuelidate generics
  const v$ = useVuelidate(
    rules as Parameters<typeof useVuelidate>[0],
    states as Parameters<typeof useVuelidate>[1],
    {
      $autoDirty: true,
      $externalResults: errorMessages,
    },
  );

  // Use formStates for state watching if provided, otherwise use states
  const statesForWatcher = formStates ?? states;
  if (!isRef(statesForWatcher) && typeof statesForWatcher === 'object') {
    useFormStateWatcher(statesForWatcher, stateUpdated);
  }

  watch(errorMessages, async (errors) => {
    if (!isEmpty(errors))
      await get(v$).$validate();
  });

  return {
    v$,
    commonRules,
    captureEditModeState,
    captureEditModeStateFromRefs,
    shouldSkipSave,
    shouldSkipSaveFromRefs,
  };
}
