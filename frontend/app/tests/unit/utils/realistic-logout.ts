import flushPromises from 'flush-promises';
import { vi } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { beginSession, endSession, onSessionEnd, scheduleSessionClear, sessionWorkSignal } from '@/modules/core/session/session-lifecycle';

/**
 * The shortest time the app stays logged out: `logout()` waits this long (`DOM_TEARDOWN_MS` in
 * `use-logout.ts`) before the login form can come back, and a person still has to log in after.
 */
const LOGGED_OUT_FLOOR_MS = 1500;

export interface SessionRequest<T> {
  readonly promise: Promise<T>;
  readonly resolve: (value: T) => void;
}

/**
 * A stand-in for a session-bound request sent in the live session.
 *
 * @remarks
 * Resolves when told to, and rejects with {@link RequestCancelledError} the moment the session it
 * was sent in ends, as the request queue does through the session's signal. A plain deferred never
 * rejects, so a spec built on one lets work resume in the next session that the app would have
 * cancelled at logout.
 *
 * @returns the pending request and its resolver
 */
export function sessionRequest<T>(): SessionRequest<T> {
  const signal = sessionWorkSignal();
  let resolve: (value: T) => void = () => {};
  const promise = new Promise<T>((settle, reject) => {
    resolve = settle;
    signal.addEventListener('abort', () => reject(new RequestCancelledError('session ended')), { once: true });
  });
  return { promise, resolve };
}

/**
 * Logs out and back in with the ordering the app guarantees.
 *
 * @remarks
 * Ends the session, which runs every `onSessionEnd` listener registered so far, plus `endWork` for
 * the resets the app's session cleaner (`use-session-state-cleaner.ts`) makes that a spec has not
 * wired up. Then it stays logged out for {@link LOGGED_OUT_FLOOR_MS}, so every continuation the
 * logout released runs with no session live, and only then begins the next session.
 *
 * With real timers only microtasks and one macrotask run in the gap; a spec that depends on a timer
 * crossing the logout has to use fake timers.
 *
 * @param endWork - resets to run as part of the session end, in order
 */
export async function logoutThenLogin(endWork: readonly (() => void)[] = []): Promise<void> {
  const remove = onSessionEnd('spec-session-work', () => {
    for (const reset of endWork)
      reset();
  });
  endSession();
  remove();
  scheduleSessionClear();

  if (vi.isFakeTimers()) {
    await vi.advanceTimersByTimeAsync(LOGGED_OUT_FLOOR_MS);
  }
  else {
    await flushPromises();
    await new Promise<void>((resolve) => {
      setTimeout(resolve, 0);
    });
    await flushPromises();
  }

  beginSession();
}
