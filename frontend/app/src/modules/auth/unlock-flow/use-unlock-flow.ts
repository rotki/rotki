import type { Ref } from 'vue';
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import type { LoginCredentials } from '@/modules/auth/login';
import { type OptionType as Option, pipe, type ResultAsyncType as ResultAsync } from 'plainfp';
import { flatMap } from 'plainfp/result-async';

/**
 * The single source of truth the login/unlock UI renders from. The whole
 * authenticate → asset-update → unlock sequence is one flow with one phase, so
 * the asset-update + restart steps never fall back to the global
 * "disconnected/connecting" UI — they are just phases here.
 */
export const UnlockPhase = {
  idle: 'idle',
  authenticating: 'authenticating',
  connecting: 'connecting',
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
  | { kind: typeof UnlockPhase.authenticating }
  | { kind: typeof UnlockPhase.connecting }
  | { kind: typeof UnlockPhase.checkingUpdate }
  | { kind: typeof UnlockPhase.updatePrompt; changes: UpdateChanges }
  | { kind: typeof UnlockPhase.applyingUpdate }
  | { kind: typeof UnlockPhase.conflicts; conflicts: AssetConflict[] }
  | { kind: typeof UnlockPhase.restarting }
  | { kind: typeof UnlockPhase.unlocking }
  | { kind: typeof UnlockPhase.loadingSession }
  | { kind: typeof UnlockPhase.ready; session: SessionModel }
  | { kind: typeof UnlockPhase.error; error: UnlockError };

/**
 * The fallible steps the flow orchestrates. Injected so the flow is unit-testable
 * in isolation (mock the steps, assert phase transitions). `authenticate` is a
 * no-op when no session key is configured, so it is always safe to run first.
 */
export interface UnlockSteps {
  authenticate: (credentials: UnlockCredentials) => ResultAsync<void, UnlockError>;
  connect: () => ResultAsync<void, UnlockError>;
  checkUpdate: () => ResultAsync<Option<UpdateChanges>, UnlockError>;
  applyUpdate: (upToVersion: number, resolution?: Resolution) => ResultAsync<ApplyOutcome, UnlockError>;
  requestRestart: () => ResultAsync<void, UnlockError>;
  waitReady: () => ResultAsync<void, UnlockError>;
  unlock: (credentials: UnlockCredentials) => ResultAsync<void, UnlockError>;
  loadSession: () => ResultAsync<SessionModel, UnlockError>;
}

export interface UseUnlockFlowReturn {
  state: Readonly<Ref<UnlockState>>;
  start: (credentials: UnlockCredentials) => Promise<void>;
  applyUpdate: (resolution?: Resolution, version?: number) => Promise<void>;
  skipUpdate: () => Promise<void>;
  reset: () => void;
}

export function useUnlockFlow(steps: UnlockSteps): UseUnlockFlowReturn {
  const state = ref<UnlockState>({ kind: UnlockPhase.idle });
  // Lives only for the duration of one flow (needed to re-authenticate after an
  // asset-update restart) and is dropped the moment we reach `ready`.
  let credentials: UnlockCredentials | undefined;
  let pendingVersion = 0;

  const toPhase = (next: UnlockState): void => set(state, next);
  const fail = (error: UnlockError): void => toPhase({ kind: UnlockPhase.error, error });

  // authenticate (no-op without sessions) → open the WS (so migration progress can
  // stream) → look for an asset update
  async function start(creds: UnlockCredentials): Promise<void> {
    credentials = creds;
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

    await finishUnlock();
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
    await finishUnlock();
  }

  // The restart is a phase WITHIN this flow — it never tears the app down to the
  // global "connecting" state. requestRestart hits the (initially no-op) HTTP
  // control endpoint; waitReady polls /ping; then we re-authenticate with the
  // password still held in this closure.
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

    await finishUnlock();
  }

  async function finishUnlock(): Promise<void> {
    const creds = credentials;
    if (!creds)
      return fail({ kind: UnlockErrorKind.unknown, message: 'unlock without an active flow' });

    toPhase({ kind: UnlockPhase.unlocking });
    const result = await pipe(
      steps.unlock(creds),
      flatMap(async () => {
        toPhase({ kind: UnlockPhase.loadingSession });
        return steps.loadSession();
      }),
    );
    if (!result.ok)
      return fail(result.error);

    credentials = undefined; // drop the password once we are in
    toPhase({ kind: UnlockPhase.ready, session: result.value });
  }

  function reset(): void {
    credentials = undefined;
    pendingVersion = 0;
    toPhase({ kind: UnlockPhase.idle });
  }

  return {
    state: computed<UnlockState>(() => get(state)),
    start,
    applyUpdate,
    skipUpdate,
    reset,
  };
}
