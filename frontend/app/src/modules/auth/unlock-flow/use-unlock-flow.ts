import type { Ref } from 'vue';
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import type { LoginCredentials } from '@/modules/auth/login';
import { type OptionType as Option, pipe, type ResultAsyncType as ResultAsync } from 'plainfp';
import { flatMap } from 'plainfp/result-async';

/**
 * The single source of truth the login/unlock UI renders from. The whole
 * resolve → authenticate → probe → (resume | asset-update + fresh-login) sequence
 * is one flow with one phase, so a background auto-unlock and a manual login share
 * the same machine and can never race each other.
 *
 * @remarks
 * `updatePrompt` and `conflicts` suspend the flow: entering either is the end of the current call,
 * and nothing advances until the UI answers through `applyUpdate()` or `skipUpdate()`. Every other
 * phase is passed through on the way somewhere.
 */
export const UnlockPhase = {
  idle: 'idle',
  resolving: 'resolving',
  authenticating: 'authenticating',
  connecting: 'connecting',
  probing: 'probing',
  checkingUpdate: 'checking-update',
  updatePrompt: 'update-prompt',
  applyingUpdate: 'applying-update',
  conflicts: 'conflicts',
  restarting: 'restarting',
  unlocking: 'unlocking',
  loadingSession: 'loading-session',
  ready: 'ready',
  error: 'error',
} as const;

export const UnlockErrorKind = {
  wrongPassword: 'wrong-password',
  syncConflict: 'sync-conflict',
  incompleteUpgrade: 'incomplete-upgrade',
  updateFailed: 'update-failed',
  restartFailed: 'restart-failed',
  unknown: 'unknown',
} as const;

export const UpdateOutcomeKind = {
  done: 'done',
  conflicts: 'conflicts',
} as const;

/**
 * Flow-local types; the injected steps adapt the real api/store calls to these. The
 * credentials are the real `LoginCredentials` so `syncApproval`/`resumeFromBackup` ride
 * through to the login task (conflict "proceed" / "resume from backup") and survive the
 * re-authenticate after an asset-update restart.
 */
export type UnlockCredentials = LoginCredentials;

/**
 * Names the asset version diff the update prompt renders: local and remote versions, the change
 * count, and the `upToVersion` a partial update stops at.
 */
export type UpdateChanges = AssetVersionUpdate;

type AssetConflict = AssetUpdateConflictResult;

export type Resolution = ConflictResolution;

export type SessionModel = Record<string, unknown>;

export type UnlockError =
  | { kind: typeof UnlockErrorKind.wrongPassword }
  | { kind: typeof UnlockErrorKind.syncConflict; payload: unknown }
  | { kind: typeof UnlockErrorKind.incompleteUpgrade }
  | { kind: typeof UnlockErrorKind.updateFailed; message: string }
  | { kind: typeof UnlockErrorKind.restartFailed }
  | { kind: typeof UnlockErrorKind.unknown; message: string };

export type ApplyOutcome =
  | { kind: typeof UpdateOutcomeKind.done }
  | { kind: typeof UpdateOutcomeKind.conflicts; conflicts: AssetConflict[] };

export type UnlockState =
  | { kind: typeof UnlockPhase.idle }
  | { kind: typeof UnlockPhase.resolving }
  | { kind: typeof UnlockPhase.authenticating }
  | { kind: typeof UnlockPhase.connecting }
  | { kind: typeof UnlockPhase.probing }
  | { kind: typeof UnlockPhase.checkingUpdate }
  | { kind: typeof UnlockPhase.updatePrompt; changes: UpdateChanges }
  | { kind: typeof UnlockPhase.applyingUpdate }
  | { kind: typeof UnlockPhase.conflicts; conflicts: AssetConflict[] }
  | { kind: typeof UnlockPhase.restarting }
  | { kind: typeof UnlockPhase.unlocking }
  | { kind: typeof UnlockPhase.loadingSession }
  | { kind: typeof UnlockPhase.ready; session: SessionModel; resumed: boolean }
  | { kind: typeof UnlockPhase.error; error: UnlockError };

