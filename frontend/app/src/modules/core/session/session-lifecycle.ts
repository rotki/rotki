/**
 * One user session, from the start of an unlock to the start of the logout that ends it.
 *
 * @remarks
 * Work that belongs to a session must not outlive it. Requests and task submits check
 * {@link hasLiveSession} when they are made, so code still running after the session ended (an
 * async body resuming once logout settled what it awaited, a watcher fired by the store reset)
 * cannot reach the backend, which keeps serving the old user until the logout call lands.
 *
 * A session ends in two phases. {@link onSessionEnd} listeners stop its work at once: they cancel
 * requests and settle what callers await. Those callers resume afterwards, in microtasks, and
 * whatever they write lands in the session's state. {@link onSessionCleared} listeners clear that
 * state once the app has logged out, one task after {@link scheduleSessionClear}, so every resumed
 * caller has run and nothing written late outlives it. A failed unlock ends its session without
 * ever logging in, so it clears nothing: what it leaves, such as a sync conflict, is for the login
 * screen to show.
 */
interface SessionState {
  /** Aborted when the session ends; `undefined` while no session is live. */
  live: AbortController | undefined;
  readonly endListeners: Map<string, () => void>;
  readonly clearListeners: Map<string, () => void>;
  readonly pendingWrites: Map<string, () => Promise<void>>;
  /** The clear phase scheduled by a logout and not run yet. */
  pendingClear: ReturnType<typeof setTimeout> | undefined;
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

  const created: SessionState = {
    clearListeners: new Map(),
    endListeners: new Map(),
    live: undefined,
    pendingClear: undefined,
    pendingWrites: new Map(),
  };
  Reflect.set(globalThis, SESSION_STATE_KEY, created);
  return created;
}

function isSessionState(value: unknown): value is SessionState {
  return typeof value === 'object'
    && value !== null
    && 'endListeners' in value
    && value.endListeners instanceof Map
    && 'clearListeners' in value
    && value.clearListeners instanceof Map
    && 'pendingWrites' in value
    && value.pendingWrites instanceof Map;
}

/** Runs the clear phase a logout scheduled, if it has not run yet. */
function clearEndedSession(): void {
  const state = sessionState();
  if (state.pendingClear === undefined)
    return;

  clearTimeout(state.pendingClear);
  state.pendingClear = undefined;
  for (const listener of state.clearListeners.values())
    listener();
}

/**
 * Starts a session, ending any session still live.
 *
 * @remarks
 * Called when an unlock starts, not when it succeeds: the unlock's own requests and tasks
 * belong to the session it creates. A failed unlock ends it again. A clear phase still pending
 * runs first, so it can never run inside the new session.
 */
export function beginSession(): void {
  endSession();
  clearEndedSession();
  sessionState().live = new AbortController();
}

/**
 * Ends the live session, if there is one. Idempotent.
 *
 * @remarks
 * Synchronous on purpose: a logout calls it as soon as the user's pending writes have landed,
 * before anything else awaits, so nothing the session started can send another request in the
 * gap.
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

/**
 * Schedules the clear phase one task from now, unless one is already pending.
 *
 * @remarks
 * Called once the app has logged out, after its session ended. Clearing from the logout rather
 * than from the end of the session keeps the state the logout itself still reads, such as the
 * username it logs out, until it no longer needs it.
 */
export function scheduleSessionClear(): void {
  sessionState().pendingClear ??= setTimeout(clearEndedSession, 0);
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
 * Captures the live session, for work that has to know later whether that same session is live.
 *
 * @remarks
 * Requests and task submits only check that *a* session is live. Work whose await is not a
 * session-bound request, such as a timer, can span a logout and the next login, and would then act
 * in a session that never started it. Capture the session when the work starts and check the
 * returned predicate after each such await.
 *
 * @returns a predicate that is true while the session live at capture is still live; always false
 * when none was
 */
export function captureSession(): () => boolean {
  const signal = liveSessionSignal();
  return () => signal !== undefined && !signal.aborted;
}

/**
 * Runs every write still waiting to persist the user's input, and resolves once they have landed.
 *
 * @remarks
 * Called by a logout before it ends the session: a debounced write that fired afterwards would be
 * refused, and the change the user made just before logging out would be lost.
 */
export async function finishPendingWrites(): Promise<void> {
  await Promise.allSettled(Array.from(sessionState().pendingWrites.values(), async write => write()));
}

/**
 * Registers `write` to run before the session ends, for input that persists on a delay.
 *
 * @param key - names the registration, one per writer
 * @param write - persists what is pending; a no-op when nothing is
 * @returns a function that removes the registration
 */
export function onPendingWrite(key: string, write: () => Promise<void>): () => void {
  const { pendingWrites } = sessionState();
  pendingWrites.set(key, write);
  return () => pendingWrites.delete(key);
}

/**
 * Registers `listener` under `key` in `listeners`.
 *
 * @remarks
 * Registering under a key already in use replaces that listener. A module evaluated again (a hot
 * update, a spec's `vi.resetModules()`) or a shared composable created again registers again, and
 * adding instead would keep every earlier copy alive and running.
 */
function register(listeners: Map<string, () => void>, key: string, listener: () => void): () => void {
  listeners.set(key, listener);
  return () => listeners.delete(key);
}

/**
 * Runs `listener` the moment a session ends, to stop its work: cancel what it sent, settle what
 * its callers await.
 *
 * @param key - names the registration, one per module that listens
 * @param listener - runs synchronously when the session ends
 * @returns a function that removes the listener
 */
export function onSessionEnd(key: string, listener: () => void): () => void {
  return register(sessionState().endListeners, key, listener);
}

/**
 * Runs `listener` once an ended session's callers have resumed, to clear the state it leaves.
 *
 * @param key - names the registration, one per module that listens
 * @param listener - runs one task after the session ended, or when the next one begins if sooner
 * @returns a function that removes the listener
 */
export function onSessionCleared(key: string, listener: () => void): () => void {
  return register(sessionState().clearListeners, key, listener);
}
