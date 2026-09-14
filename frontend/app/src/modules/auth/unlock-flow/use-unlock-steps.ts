import type { Exchange } from '@/modules/balances/types/exchanges';
import { err, none, ok, type OptionType as Option, type ResultType as Result } from 'plainfp';
import { lastLogin } from '@/modules/auth/account-management';
import { type CreateAccountPayload, IncompleteUpgradeError, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { useSessionSettings } from '@/modules/session/use-session-settings';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { collectMigrationPatch } from '@/modules/settings/types/frontend-settings-migrations';
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
  /** Set by `createUnlock`. Suppresses the settings-suggestions dialog for a fresh account. */
  newAccount?: boolean;
}

export interface UseUnlockStepsReturn {
  loginSteps: UnlockSteps;
  createSteps: (payload: CreateAccountPayload) => UnlockSteps;
}

/**
 * Builds the session steps of the unlock flow: authenticate, connect, unlock, loadSession.
 *
 * @remarks
 * Also assembles the login and account-creation step sets over the shared asset-update steps, so
 * both drive the same machine. Add a step here rather than branching at a call site.
 */
export function useUnlockSteps(): UseUnlockStepsReturn {
  const authStore = useSessionAuthStore();
  const { conflictExist, incompleteUpgradeConflict, logged, shouldFetchData, syncConflict, username } = storeToRefs(authStore);
  const { submitTask } = useNativeTask();
  const { initialize } = useSessionSettings();
  const { authenticate: sessionAuthenticate, checkIfLogged, colibriLogin, createAccount: callCreateAccount, login: callLogin } = useUsersApi();
  const { getFrontendSettings, getRawSettings, patchFrontendSettings } = useSettingsApi();
  const { getExchanges } = useExchangeApi();
  const { resolveStoredCredentials } = useStoredCredentials();
  const assetSteps = useAssetUpdateSteps();

  /** The account `unlock` produced and `loadSession` consumes. One flow runs at a time. */
  let loaded: LoadedAccount | undefined;

  /**
   * Writes back the keys a legacy blob still spells the old way, and retires the old ones.
   *
   * @remarks
   * Tidying, not correctness: `parseFrontendSettings` brings an old shape forward in memory on every
   * read, so the session is already right whether this runs, fails, or is skipped. That is why it
   * only logs on failure - a login must not hinge on it - and why the caller keeps the blob it was
   * given rather than the rewritten one.
   *
   * It goes out as a patch, so the keys a newer rotki wrote and this version cannot represent are
   * left alone. Rewriting the whole blob here used to delete them.
   */
  async function compactLegacySettings(frontendSettings: Record<string, unknown>): Promise<void> {
    const migration = collectMigrationPatch(frontendSettings);
    if (migration === undefined) {
      return;
    }

    try {
      await patchFrontendSettings(migration.patch, migration.remove);
    }
    catch (error: unknown) {
      logger.error('failed to write back the migrated frontend settings', error);
    }
  }

  /** Maps a thrown failure to a typed error, and onto the store refs the conflict dialogs read. */
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

  function failWith(error: unknown): UnlockError {
    authStore.clearUpgradeMessages();
    return toUnlockError(error);
  }

  /**
   * Runs a step behind the single throw boundary of the unlock pipe, turning a throw into a typed
   * `err`. A step that already returns one passes through untouched.
   */
  async function guarded<T>(step: () => Promise<Result<T, UnlockError>>): Promise<Result<T, UnlockError>> {
    try {
      return await step();
    }
    catch (error: unknown) {
      return err(failWith(error));
    }
  }

  async function resumeSession(name: string): Promise<Result<LoadedAccount, UnlockError>> {
    const [rawSettings, frontendSettings, exchanges] = await Promise.all([
      getRawSettings(),
      getFrontendSettings(),
      getExchanges(),
    ]);
    await compactLegacySettings(frontendSettings);
    return ok({
      exchanges,
      fetchData: true,
      settings: UserSettingsModel.parse({ ...rawSettings, frontendSettings }),
      username: name,
    });
  }

  /**
   * Logs in through the orchestrator, flagged `ephemeral` so it leaves no task-center entry: it
   * settles before the shell mounts. A conflict cause rides out on `TaskFailed.cause`.
   */
  async function freshLogin(credentials: UnlockCredentials, name: string): Promise<Result<LoadedAccount, UnlockError>> {
    if (!credentials.username)
      return err({ kind: UnlockErrorKind.unknown, message: '' });

    authStore.resetSyncConflict();
    authStore.resetIncompleteUpgradeConflict();
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
      if (isActionable(outcome.error))
        return err(failWith(outcome.error.cause ?? new Error(outcome.error.message)));
      return err({ kind: UnlockErrorKind.wrongPassword });
    }

    await colibriLogin({ password: credentials.password, username: credentials.username });
    const result = outcome.value;
    // The login response carries every setting but this one, which has its own resource
    const frontendSettings = await getFrontendSettings();
    await compactLegacySettings(frontendSettings);
    const account = UserAccount.parse({
      ...result,
      settings: { ...result.settings, frontendSettings },
    });
    return ok({ exchanges: account.exchanges, fetchData: true, settings: account.settings, username: name });
  }

  /**
   * Mints the signed `rotki_session` cookie the Docker deployment gates on.
   *
   * @remarks
   * Must precede both the websocket open and the unlock task, since `on_open` validates the cookie
   * and the `/tasks` poll is cookie-gated. Runs again after an asset-update restart, to re-mint it
   * with the still-held password. Inert in Electron and dev, where the endpoint sets no cookie.
   */
  const authenticate = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      if (!credentials.password)
        return ok(undefined);

      const name = credentials.username || get<string>(lastLogin);
      await sessionAuthenticate({ password: credentials.password, username: name });
      return ok(undefined);
    });

  /** Skips the cookie handshake for account creation: the user does not exist until the ack. */
  const noopAuthenticate = async (): Promise<Result<void, UnlockError>> => ok(undefined);

  const connect = async (): Promise<Result<void, UnlockError>> => {
    useMonitorService().start();
    return ok(undefined);
  };

  /**
   * Tears the monitor down when the flow abandons an unlock. Stopping it disables websocket
   * reconnection, so a socket the gate rejected for a stale cookie stops retrying instead of
   * looping.
   */
  const disconnect = (): void => {
    useMonitorService().stop();
  };

  /**
   * Defers the socket for account creation, which `createUnlock` opens right after the ack.
   * Opening it here would hand the gate an uncookied handshake and get it closed.
   */
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

  /** Resolves the credentials a background auto-unlock can use; `none` sends the flow to the form. */
  const resolveCredentials = async (): Promise<Result<Option<UnlockCredentials>, UnlockError>> =>
    guarded<Option<UnlockCredentials>>(async () => ok(await resolveStoredCredentials()));

  /**
   * Reports whether the backend already holds a live session for this user with no conflict
   * pending. Decided up front, because the resume branch it selects skips the asset-update prompt.
   */
  const probeSession = async (credentials: UnlockCredentials): Promise<Result<boolean, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const alreadyLogged = await checkIfLogged(name);
      return ok(alreadyLogged && !get(conflictExist));
    });

  /** Stashes an already-live server-side session for `loadSession`, running no login task. */
  const resumeUnlock = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const account = await resumeSession(name);
      if (!account.ok)
        return account;
      loaded = account.value;
      return ok(undefined);
    });

  /** Stashes the account a fresh login returns, for either a manual login or an auto-unlock. */
  const loginUnlock = async (credentials: UnlockCredentials): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      const name = credentials.username || get<string>(lastLogin);
      const account = await freshLogin(credentials, name);
      if (!account.ok)
        return account;
      loaded = account.value;
      return ok(undefined);
    });

  /**
   * Creates the account and stashes it for `loadSession`, opening the socket once the ack lands.
   *
   * @remarks
   * Restoring a premium backup is not a fresh account: the pulled database carries the settings of
   * the account it came from, so the suggestions still apply and the dialog stays available.
   */
  const createUnlock = (payload: CreateAccountPayload) => async (): Promise<Result<void, UnlockError>> =>
    guarded(async () => {
      const outcome = await submitTask<UserAccount>({
        ephemeral: true,
        id: makeActivityId(ActivityKind.SESSION, ActivityPart.CREATE),
        kind: ActivityKind.SESSION,
        lane: SESSION_LANE,
        run: async ({ runTask }) => runTask<UserAccount>(
          async () => {
            const pending = await callCreateAccount(payload);
            useMonitorService().start();
            return pending;
          },
        ),
        title: 'creating account',
      });
      if (!outcome.ok)
        return err({ kind: UnlockErrorKind.unknown, message: outcome.error.message });

      const { exchanges, settings } = UserAccount.parse(outcome.value);
      await colibriLogin({ password: payload.credentials.password, username: payload.credentials.username });
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
      checkUpdate: async () => ok(none),
      connect: noopConnect,
      login: createUnlock(payload),
      probeSession: async () => ok(false),
      resolveCredentials: async () => ok(none),
      resume: async () => ok(undefined),
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
