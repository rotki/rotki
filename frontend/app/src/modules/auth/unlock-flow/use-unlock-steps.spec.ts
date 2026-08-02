import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, none, ok, some } from 'plainfp';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type CreateAccountPayload, IncompleteUpgradeError, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { type UnlockCredentials, UnlockErrorKind } from './use-unlock-flow';
import { useUnlockSteps } from './use-unlock-steps';

const {
  applyUpdate,
  authenticateApi,
  callCreateAccount,
  callLogin,
  checkIfLogged,
  checkUpdate,
  colibriLogin,
  getExchanges,
  getRawSettings,
  initialize,
  lastLoginRef,
  migrateSettingsIfNeeded,
  monitorStart,
  monitorStop,
  requestRestart,
  resolveStoredCredentials,
  runTaskResult,
  setSettings,
  sigilEmit,
  waitReady,
} = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    applyUpdate: vi.fn(),
    authenticateApi: vi.fn().mockResolvedValue(undefined),
    callCreateAccount: vi.fn(),
    callLogin: vi.fn(),
    checkIfLogged: vi.fn(),
    checkUpdate: vi.fn(),
    colibriLogin: vi.fn().mockResolvedValue(undefined),
    getExchanges: vi.fn(),
    getRawSettings: vi.fn(),
    initialize: vi.fn(),
    lastLoginRef: vueRef(''),
    migrateSettingsIfNeeded: vi.fn(),
    monitorStart: vi.fn(),
    monitorStop: vi.fn(),
    requestRestart: vi.fn(),
    resolveStoredCredentials: vi.fn(),
    runTaskResult: vi.fn(),
    setSettings: vi.fn(),
    sigilEmit: vi.fn(),
    waitReady: vi.fn(),
  };
});

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
    authenticate: authenticateApi,
    checkIfLogged,
    colibriLogin,
    createAccount: callCreateAccount,
    login: callLogin,
  })),
}));

vi.mock('@/modules/settings/api/use-settings-api', () => ({
  useSettingsApi: vi.fn(() => ({ getRawSettings, setSettings })),
}));

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: vi.fn(() => ({ getExchanges })),
}));

vi.mock('./use-stored-credentials', () => ({
  useStoredCredentials: vi.fn(() => ({ resolveStoredCredentials })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  ActivityKind: { SESSION: 'session' },
  ActivityPart: { CREATE: 'create', LOGIN: 'login' },
  // Mirrors the real predicate: only an actionable `TaskFailed` carries a `cause`.
  isActionable: (error: { _tag?: string }): boolean => error?._tag === 'TaskFailed',
  makeActivityId: (kind: string, ...parts: (string | number)[]): string => [kind, ...parts].join(':'),
  // The real bridge runs the spec's `run` and returns its outcome; do the same so a test drives
  // the flow purely through `runTaskResult`.
  useNativeTask: vi.fn(() => ({
    runTaskResult,
    submitTask: vi.fn(runSpecWith(runTaskResult)),
  })),
}));

vi.mock('@/modules/session/use-session-settings', () => ({
  useSessionSettings: vi.fn(() => ({ initialize })),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: vi.fn(() => ({ start: monitorStart, stop: monitorStop })),
}));

vi.mock('@/modules/core/sigil/event-bus', () => ({
  sigilBus: { emit: sigilEmit },
}));

vi.mock('@/modules/auth/account-management', () => ({
  lastLogin: lastLoginRef,
}));

vi.mock('@/modules/settings/types/frontend-settings-migrations', () => ({
  migrateSettingsIfNeeded,
}));

vi.mock('@/modules/settings/types/user-settings', () => ({
  UserAccount: { parse: vi.fn((value: unknown) => value) },
  UserSettingsModel: { parse: vi.fn((value: unknown) => value) },
}));

vi.mock('@/modules/core/common/logging/error-handling', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
}));

vi.mock('./use-asset-update-steps', () => ({
  useAssetUpdateSteps: vi.fn(() => ({ applyUpdate, checkUpdate, requestRestart, waitReady })),
}));

function setupStore(): ReturnType<typeof useSessionAuthStore> {
  setActivePinia(createPinia());
  return useSessionAuthStore();
}

const credentials: UnlockCredentials = { password: 'p', username: 'alice' };

