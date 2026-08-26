import type { Ref, UnwrapNestedRefs } from 'vue';
import { isEqual } from 'es-toolkit';

export interface ModelMirrorOptions<TModel extends object, TState extends object> {
  /** The payload the parent owns, saves, and reseeds. Edits are mirrored back into it. */
  readonly model: Ref<TModel>;
  /** The reactive state the inputs bind to. Already holding `toState(model)`, or a seed of it. */
  readonly state: UnwrapNestedRefs<TState>;
  /**
   * The payload as the inputs need to hold it. Called for every edit made outside the state.
   *
   * It has to be stable: the same payload in must give a deep-equal state out. The mirroring
   * compares the two to decide whether an outside edit is news, and a mapper that invents a fresh
   * value each call - a timestamp, a generated id - reports every pass as a change, so the two
   * directions write to each other without ever settling.
   */
  readonly toState: (model: TModel) => TState;
  /**
   * The state as the payload wants it. Handed the payload currently held as well, so a caller
   * editing part of a larger payload can fold its fields over it and leave the rest alone.
   */
  readonly toModel: (state: UnwrapNestedRefs<TState>, model: TModel) => TModel;
  /**
   * Whether the state was already moved past what the payload says, by a caller that decides part
   * of its opening value. It is then written to the payload instead of read from it, because the
   * state is the newer of the two and reading the payload now would undo the choice.
   */
  readonly seeded?: boolean;
}

/**
 * Two shapes of the same data, kept in step.
 *
 * A component that edits a payload its parent owns cannot always bind to the payload as it stands:
 * a text input needs a string where the api admits null, a key is masked while it is not being
 * edited, one field is edited through two controls. Left to each field that gap becomes a writable
 * computed per input, wrapping and unwrapping the same value on every keystroke, and the shape the
 * inputs actually want is never written down anywhere.
 *
 * Written down here it is two pure functions with the whole payload in view, testable on their own,
 * and the inputs bind to plain reactive state.
 *
 * This is the half of `useMappedModelForm` that has nothing to do with validation, for a component
 * that maps but does not validate. One that does both wants that instead.
 *
 * The two watchers face each other, and the equality guard on the inbound one is what makes the
 * pair terminate: `toState` answers with a new object every time, so assigning it back
 * unconditionally counts as a change even when nothing moved, and the outbound watcher answers that
 * with a new payload, forever. `syncRef` solves the same problem by pausing the opposing watcher,
 * but it needs two refs of one type and a sync flush, and these two are neither.
 */
export function useModelMirror<TModel extends object, TState extends object>(
  options: ModelMirrorOptions<TModel, TState>,
): void {
  const { model, seeded = false, state, toModel, toState } = options;

  // Every edit is written back, because the parent saves what it reads off the payload, not what
  // the state holds.
  watch(() => state, (value) => {
    set(model, toModel(value, get(model)));
  }, { deep: true });

  if (seeded) {
    // The parent saves what it reads off the payload, so the opening state has to land there too.
    set(model, toModel(state, get(model)));
  }

  watch(model, (value) => {
    const next = toState(value);
    if (!isEqual(next, state))
      Object.assign(state, next);
  }, { deep: true, immediate: !seeded });
}
