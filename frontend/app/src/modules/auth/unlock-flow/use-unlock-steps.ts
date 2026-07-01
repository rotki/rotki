import type { Exchange } from '@/modules/balances/types/exchanges';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { err, none, ok, type OptionType as Option, type ResultType as Result } from 'plainfp';
import { lastLogin } from '@/modules/auth/account-management';
import { type CreateAccountPayload, IncompleteUpgradeError, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useSessionSettings } from '@/modules/session/use-session-settings';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { migrateSettingsIfNeeded } from '@/modules/settings/types/frontend-settings-migrations';
import { type SettingsUpdate, UserAccount, UserSettingsModel } from '@/modules/settings/types/user-settings';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
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
  const { runTask } = useTaskHandler();
  const { initialize } = useSessionSettings();
  const { checkIfLogged, colibriLogin, createAccount: callCreateAccount, login: callLogin } = useUsersApi();
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
    const outcome = await runTask<{ settings: SettingsUpdate; exchanges: Exchange[] }, TaskMeta>(
      async () => callLogin(credentials),
      { meta: { title: 'login in' }, type: TaskType.LOGIN },
    );

    if (!outcome.success) {
      // An actionable failure carries the original error (the task monitor forwards a
      // SyncConflictError/IncompleteUpgradeError verbatim). Map it through `failWith` so its
      // type survives — throwing a generic Error here would erase it and the sync/upgrade
      // alerts would never show.
      if (isActionableFailure(outcome))
        return err(failWith(outcome.error ?? new Error(outcome.message)));
      return err({ kind: UnlockErrorKind.wrongPassword });
    }

    await colibriLogin({ password: credentials.password, username: credentials.username });
    outcome.result.settings.frontendSettings = await migrateAndSaveSettings(outcome.result.settings.frontendSettings);
    const account = UserAccount.parse(outcome.result);
    return ok({ exchanges: account.exchanges, fetchData: true, settings: account.settings, username: name });
  }

  const authenticate = async (): Promise<Result<void, UnlockError>> => ok(undefined);

  const connect = async (): Promise<Result<void, UnlockError>> => {
    useMonitorService().start();
    return ok(undefined);
  };

  const loadSession = async (): Promise<Result<SessionModel, UnlockError>> => {
    if (!loaded)
      return err({ kind: UnlockErrorKind.unknown, message: 'no unlocked account to load' });

    try {
      await initialize(loaded.settings, loaded.exchanges);
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
      const outcome = await runTask<UserAccount, TaskMeta>(
        async () => callCreateAccount(payload),
        { meta: { title: 'creating account' }, type: TaskType.CREATE_ACCOUNT },
      );
      if (!outcome.success)
        return err({ kind: UnlockErrorKind.unknown, message: outcome.message });

      const { exchanges, settings } = UserAccount.parse(outcome.result);
      await colibriLogin({ password: payload.credentials.password, username: payload.credentials.username });
      loaded = {
        exchanges,
        fetchData: payload.premiumSetup?.syncDatabase ?? false,
        settings,
        username: payload.credentials.username,
      };
      return ok(undefined);
    });

  const shared = {
    authenticate,
    connect,
    loadSession,
    requestRestart: assetSteps.requestRestart,
    waitReady: assetSteps.waitReady,
  };

  return {
    createSteps: (payload: CreateAccountPayload): UnlockSteps => ({
      ...shared,
      applyUpdate: assetSteps.applyUpdate,
      checkUpdate: async () => ok(none), // a fresh account is always current
      login: createUnlock(payload),
      probeSession: async () => ok(false), // a new account is never resumable
      resolveCredentials: async () => ok(none), // create is never a background auto-unlock
      resume: async () => ok(undefined), // never reached for create
    }),
    loginSteps: {
      ...shared,
      applyUpdate: assetSteps.applyUpdate,
      checkUpdate: assetSteps.checkUpdate,
      login: loginUnlock,
      probeSession,
      resolveCredentials,
      resume: resumeUnlock,
    },
  };
}