/**
 * The fallible steps the flow orchestrates. Injected so the flow is unit-testable
 * in isolation (mock the steps, assert phase transitions). `authenticate` is a
 * no-op when no session key is configured, so it is always safe to run first.
 *
 * `probeSession` decides resume-vs-fresh-login up front (part of the flow), so the
 * resume branch structurally skips `checkUpdate` and the fresh-login branch keeps it.
 * `resolveCredentials` gathers the stored credentials for a background auto-unlock.
 */
export interface UnlockSteps {
  resolveCredentials: () => ResultAsync<Option<UnlockCredentials>, UnlockError>;
  authenticate: (credentials: UnlockCredentials) => ResultAsync<void, UnlockError>;
  connect: () => ResultAsync<void, UnlockError>;
  disconnect: () => void;
  probeSession: (credentials: UnlockCredentials) => ResultAsync<boolean, UnlockError>;
  checkUpdate: () => ResultAsync<Option<UpdateChanges>, UnlockError>;
  applyUpdate: (upToVersion: number, resolution?: Resolution) => ResultAsync<ApplyOutcome, UnlockError>;
  requestRestart: () => ResultAsync<void, UnlockError>;
  waitReady: () => ResultAsync<void, UnlockError>;
  resume: (credentials: UnlockCredentials) => ResultAsync<void, UnlockError>;
  login: (credentials: UnlockCredentials) => ResultAsync<void, UnlockError>;
  loadSession: () => ResultAsync<SessionModel, UnlockError>;
}

export interface UseUnlockFlowReturn {
  state: Readonly<Ref<UnlockState>>;
  start: (credentials: UnlockCredentials) => Promise<void>;
  startAuto: () => Promise<void>;
  applyUpdate: (resolution?: Resolution, version?: number) => Promise<void>;
  skipUpdate: () => Promise<void>;
  reset: () => void;
}

