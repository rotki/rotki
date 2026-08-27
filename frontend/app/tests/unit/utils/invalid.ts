/**
 * Types `value` as `T` so a test can pass something `T` forbids.
 *
 * @remarks
 * For exercising a defensive branch: code that guards against a value its own types rule out, such
 * as an unhandled member of a union or an enum value from the wire that the frontend does not know.
 * Those guards matter most on destructive paths, where falling through to a broader default is the
 * difference between deleting one thing and deleting everything, and the type system is exactly
 * what stops a test from reaching them.
 *
 * Reach for this only when the value is *meant* to be invalid. A partial stand-in for a real type
 * is `createMock<T>()` instead, and a value the type genuinely permits needs neither.
 *
 * The single assertion is intentionally contained here, so spec files stay assertion-free.
 *
 * @param value - the deliberately invalid value, unconstrained on purpose
 * @returns `value`, typed as `T`
 */
export function invalid<T>(value: unknown): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the whole point is a value T forbids; contained to this helper
  return value as T;
}
