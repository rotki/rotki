/**
 * A promise that never resolves and never rejects.
 *
 * @remarks
 * Stands in for work still in flight, so a test can assert what the code under test does *while*
 * it waits: a spinner that stays up, a slot the queue keeps held, a timeout that fires on its own,
 * a later answer that must not be overwritten by an earlier one. A resolved promise settles on the
 * next microtask and closes that window before the assertion can see it.
 *
 * Nothing ever settles this, so never `await` it outside a timeout or a `Promise.race`.
 *
 * @returns a promise stuck in the pending state for the lifetime of the test
 */
export async function neverSettles<T = never>(): Promise<T> {
  return new Promise<T>(() => {});
}