describe('useUnlockSteps', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(lastLoginRef, '');
    resolveStoredCredentials.mockResolvedValue(none);
    migrateSettingsIfNeeded.mockReturnValue(undefined);
  });

  describe('loginSteps.probeSession', () => {
    it('should report resumable when already logged in and no conflict', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(true);

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.probeSession(credentials)).toEqual({ ok: true, value: true });
    });

    it('should not be resumable when a conflict exists', async () => {
      const store = setupStore();
      checkIfLogged.mockResolvedValue(true);
      set(storeToRefs(store).syncConflict, { message: 'x', payload: { localLastModified: 1, remoteLastModified: 2 } });

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.probeSession(credentials)).toEqual({ ok: true, value: false });
    });

    it('should not be resumable when not logged in', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.probeSession(credentials)).toEqual({ ok: true, value: false });
    });

    it('should fall back to lastLogin when credentials.username is empty', async () => {
      setupStore();
      set(lastLoginRef, 'remembered');
      checkIfLogged.mockResolvedValue(true);

      const { loginSteps } = useUnlockSteps();
      await loginSteps.probeSession({ password: 'p', username: '' });

      expect(checkIfLogged).toHaveBeenCalledWith('remembered');
    });

    it('should map an unexpected throw to err(unknown)', async () => {
      setupStore();
      checkIfLogged.mockRejectedValue(new Error('boom'));

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.probeSession(credentials)).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'boom' }, ok: false });
    });
  });

  describe('loginSteps.resume', () => {
    it('should resume from settings + exchanges without running the login task', async () => {
      setupStore();
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([{ location: 'kraken', name: 'kraken' }]);

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.resume(credentials);

      expect(result).toEqual({ ok: true, value: undefined });
      expect(getRawSettings).toHaveBeenCalled();
      expect(getExchanges).toHaveBeenCalled();
      expect(runTaskResult).not.toHaveBeenCalled();
    });

    it('should map SyncConflictError onto the store and return err(syncConflict)', async () => {
      const store = setupStore();
      const { syncConflict } = storeToRefs(store);
      const payload = { localLastModified: 1, remoteLastModified: 2 };
      getRawSettings.mockRejectedValueOnce(new SyncConflictError('conflict!', { payload }));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.resume(credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.syncConflict, payload }, ok: false });
      expect(get(syncConflict)).toEqual({ message: 'conflict!', payload });
    });

    it('should map IncompleteUpgradeError onto the store and return err(incompleteUpgrade)', async () => {
      const store = setupStore();
      const { incompleteUpgradeConflict } = storeToRefs(store);
      getRawSettings.mockRejectedValueOnce(new IncompleteUpgradeError('upgrade!'));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.resume(credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.incompleteUpgrade }, ok: false });
      expect(get(incompleteUpgradeConflict)).toEqual({ message: 'upgrade!' });
    });

    it('should persist migrated frontend settings on resume', async () => {
      setupStore();
      getRawSettings.mockResolvedValue({ frontendSettings: 'OLD' });
      getExchanges.mockResolvedValue([]);
      migrateSettingsIfNeeded.mockReturnValue('NEW');

      const { loginSteps } = useUnlockSteps();
      await loginSteps.resume(credentials);

      expect(setSettings).toHaveBeenCalledWith({ frontendSettings: 'NEW' });
    });
  });

  describe('loginSteps.login', () => {
    it('should run the login task path and colibri login', async () => {
      setupStore();
      runTaskResult.mockResolvedValue(ok({ exchanges: [], settings: { frontendSettings: '{}' } }));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.login({ password: 'p', username: 'bob' });

      expect(result).toEqual({ ok: true, value: undefined });
      expect(runTaskResult).toHaveBeenCalled();
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'p', username: 'bob' });
    });

    it('should return err(wrongPassword) on a non-actionable login failure', async () => {
      setupStore();
      runTaskResult.mockResolvedValue(err(Cancelled({ message: '' })));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.login({ password: 'p', username: 'bob' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.wrongPassword }, ok: false });
      expect(colibriLogin).not.toHaveBeenCalled();
    });

    it('should return a silent unknown err when no username is available', async () => {
      setupStore();

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.login({ password: 'p', username: '' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: '' }, ok: false });
      expect(runTaskResult).not.toHaveBeenCalled();
    });

    it('should map a SyncConflictError carried by an actionable login-task failure', async () => {
      const store = setupStore();
      const { syncConflict } = storeToRefs(store);
      const payload = { localLastModified: 1, remoteLastModified: 2 };
      // the task monitor forwards the original error as the cause of an actionable TaskFailed
      runTaskResult.mockResolvedValue(err(TaskFailed({ cause: new SyncConflictError('conflict!', { payload }), message: 'conflict!' })));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.login({ password: 'p', username: 'bob' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.syncConflict, payload }, ok: false });
      expect(get(syncConflict)).toEqual({ message: 'conflict!', payload });
      expect(colibriLogin).not.toHaveBeenCalled();
    });
  });

  describe('loginSteps.resolveCredentials', () => {
    it('should wrap the resolved stored credentials in ok', async () => {
      setupStore();
      resolveStoredCredentials.mockResolvedValue(some({ password: 'secret', username: 'alice' }));

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.resolveCredentials()).toEqual({ ok: true, value: some({ password: 'secret', username: 'alice' }) });
    });

    it('should map a resolution throw to err(unknown)', async () => {
      setupStore();
      resolveStoredCredentials.mockRejectedValue(new Error('keychain boom'));

      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.resolveCredentials()).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'keychain boom' }, ok: false });
    });
  });

  describe('createSteps(payload)', () => {
    const payload: CreateAccountPayload = {
      credentials: { password: 'pw', username: 'new-user' },
      initialSettings: { submitUsageAnalytics: true },
    };

    it('should stash the new account when the create task succeeds', async () => {
      setupStore();
      runTaskResult.mockResolvedValue(ok({ exchanges: [], settings: { frontendSettings: '{}' } }));

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).login(payload.credentials);

      expect(result).toEqual({ ok: true, value: undefined });
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'pw', username: 'new-user' });
    });

    it('should return err(unknown) with the message when the create task fails', async () => {
      setupStore();
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'nope' })));

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).login(payload.credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'nope' }, ok: false });
      expect(colibriLogin).not.toHaveBeenCalled();
    });

    it('should never be resumable and never prompt for an update', async () => {
      setupStore();

      const { createSteps } = useUnlockSteps();
      const steps = createSteps(payload);
      expect(await steps.probeSession(payload.credentials)).toEqual({ ok: true, value: false });
      expect(await steps.checkUpdate()).toEqual({ ok: true, value: { some: false } });
      expect(checkUpdate).not.toHaveBeenCalled();
    });

    it('should not open the socket on connect (deferred to post-ack)', async () => {
      setupStore();
      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).connect();

      expect(result).toEqual({ ok: true, value: undefined });
      expect(monitorStart).not.toHaveBeenCalled();
    });

    it('should start the monitor only after the create ack sets the cookie', async () => {
      setupStore();
      callCreateAccount.mockResolvedValue({ taskId: 1 });
      // run the executor so the ack→monitor ordering inside createUnlock is observable.
      runTaskResult.mockImplementation(async (executor: () => Promise<unknown>) => {
        await executor();
        return ok({ exchanges: [], settings: { frontendSettings: '{}' } });
      });

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).login(payload.credentials);

      expect(result).toEqual({ ok: true, value: undefined });
      expect(monitorStart).toHaveBeenCalled();
      // the socket must not open before the create ack (no cookie exists until then).
      expect(callCreateAccount.mock.invocationCallOrder[0])
        .toBeLessThan(monitorStart.mock.invocationCallOrder[0]);
    });
  });

  describe('loadSession', () => {
    it('should hydrate the store and emit session:ready after a successful unlock', async () => {
      const store = setupStore();
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);

      const { loginSteps } = useUnlockSteps();
      await loginSteps.resume(credentials);
      const result = await loginSteps.loadSession();

      expect(result).toEqual({ ok: true, value: { username: 'alice' } });
      expect(initialize).toHaveBeenCalled();
      const refs = storeToRefs(store);
      expect(get(refs.logged)).toBe(true);
      expect(get(refs.username)).toBe('alice');
      expect(get(refs.shouldFetchData)).toBe(true);
      expect(sigilEmit).toHaveBeenCalledWith('session:ready');
    });

    it('should return err(unknown) when there is no unlocked account', async () => {
      setupStore();

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.loadSession();

      expect(result.ok).toBe(false);
    });

    it('should map an initialize failure to a typed err', async () => {
      setupStore();
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);
      initialize.mockRejectedValueOnce(new Error('init failed'));

      const { loginSteps } = useUnlockSteps();
      await loginSteps.resume(credentials);
      const result = await loginSteps.loadSession();

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'init failed' }, ok: false });
    });
  });

  describe('shared steps', () => {
    it('should post the credentials to the authenticate endpoint on login', async () => {
      setupStore();
      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.authenticate(credentials)).toEqual({ ok: true, value: undefined });
      // authenticate-first: the cookie must ride the WS handshake and /tasks poll.
      expect(authenticateApi).toHaveBeenCalledWith({ password: 'p', username: 'alice' });
    });

    it('should fall back to the last login when authenticating without a username', async () => {
      setupStore();
      set(lastLoginRef, 'remembered');
      const { loginSteps } = useUnlockSteps();
      await loginSteps.authenticate({ password: 'p', username: '' });
      expect(authenticateApi).toHaveBeenCalledWith({ password: 'p', username: 'remembered' });
    });

    it('should skip the authenticate call when there is no password (cookie-based resume)', async () => {
      setupStore();
      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.authenticate({ password: '', username: 'alice' })).toEqual({ ok: true, value: undefined });
      expect(authenticateApi).not.toHaveBeenCalled();
    });

    it('should map a wrong-password rejection to a typed err', async () => {
      setupStore();
      authenticateApi.mockRejectedValueOnce(new Error('Wrong username/password combination'));
      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.authenticate(credentials)).toEqual({
        error: { kind: UnlockErrorKind.unknown, message: 'Wrong username/password combination' },
        ok: false,
      });
    });

    it('should not authenticate on account creation (cookie rides the task ack)', async () => {
      setupStore();
      const payload: CreateAccountPayload = {
        credentials: { password: 'pw', username: 'new-user' },
        initialSettings: { submitUsageAnalytics: true },
      };
      const { createSteps } = useUnlockSteps();
      expect(await createSteps(payload).authenticate(credentials)).toEqual({ ok: true, value: undefined });
      expect(authenticateApi).not.toHaveBeenCalled();
    });

    it('should start the monitor service on connect', async () => {
      setupStore();
      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.connect();

      expect(result).toEqual({ ok: true, value: undefined });
      expect(monitorStart).toHaveBeenCalled();
    });
  });
});