export function useUnlockFlow(steps: UnlockSteps): UseUnlockFlowReturn {
  const state = ref<UnlockState>({ kind: UnlockPhase.idle });
  /** Held for one flow only: the restart path re-authenticates with it, and `ready` drops it. */
  let credentials: UnlockCredentials | undefined;
  /** A background auto-unlock, whose failures return to the idle form instead of parking in `error`. */
  let startedInTheBackground = false;
  let pendingVersion = 0;

  const toPhase = (next: UnlockState): void => set(state, next);
  /**
   * Moves the flow into its error phase, tearing the websocket down on the way out.
   *
   * @remarks
   * The pipeline opens the socket before it knows the session is valid, so every exit without a
   * live session has to disconnect: an invalid session makes that socket 403 and reconnect forever.
   */
  const fail = (error: UnlockError): void => {
    steps.disconnect();
    toPhase({ kind: UnlockPhase.error, error });
  };

  /**
   * Runs the flow for a manual login or account creation.
   *
   * @remarks
   * Failures park in the error phase for the form to render, unlike {@link startAuto}.
   */
  async function start(creds: UnlockCredentials): Promise<void> {
    startedInTheBackground = false;
    credentials = creds;
    await runPipeline();
  }

  /**
   * Runs the flow in the background from the stored credentials.
   *
   * @remarks
   * With nothing stored, or with a stored profile that carries no password, the flow returns to
   * the idle login form rather than parking in the error phase.
   */
  async function startAuto(): Promise<void> {
    startedInTheBackground = true;
    toPhase({ kind: UnlockPhase.resolving });
    const resolved = await steps.resolveCredentials();
    if (!resolved.ok)
      return fail(resolved.error);
    if (!resolved.value.some)
      return reset();

    credentials = resolved.value.value;
    await runPipeline();
  }

  /**
   * Authenticates, opens the websocket, then probes whether the backend already holds a live
   * session for these credentials.
   *
   * @remarks
   * The socket opens before the probe so backend migration progress can stream while it runs.
   * A live session resumes straight away and never reaches the asset-update prompt: applying an
   * update restarts the backend, which would kill the session just re-attached to.
   */
  async function runPipeline(): Promise<void> {
    const creds = credentials;
    if (!creds)
      return fail({ kind: UnlockErrorKind.unknown, message: 'unlock without an active flow' });

    toPhase({ kind: UnlockPhase.authenticating });
    const connected = await pipe(
      steps.authenticate(creds),
      flatMap(async () => {
        toPhase({ kind: UnlockPhase.connecting });
        return steps.connect();
      }),
    );
    if (!connected.ok)
      return fail(connected.error);

    toPhase({ kind: UnlockPhase.probing });
    const resumable = await steps.probeSession(creds);
    if (!resumable.ok)
      return fail(resumable.error);

    if (resumable.value)
      return finishUnlock(true);

    const wouldBeADoomedEmptyPasswordLogin = startedInTheBackground && !creds.password;
    if (wouldBeADoomedEmptyPasswordLogin)
      return reset();

    await checkUpdate();
  }

  async function checkUpdate(): Promise<void> {
    toPhase({ kind: UnlockPhase.checkingUpdate });
    const found = await steps.checkUpdate();
    if (!found.ok)
      return fail(found.error);

    if (found.value.some) {
      pendingVersion = found.value.value.upToVersion;
      return toPhase({ kind: UnlockPhase.updatePrompt, changes: found.value.value });
    }

    await finishUnlock(false);
  }

  /**
   * Applies the pending asset update, then restarts the backend or suspends on conflicts.
   *
   * @remarks
   * Conflict re-resolution calls this a second time with only a resolution, reusing the version
   * the first call recorded.
   *
   * @param resolution - how to settle the conflicts a previous call reported
   * @param version - stops the update short at this version; omitted, the whole pending diff applies
   */
  async function applyUpdate(resolution?: Resolution, version?: number): Promise<void> {
    if (version !== undefined)
      pendingVersion = version;
    toPhase({ kind: UnlockPhase.applyingUpdate });
    const outcome = await steps.applyUpdate(pendingVersion, resolution);
    if (!outcome.ok)
      return fail(outcome.error);

    if (outcome.value.kind === UpdateOutcomeKind.conflicts)
      return toPhase({ kind: UnlockPhase.conflicts, conflicts: outcome.value.conflicts });

    await restart();
  }

  async function skipUpdate(): Promise<void> {
    await finishUnlock(false);
  }

  /**
   * Restarts the backend, re-authenticates against it, and finishes with a fresh login.
   *
   * @remarks
   * The restart is a phase of this flow, not a drop back to the app-wide connecting state:
   * `waitReady` polls until the backend answers, the password still held in this closure
   * re-authenticates, and the socket is reopened because it dropped with the restart. An asset
   * update only ever runs on the fresh-login branch, so a restart never ends in a resume.
   */
  async function restart(): Promise<void> {
    const creds = credentials;
    if (!creds)
      return fail({ kind: UnlockErrorKind.unknown, message: 'restart without an active flow' });

    toPhase({ kind: UnlockPhase.restarting });
    const result = await pipe(
      steps.requestRestart(),
      flatMap(async () => steps.waitReady()),
      flatMap(async () => steps.authenticate(creds)),
      flatMap(async () => steps.connect()),
    );
    if (!result.ok)
      return fail(result.error);

    await finishUnlock(false);
  }

  async function finishUnlock(resumed: boolean): Promise<void> {
    const creds = credentials;
    if (!creds)
      return fail({ kind: UnlockErrorKind.unknown, message: 'unlock without an active flow' });

    toPhase({ kind: UnlockPhase.unlocking });
    const result = await pipe(
      resumed ? steps.resume(creds) : steps.login(creds),
      flatMap(async () => {
        toPhase({ kind: UnlockPhase.loadingSession });
        return steps.loadSession();
      }),
    );
    if (!result.ok)
      return fail(result.error);

    credentials = undefined; // drop the password once we are in
    toPhase({ kind: UnlockPhase.ready, session: result.value, resumed });
  }

  function reset(): void {
    steps.disconnect();
    credentials = undefined;
    startedInTheBackground = false;
    pendingVersion = 0;
    toPhase({ kind: UnlockPhase.idle });
  }

  return {
    state: computed<UnlockState>(() => get(state)),
    start,
    startAuto,
    applyUpdate,
    skipUpdate,
    reset,
  };
}
