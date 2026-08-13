import type { MaybeRefOrGetter, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import { isEqual } from 'es-toolkit';
import { type FormApi, useForm } from '@/modules/core/form/use-form';

export interface ModelFormOptions<TState extends object> {
  /** The payload the parent dialog owns, saves, and reseeds. Edits are mirrored back into it. */
  readonly model: Ref<TState>;
  /** The single validation source of truth. A getter for rules that depend on props. */
  readonly schema: MaybeRefOrGetter<ZodType>;
  /** The dialog's unsaved-changes flag, kept in step with `dirty`. */
  readonly stateUpdated?: Ref<boolean>;
  /** State keys, at any depth, that must not count as an edit. */
  readonly transientKeys?: readonly string[];
}

/**
 * A form whose state belongs to the dialog above it.
 *
 * These forms validate and edit, but never persist: the dialog reads the payload straight off the
 * model when its save button is pressed. That makes the model and the form state two copies of the
 * same data which have to be kept in step, which is the boilerplate this removes.
 *
 * For a form that owns its own state and submits it, use `useForm` directly.
 */
export function useModelForm<TState extends object>(
  options: ModelFormOptions<TState>,
): FormApi<TState, UnwrapNestedRefs<TState>> {
  const { model, schema, stateUpdated, transientKeys } = options;

  const form = useForm<TState, UnwrapNestedRefs<TState>>({
    initial: (): TState => ({ ...get(model) }),
    schema,
    // The dialog owns the persist, so there is nothing to submit or reshape here.
    submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
    transform: (state): UnwrapNestedRefs<TState> => ({ ...state }),
    transientKeys,
  });

  // Every edit is written back, because the dialog saves what it reads off the model, not what the
  // form holds.
  // Spread over the current payload rather than the state alone: it keeps the result typed as the
  // payload, which the reactive state is not, without an assertion to bridge the two.
  watch(() => form.state, (state) => {
    set(model, { ...get(model), ...state });
  }, { deep: true });

  // And an edit made outside the form - a reset, a different row seeded while it stays mounted - is
  // pulled back in.
  //
  // The equality guard is defence, not the thing that makes this terminate: measured, the echo dies
  // on its own, because the copy above is shallow, so both sides end up holding the same nested
  // references and assigning them back is not a reactive change. That argument stops holding the
  // day the copy deep-clones, and the failure mode then is an endless update loop, so the guard
  // stays. `syncRef` handles the same problem by pausing the opposing watcher, but it needs two
  // refs and a sync flush, and this state is reactive and watched deep.
  watchImmediate(model, (value) => {
    if (!isEqual(value, form.state))
      Object.assign(form.state, value);
  }, { deep: true });

  if (stateUpdated) {
    // Immediate, so reopening a dialog that kept its flag from the last edit starts disarmed.
    syncRefs(form.dirty, stateUpdated);
  }

  return form;
}
