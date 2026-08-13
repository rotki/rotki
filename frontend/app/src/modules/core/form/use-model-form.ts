import type { MaybeRefOrGetter, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { isEqual } from 'es-toolkit';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, useForm } from '@/modules/core/form/use-form';

export interface ModelFormOptions<TState extends object> {
  /** The payload the parent dialog owns, saves, and reseeds. Edits are mirrored back into it. */
  readonly model: Ref<TState>;
  /** The single validation source of truth. A getter for rules that depend on props. */
  readonly schema: MaybeRefOrGetter<ZodType>;
  /**
   * The state the form opens on, for a form that decides part of it itself: a remembered chain, a
   * suggested name. It is folded into the baseline rather than written over it, so what the form
   * chose for the user does not read back as something the user typed.
   */
  readonly seed?: (state: TState) => TState;
  /**
   * Field errors reported by the api, mirrored in as they arrive. Immediate, because the dialog may
   * already be holding errors from a failed save when the form mounts.
   */
  readonly serverErrors?: Ref<ValidationErrors>;
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
  const { model, schema, seed, serverErrors, stateUpdated, transientKeys } = options;

  const form = useForm<TState, UnwrapNestedRefs<TState>>({
    // Seeded here rather than by the caller writing the model first: a write to the model is only
    // readable back on the next tick, so a caller doing it by hand takes its baseline from the
    // payload as it was before the write, and the seeding then counts as the first edit.
    initial: (): TState => {
      const current = { ...get(model) };
      return seed ? seed(current) : current;
    },
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

  if (seed) {
    // The dialog saves what it reads off the model, so the opening state has to land there too. It
    // is not readable back on this tick, which is why the sync below skips its immediate run: the
    // state is already the newer of the two, and reading the model now would undo the seeding.
    set(model, { ...get(model), ...form.state });
  }

  if (serverErrors) {
    watchImmediate(serverErrors, (value) => {
      form.setServerErrors(toServerErrors(value));
    }, { deep: true });
  }

  // And an edit made outside the form - a reset, a different row seeded while it stays mounted - is
  // pulled back in.
  //
  // The equality guard is defence, not the thing that makes this terminate: measured, the echo dies
  // on its own, because the copy above is shallow, so both sides end up holding the same nested
  // references and assigning them back is not a reactive change. That argument stops holding the
  // day the copy deep-clones, and the failure mode then is an endless update loop, so the guard
  // stays. `syncRef` handles the same problem by pausing the opposing watcher, but it needs two
  // refs and a sync flush, and this state is reactive and watched deep.
  watch(model, (value) => {
    if (!isEqual(value, form.state))
      Object.assign(form.state, value);
  }, { deep: true, immediate: !seed });

  if (stateUpdated) {
    // Immediate, so reopening a dialog that kept its flag from the last edit starts disarmed.
    syncRefs(form.dirty, stateUpdated);
  }

  return form;
}
