/**
 * One user session, from the start of an unlock to the start of the logout that ends it.
 *
 * @remarks
 * Work that belongs to a session must not outlive it. Requests and task submits check
 * {@link hasLiveSession} when they are made, so code still running after the session ended (an
 * async body resuming once logout settled what it awaited, a watcher fired by the store reset)
 * cannot reach the backend, which keeps serving the old user until the logout call lands.
 */
interface SessionState {
  /** Aborted when the session ends; `undefined` while no session is live. */
  live: AbortController | undefined;
  readonly endListeners: Map<string, () => void>;
}

const SESSION_STATE_KEY = Symbol.for('rotki.session-lifecycle');

/**
 * The one session state, kept on `globalThis` rather than in this module.
 *
 * @remarks
 * A module can be evaluated more than once: by a Vite hot update in development, and by
 * `vi.resetModules()` in specs. A second copy holding its own state would report no live session
 * while the first still holds one, and every request through it would be refused.
 */
function sessionState(): SessionState {
  const existing: unknown = Reflect.get(globalThis, SESSION_STATE_KEY);
  if (isSessionState(existing))
    return existing;

  const created: SessionState = { endListeners: new Map(), live: undefined };
  Reflect.set(globalThis, SESSION_STATE_KEY, created);
  return created;
}

function isSessionState(value: unknown): value is SessionState {
  return typeof value === 'object' && value !== null && 'endListeners' in value && value.endListeners instanceof Map;
}

/**
 * Starts a session, ending any session still live.
 *
 * @remarks
 * Called when an unlock starts, not when it succeeds: the unlock's own requests and tasks
 * belong to the session it creates. A failed unlock ends it again.
 */
export function beginSession(): void {
  endSession();
  sessionState().live = new AbortController();
}

/**
 * Ends the live session, if there is one. Idempotent.
 *
 * @remarks
 * Synchronous on purpose: it is the first thing a logout does, before anything awaits, so
 * nothing the session started can send another request in the gap.
 */
export function endSession(): void {
  const state = sessionState();
  const ending = state.live;
  if (!ending)
    return;

  state.live = undefined;
  ending.abort();
  for (const listener of state.endListeners.values())
    listener();
}

export function hasLiveSession(): boolean {
  return sessionState().live !== undefined;
}

/**
 * The live session's abort signal, which aborts when it ends.
 *
 * @returns `undefined` while no session is live
 */
export function liveSessionSignal(): AbortSignal | undefined {
  return sessionState().live?.signal;
}

/**
 * Runs `listener` every time a session ends.
 *
 * @remarks
 * Registering under a key already in use replaces that listener. A module evaluated again (a hot
 * update, a spec's `vi.resetModules()`) registers again, and adding instead would keep every
 * earlier copy alive and running.
 *
 * @param key - names the registration, one per module that listens
 * @param listener - runs after the session has ended
 * @returns a function that removes the listener
 */
export function onSessionEnd(key: string, listener: () => void): () => void {
  const { endListeners } = sessionState();
  endListeners.set(key, listener);
  return () => endListeners.delete(key);
}
