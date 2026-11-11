import type { ClearedValue } from '@rotki/ui-library';

/**
 * The value a wrapper around a clearable select hands its parent when the field is cleared.
 *
 * @remarks
 * A wrapper generic over `TClear` and `TClearable` types its update as `TValue | ClearedValue<…>`,
 * the way the wrapped `RuiAutoComplete` does. The checker cannot narrow `ClearedValue` while those
 * parameters are unresolved, so it cannot see that `valueOnClear` is that type; this is the one
 * place the wrappers assert it. It holds because a field only clears when `clearable` is on, and
 * then `ClearedValue` is `TClear`, which `valueOnClear` is, `undefined` standing in for the default.
 *
 * @param valueOnClear - what the caller asked clearing to write; `undefined` when not given
 */
export function toClearedValue<TValue, TClear, TClearable extends boolean>(
  valueOnClear: TClear | undefined,
): ClearedValue<TValue, TClear, TClearable> {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the checker cannot narrow ClearedValue over unresolved parameters; see the remarks above
  return valueOnClear as ClearedValue<TValue, TClear, TClearable>;
}
