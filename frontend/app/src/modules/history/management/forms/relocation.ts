/** The fields a move to another location may carry over, or empty when the new kind has none. */
const CARRIED_FIELDS = ['address', 'txRef'] as const;

interface RelocatableState {
  kind: string;
  address: string;
  txRef: string;
}

interface RelocationHooks {
  /** Forgets the transaction lookup, which belongs to the kind the event had before. */
  resetLookup: () => void;
  untouch: (path: string) => void;
}

/**
 * Applies a relocated form state to the live one.
 *
 * @remarks
 * A change of kind resets the transaction lookup. A reference or address the move emptied counts as
 * untouched again, so it is not flagged as missing before the user has had a chance to fill it in.
 *
 * @param state - the live, reactive form state, updated in place
 * @param relocated - the state the location implies, from the form's own relocate function
 * @param hooks - what to reset alongside the state
 */
export function applyRelocation<S extends RelocatableState>(state: S, relocated: S, hooks: RelocationHooks): void {
  if (relocated.kind !== state.kind)
    hooks.resetLookup();
  const emptied = CARRIED_FIELDS.filter(path => state[path] && !relocated[path]);
  Object.assign(state, relocated);
  emptied.forEach(path => hooks.untouch(path));
}
