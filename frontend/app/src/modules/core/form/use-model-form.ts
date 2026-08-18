import type { MaybeRefOrGetter, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { isEqual } from 'es-toolkit';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, useForm } from '@/modules/core/form/use-form';

interface SharedModelFormOptions<TState extends object> {
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

export interface ModelFormOptions<TState extends object> extends SharedModelFormOptions<TState> {
  /** The payload the parent dialog owns, saves, and reseeds. Edits are mirrored back into it. */
  readonly model: Ref<TState>;
}

export interface MappedModelFormOptions<
  TModel extends object,
  TState extends object,
> extends SharedModelFormOptions<TState> {
  /** The payload the parent dialog owns, saves, and reseeds. Edits are mirrored back into it. */
  readonly model: Ref<TModel>;
  /**
   * The payload as the inputs need to hold it. Called for the opening state and again for every
   * edit made outside the form.
   *
   * 🔴 It has to be stable: the same payload in must give a deep-equal state out. The mirroring
   * below compares the two to decide whether an outside edit is news, and a mapper that invents a
   * fresh value each call - a timestamp, a generated id - reports every pass as a change and the
   * two directions then write to each other without settling.
   */
  readonly toState: (model: TModel) => TState;
  /**
   * The state as the payload wants it. Handed the payload the dialog is currently holding as well,
   * so a form that edits part of a larger payload can fold its fields over it and leave the rest
   * alone.
   */
  readonly toModel: (state: UnwrapNestedRefs<TState>, model: TModel) => TModel;
}

/**
 * A form whose state belongs to the dialog above it, and whose fields are shaped differently from
 * the payload.
 *
 * The shapes disagree whenever the api's idea of a field is not the input's. A text input needs a
 * string to write into where the payload admits null; a key is masked while it is not being edited;
 * one payload field is edited through two inputs. Left to each field, that gap becomes a writable
 * computed per input, wrapping and unwrapping the same value on every keystroke. Given here, it is
 * two pure functions with the whole payload in view, which can be tested on their own.
 *
 * For a form whose state is the payload, use `useModelForm`, which is this with both mappers set to
 * a copy.
 */
export function useMappedModelForm<TModel extends object, TState extends object>(
  options: MappedModelFormOptions<TModel, TState>,
): FormApi<TState, UnwrapNestedRefs<TState>> {
  const { model, schema, seed, serverErrors, stateUpdated, toModel, toState, transientKeys } = options;

  const form = useForm<TState, UnwrapNestedRefs<TState>>({
    // Seeded here rather than by the caller writing the model first: a write to the model is only
    // readable back on the next tick, so a caller doing it by hand takes its baseline from the
    // payload as it was before the write, and the seeding then counts as the first edit.
    initial: (): TState => {
      const current = toState(get(model));
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
  watch(() => form.state, (state) => {
    set(model, toModel(state, get(model)));
  }, { deep: true });

  if (seed) {
    // The dialog saves what it reads off the model, so the opening state has to land there too. It
    // is not readable back on this tick, which is why the sync below skips its immediate run: the
    // state is already the newer of the two, and reading the model now would undo the seeding.
    set(model, toModel(form.state, get(model)));
  }

  if (serverErrors) {
    watchImmediate(serverErrors, (value) => {
      form.setServerErrors(toServerErrors(value));
    }, { deep: true });
  }

  // And an edit made outside the form - a reset, a different row seeded while it stays mounted - is
  // pulled back in.
  //
  // 🔴 The equality guard is what makes this terminate. `toState` answers with a new object every
  // time, so assigning it back unconditionally would count as a change even when nothing moved, and
  // the write-back above would then answer that with a new payload, forever. Comparing first means
  // a pass that found nothing new stops here. `syncRef` handles the same problem by pausing the
  // opposing watcher, but it needs two refs of one type and a sync flush, and these two are neither
  // the same shape nor plain refs.
  watch(model, (value) => {
    const next = toState(value);
    if (!isEqual(next, form.state))
      Object.assign(form.state, next);
  }, { deep: true, immediate: !seed });

  if (stateUpdated) {
    // Immediate, so reopening a dialog that kept its flag from the last edit starts disarmed.
    syncRefs(form.dirty, stateUpdated);
  }

  return form;
}

/**
 * A form whose state belongs to the dialog above it.
 *
 * These forms validate and edit, but never persist: the dialog reads the payload straight off the
 * model when its save button is pressed. That makes the model and the form state two copies of the
 * same data which have to be kept in step, which is the boilerplate this removes.
 *
 * For a form that owns its own state and submits it, use `useForm` directly. For one whose inputs
 * cannot hold the payload as it stands, use `useMappedModelForm`.
 */
export function useModelForm<TState extends object>(
  options: ModelFormOptions<TState>,
): FormApi<TState, UnwrapNestedRefs<TState>> {
  return useMappedModelForm<TState, TState>({
    ...options,
    // Spread over the current payload rather than the state alone: it keeps the result typed as the
    // payload, which the reactive state is not, without an assertion to bridge the two.
    toModel: (state, model): TState => ({ ...model, ...state }),
    toState: (model): TState => ({ ...model }),
  });
}
