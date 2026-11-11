import type { ComputedRef, MaybeRefOrGetter } from 'vue';

/** What a step's form exposes for the step to check it. */
interface CheckableForm {
  validate: () => Promise<boolean>;
  errorCount: number;
}

interface UseStepCheckReturn {
  /** Fields still showing an error, counted only once the user has tried to move on. */
  issueCount: ComputedRef<number>;
  /** Reveals the form's errors and reports whether the step can be left. */
  validate: () => Promise<boolean>;
}

/**
 * Gates a wizard step's primary button on its form.
 *
 * @remarks
 * The button stays enabled; pressing it reveals what is missing instead. A form that is not
 * rendered, such as a collapsed optional section, holds nothing to check and passes.
 *
 * @param form - the step's form, usually a template ref
 */
export function useStepCheck(form: MaybeRefOrGetter<CheckableForm | null | undefined>): UseStepCheckReturn {
  const attempted = shallowRef<boolean>(false);

  const issueCount = computed<number>(() => (get(attempted) ? toValue(form)?.errorCount ?? 0 : 0));

  async function validate(): Promise<boolean> {
    set(attempted, true);
    return await toValue(form)?.validate() ?? true;
  }

  return { issueCount, validate };
}
