import type { MaybeRefOrGetter, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, noSubmit, useForm } from '@/modules/core/form/use-form';
import { type ModelMirrorOptions, useModelMirror } from '@/modules/core/form/use-model-mirror';

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
> extends
  SharedModelFormOptions<TState>,
  // The two mappers and the payload are the mirror's, described there.
  Pick<ModelMirrorOptions<TModel, TState>, 'model' | 'toModel' | 'toState'> {}

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
 *
 * @param options - `seed` shapes the opening state, and is applied here rather than by writing the
 * model first: a model write only reads back on the next tick, so a caller doing it by hand takes
 * its baseline from the payload as it was before the write and the seeding counts as the first edit
 */
export function useMappedModelForm<TModel extends object, TState extends object>(
  options: MappedModelFormOptions<TModel, TState>,
): FormApi<TState, UnwrapNestedRefs<TState>> {
  const { model, schema, seed, serverErrors, stateUpdated, toModel, toState, transientKeys } = options;

  const form = useForm<TState, UnwrapNestedRefs<TState>>({
    initial: (): TState => {
      const current = toState(get(model));
      return seed ? seed(current) : current;
    },
    schema,
    submit: noSubmit,
    transform: (state): UnwrapNestedRefs<TState> => ({ ...state }),
    transientKeys,
  });

  useModelMirror<TModel, TState>({
    model,
    seeded: Boolean(seed),
    state: form.state,
    toModel,
    toState,
  });

  if (serverErrors) {
    watchImmediate(serverErrors, (value) => {
      form.setServerErrors(toServerErrors(value));
    }, { deep: true });
  }

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
    toModel: (state, model): TState => ({ ...model, ...state }),
    toState: (model): TState => ({ ...model }),
  });
}
