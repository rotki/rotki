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

// The full version diff so the asset-update prompt can show local→remote + change count,
// and the user can pick a partial `upToVersion` (advanced).
export type UpdateChanges = AssetVersionUpdate;

export type AssetConflict = AssetUpdateConflictResult;

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
  // Lives only for the duration of one flow (needed to re-authenticate after an
  // asset-update restart) and is dropped the moment we reach `ready`.
  let credentials: UnlockCredentials | undefined;
  // True for a background auto-unlock: a failure (or nothing to resume/log in with)
  // silently returns to the idle form instead of parking in `error`.
  let auto = false;
  let pendingVersion = 0;

  const toPhase = (next: UnlockState): void => set(state, next);
  const fail = (error: UnlockError): void => toPhase({ kind: UnlockPhase.error, error });

  // Manual login/create: credentials come from the form/payload.
  async function start(creds: UnlockCredentials): Promise<void> {
    auto = false;
    credentials = creds;
    await runPipeline();
  }

  // Background auto-unlock: resolve the stored credentials first. Nothing stored ⇒
  // there is nothing to auto-unlock with, so drop back to the idle login form.
  async function startAuto(): Promise<void> {
    auto = true;
    toPhase({ kind: UnlockPhase.resolving });
    const resolved = await steps.resolveCredentials();
    if (!resolved.ok)
      return fail(resolved.error);
    if (!resolved.value.some)
      return reset();

    credentials = resolved.value.value;
    await runPipeline();
  }

  // authenticate (no-op without sessions) → open the WS (so migration progress can
  // stream) → probe whether the backend already has a live session for this user.
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

    // Live session ⇒ resume directly, never touching the asset-update prompt (applying
    // it would restart the backend and kill the session we just re-attached to).
    if (resumable.value)
      return finishUnlock(true);

    // No live session and nothing to log in with (background auto-unlock without a saved
    // password) ⇒ show the form for manual entry instead of a doomed empty-password login.
    if (auto && !creds.password)
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
      // suspend: the UI shows the prompt and calls applyUpdate()/skipUpdate()
      return toPhase({ kind: UnlockPhase.updatePrompt, changes: found.value.value });
    }

    await finishUnlock(false);
  }

  // user accepted the update (optionally resolving conflicts). `version` lets the prompt
  // request a partial update (advanced); conflict re-resolution reuses the pending version.
  async function applyUpdate(resolution?: Resolution, version?: number): Promise<void> {
    if (version !== undefined)
      pendingVersion = version;
    toPhase({ kind: UnlockPhase.applyingUpdate });
    const outcome = await steps.applyUpdate(pendingVersion, resolution);
    if (!outcome.ok)
      return fail(outcome.error);

    if (outcome.value.kind === UpdateOutcomeKind.conflicts)
      // suspend: the UI shows conflicts and calls applyUpdate(resolution)
      return toPhase({ kind: UnlockPhase.conflicts, conflicts: outcome.value.conflicts });

    await restart();
  }

  async function skipUpdate(): Promise<void> {
    await finishUnlock(false);
  }

  // The restart is a phase WITHIN this flow — it never tears the app down to the
  // global "connecting" state. requestRestart hits the (initially no-op) HTTP
  // control endpoint; waitReady polls /ping; then we re-authenticate with the
  // password still held in this closure. An asset update only ever happens on the
  // fresh-login branch, so after the restart we always do a fresh login.
  async function restart(): Promise<void> {
    const creds = credentials;
    if (!creds)
      return fail({ kind: UnlockErrorKind.unknown, message: 'restart without an active flow' });

    toPhase({ kind: UnlockPhase.restarting });
    const result = await pipe(
      steps.requestRestart(),
      flatMap(async () => steps.waitReady()),
      flatMap(async () => steps.authenticate(creds)),
      flatMap(async () => steps.connect()), // the socket dropped with the restart
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
    credentials = undefined;
    auto = false;
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
