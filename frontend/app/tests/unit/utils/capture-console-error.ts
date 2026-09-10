import { type MockInstance, vi } from 'vitest';

/**
 * Silences `console.error` for the current test and returns the spy to assert on.
 *
 * @remarks
 * Code under test that swallows a failure reports it through `console.error`, directly or via
 * `startPromise`. A spec exercising that path therefore prints a stack trace on a passing run,
 * which is noise in CI and hides the traces that do mean something.
 *
 * Asserting on the returned spy is the point: it turns the printed error into the statement the
 * test was making anyway, that the failure was reported rather than silently dropped. Silencing
 * without asserting only hides it.
 *
 * The spy is installed for the calling test alone, so restore it in `afterEach` with
 * `vi.restoreAllMocks()`.
 *
 * @returns the `console.error` spy, with its calls recorded and its output suppressed
 */
export function captureConsoleError(): MockInstance<typeof console.error> {
  return vi.spyOn(console, 'error').mockImplementation(() => {});
}
