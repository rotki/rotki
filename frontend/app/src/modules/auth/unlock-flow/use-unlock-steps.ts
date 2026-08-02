import type { Exchange } from '@/modules/balances/types/exchanges';
import { err, none, ok, type OptionType as Option, type ResultType as Result } from 'plainfp';
import { lastLogin } from '@/modules/auth/account-management';
import { type CreateAccountPayload, IncompleteUpgradeError, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { useSessionSettings } from '@/modules/session/use-session-settings';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { migrateSettingsIfNeeded } from '@/modules/settings/types/frontend-settings-migrations';
import { type SettingsUpdate, UserAccount, UserSettingsModel } from '@/modules/settings/types/user-settings';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { SESSION_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart, isActionable, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';
import { useAssetUpdateSteps } from './use-asset-update-steps';
import { useStoredCredentials } from './use-stored-credentials';
import {
  type SessionModel,
  type UnlockCredentials,
  type UnlockError,
  UnlockErrorKind,
  type UnlockSteps,
} from './use-unlock-flow';

interface LoadedAccount {
  settings: UserSettingsModel;
  exchanges: Exchange[];
  fetchData: boolean;
  username: string;
  /** set by `createUnlock`; suppresses the settings-suggestions dialog for a fresh account */
  newAccount?: boolean;
}

export interface UseUnlockStepsReturn {
  loginSteps: UnlockSteps;
  createSteps: (payload: CreateAccountPayload) => UnlockSteps;
}

/**
 * The session steps of the unlock flow (authenticate/connect/unlock/loadSession),
 * plus the orchestration that assembles login vs account-creation step-sets over
 * the shared asset-update steps. This is a clean rewrite of the old monolithic
 * `useLogin` orchestration — login and create now share one tested machine.
 */
export function useUnlockSteps(): UseUnlockStepsReturn {
  const authStore = useSessionAuthStore();
  const { conflictExist, incompleteUpgradeConflict, logged, shouldFetchData, syncConflict, username } = storeToRefs(authStore);
  const { submitTask } = useNativeTask();
  const { initialize } = useSessionSettings();
  const { authenticate: sessionAuthenticate, checkIfLogged, colibriLogin, createAccount: callCreateAccount, login: callLogin } = useUsersApi();
  const { getRawSettings, setSettings } = useSettingsApi();
  const { getExchanges } = useExchangeApi();
  const { resolveStoredCredentials } = useStoredCredentials();
  const assetSteps = useAssetUpdateSteps();

  // the account produced by `unlock`, consumed by `loadSession` (one flow at a time)
  let loaded: LoadedAccount | undefined;

  async function migrateAndSaveSettings(frontendSettings?: string): Promise<string | undefined> {
    const migrated = migrateSettingsIfNeeded(frontendSettings);
    if (migrated) {
      await setSettings({ frontendSettings: migrated });
      return migrated;
    }
    return frontendSettings;
  }

  // Map conflict/upgrade/credential errors as the old flow did: the store refs still
  // drive the existing dialogs; the flow additionally gets a typed error.
  function toUnlockError(error: unknown): UnlockError {
    if (error instanceof IncompleteUpgradeError) {
      set(incompleteUpgradeConflict, { message: error.message });
      return { kind: UnlockErrorKind.incompleteUpgrade };
    }
    if (error instanceof SyncConflictError) {
      set(syncConflict, { message: error.message, payload: error.payload });
      return { kind: UnlockErrorKind.syncConflict, payload: error.payload };
    }
    return { kind: UnlockErrorKind.unknown, message: getErrorMessage(error) };
  }

  // Clear stale WS upgrade progress before mapping, matching the old catch block.
  function failWith(error: unknown): UnlockError {
    authStore.clearUpgradeMessages();
    return toUnlockError(error);
  }

  // The single throw boundary of the login pipe: any throw becomes a typed `err`,
  // while a step that already returns a typed `err` (e.g. wrong password) passes through.
  async function guarded<T>(step: () => Promise<Result<T, UnlockError>>): Promise<Result<T, UnlockError>> {
    try {
      return await step();
    }
    catch (error: unknown) {
      return err(failWith(error));
    }
  }

  // resume: already logged in server-side and no conflict ⇒ load directly
  async function resumeSession(name: string): Promise<Result<LoadedAccount, UnlockError>> {
    const [rawSettings, exchanges] = await Promise.all([getRawSettings(), getExchanges()]);
    rawSettings.frontendSettings = await migrateAndSaveSettings(rawSettings.frontendSettings);
    return ok({ exchanges, fetchData: true, settings: UserSettingsModel.parse(rawSettings), username: name });
  }

  async function freshLogin(credentials: UnlockCredentials, name: string): Promise<Result<LoadedAccount, UnlockError>> {
    if (!credentials.username)
      return err({ kind: UnlockErrorKind.unknown, message: '' });

    authStore.resetSyncConflict();
    authStore.resetIncompleteUpgradeConflict();
    // Login runs through the orchestrator like any other backend task, but flagged `ephemeral`
    // so it never shows in the task center (it settles before the shell even mounts). The task
    // result rides out on the outcome, and the SyncConflict/IncompleteUpgrade cause rides through
    // on `TaskFailed.cause`.
    const outcome = await submitTask<{ settings: SettingsUpdate; exchanges: Exchange[] }>({
      ephemeral: true,
      id: makeActivityId(ActivityKind.SESSION, ActivityPart.LOGIN),
      kind: ActivityKind.SESSION,
      lane: SESSION_LANE,
      run: async ({ runTask }) => runTask<{ settings: SettingsUpdate; exchanges: Exchange[] }>(
        async () => callLogin(credentials),
      ),
      title: 'login',
    });

    if (!outcome.ok) {
      // An actionable failure carries the original error (the task monitor forwards a
      // SyncConflictError/IncompleteUpgradeError verbatim on `TaskFailed.cause`). Map it through
      // `failWith` so its type survives — a generic Error here would erase it and the
      // sync/upgrade alerts would never show. Cancels/skips fall through to wrong-password.
      if (!outcome.ok && isActionable(outcome.error))
        return err(failWith(outcome.error.cause ?? new Error(outcome.error.message)));
      return err({ kind: UnlockErrorKind.wrongPassword });
    }

    await colibriLogin({ password: credentials.password, username: credentials.username });
    const result = outcome.value;
    result.settings.frontendSettings = await migrateAndSaveSettings(result.settings.frontendSettings);
    const account = UserAccount.parse(result);
    return ok({ exchanges: account.exchanges, fetchData: true, settings: account.settings, username: name });
  }

  // Docker cookie auth: obtain the signed `rotki_session` cookie before the WS opens
  // and the unlock task runs, so both carry it (on_open validates it and the `/tasks`
  // poll is cookie-gated). Also re-run after an asset-update restart to re-mint the
  // cookie with the still-held password. Inert in Electron/dev — the endpoint is a
  // no-op that sets no cookie. A wrong password rejects here (401), mapped to a typed
  // err via `guarded`, before the heavy unlock. Account creation does NOT use this:
  // the cookie rides the create task ack instead (the user does not exist yet).
  const authenticate = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      // No password ⇒ a background/resume attempt relying on an existing cookie, not a
      // fresh login. There is nothing to prove, and posting an empty password would 400
      // on the endpoint's NonEmptyString validation. Skip it: probeSession validates the
      // cookie next, and if it is missing/stale the flow falls back to the login form.
      if (!credentials.password)
        return ok(undefined);

      const name = credentials.username || get<string>(lastLogin);
      await sessionAuthenticate({ password: credentials.password, username: name });
      return ok(undefined);
    });

  // Create never authenticates first (see above); the cookie comes from the task ack.
  const noopAuthenticate = async (): Promise<Result<void, UnlockError>> => ok(undefined);

  const connect = async (): Promise<Result<void, UnlockError>> => {
    useMonitorService().start();
    return ok(undefined);
  };

  // Tear the monitor down when the flow abandons an unlock (error or back to the login
  // form). Stopping disables websocket reconnection, so an optimistically-opened socket
  // that the gate rejected (stale/absent cookie) stops retrying instead of looping.
  const disconnect = (): void => {
    useMonitorService().stop();
  };

  // Create defers the socket: its cookie only exists after the create task ack, so opening
  // the socket here (before that ack) would hand the gate an uncookied handshake and get it
  // closed. createUnlock starts the monitor right after the ack instead. Nothing streams
  // over the socket during create anyway (fresh DB: no upgrade, no migration progress).
  const noopConnect = async (): Promise<Result<void, UnlockError>> => ok(undefined);

  const loadSession = async (): Promise<Result<SessionModel, UnlockError>> => {
    if (!loaded)
      return err({ kind: UnlockErrorKind.unknown, message: 'no unlocked account to load' });

    try {
      await initialize(loaded.settings, loaded.exchanges, loaded.newAccount);
      set(username, loaded.username);
      set(logged, true);
      if (loaded.fetchData)
        set(shouldFetchData, true);
      sigilBus.emit('session:ready');
      const session: SessionModel = { username: loaded.username };
      loaded = undefined;
      return ok(session);
    }
    catch (error: unknown) {
      return err(toUnlockError(error));
    }
  };

  // Resolve the stored credentials for a background auto-unlock (delegated to
  // useStoredCredentials); `none` ⇒ nothing to auto-unlock with, so the flow drops back to
  // the manual login form. `guarded` maps any throw to a typed err.
  const resolveCredentials = async (): Promise<Result<Option<UnlockCredentials>, UnlockError>> =>
    guarded<Option<UnlockCredentials>>(async () => ok(await resolveStoredCredentials()));

  // The "auto-login check": does the backend already hold a live session for this user
  // (and no conflict is pending)? Decided up front so the resume branch skips the
  // asset-update prompt and the fresh-login branch keeps it.
  const probeSession = async (credentials: UnlockCredentials): Promise<Result<boolean, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const alreadyLogged = await checkIfLogged(name);
      return ok(alreadyLogged && !get(conflictExist));
    });

  // Resume an already-live server-side session — no login task, no colibri login.
  const resumeUnlock = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const account = await resumeSession(name);
      if (!account.ok)
        return account;
      loaded = account.value;
      return ok(undefined);
    });

  // Fresh login with credentials (manual or saved-password auto-unlock). Every async op is
  // behind `guarded`, so a throw from any stage is mapped to a typed `err`
  // (single-boundary safety) instead of rejecting the flow.
  const loginUnlock = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const account = await freshLogin(credentials, name);
      if (!account.ok)
        return account;
      loaded = account.value;
      return ok(undefined);
    });

  const createUnlock = (payload: CreateAccountPayload) => async (): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      // Account creation runs through the orchestrator flagged `ephemeral`, same as login, so it
      // never leaves a stale task-center entry once the shell mounts.
      const outcome = await submitTask<UserAccount>({
        ephemeral: true,
        id: makeActivityId(ActivityKind.SESSION, ActivityPart.CREATE),
        kind: ActivityKind.SESSION,
        lane: SESSION_LANE,
        run: async ({ runTask }) => runTask<UserAccount>(
          async () => {
            const pending = await callCreateAccount(payload);
            // The create ack has now set the session cookie and the active sid, so the socket
            // handshake and the gated /tasks poll both carry it. Start the monitor here (create's
            // connect step is a no-op) rather than before the ack, when no cookie exists yet.
            useMonitorService().start();
            return pending;
          },
        ),
        title: 'creating account',
      });
      if (!outcome.ok)
        return err({ kind: UnlockErrorKind.unknown, message: outcome.ok ? '' : outcome.error.message });

      const { exchanges, settings } = UserAccount.parse(outcome.value);
      await colibriLogin({ password: payload.credentials.password, username: payload.credentials.username });
      // Restoring a premium backup is not a fresh account: the pulled database carries the
      // settings (and the applied-suggestions version) of the account it came from, so the
      // recommendations still apply to it.
      const syncDatabase = payload.premiumSetup?.syncDatabase ?? false;
      loaded = {
        exchanges,
        fetchData: syncDatabase,
        newAccount: !syncDatabase,
        settings,
        username: payload.credentials.username,
      };
      return ok(undefined);
    });

  const shared = {
    connect,
    disconnect,
    loadSession,
    requestRestart: assetSteps.requestRestart,
    waitReady: assetSteps.waitReady,
  };

  return {
    createSteps: (payload: CreateAccountPayload): UnlockSteps => ({
      ...shared,
      applyUpdate: assetSteps.applyUpdate,
      authenticate: noopAuthenticate,
      checkUpdate: async () => ok(none), // a fresh account is always current
      connect: noopConnect, // the socket starts post-ack inside createUnlock (cookie-safe)
      login: createUnlock(payload),
      probeSession: async () => ok(false), // a new account is never resumable
      resolveCredentials: async () => ok(none), // create is never a background auto-unlock
      resume: async () => ok(undefined), // never reached for create
    }),
    loginSteps: {
      ...shared,
      applyUpdate: assetSteps.applyUpdate,
      authenticate,
      checkUpdate: assetSteps.checkUpdate,
      login: loginUnlock,
      probeSession,
      resolveCredentials,
      resume: resumeUnlock,
    },
  };
}
