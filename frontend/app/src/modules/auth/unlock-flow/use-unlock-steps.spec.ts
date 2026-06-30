import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type CreateAccountPayload, IncompleteUpgradeError, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { type UnlockCredentials, UnlockErrorKind } from './use-unlock-flow';
import { useUnlockSteps } from './use-unlock-steps';

const {
  applyUpdate,
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
  requestRestart,
  runTask,
  setSettings,
  sigilEmit,
  waitReady,
} = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    applyUpdate: vi.fn(),
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
    requestRestart: vi.fn(),
    runTask: vi.fn(),
    setSettings: vi.fn(),
    sigilEmit: vi.fn(),
    waitReady: vi.fn(),
  };
});

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
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

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: (outcome: { success: boolean; error?: unknown }): boolean =>
    !outcome.success && outcome.error !== undefined,
  useTaskHandler: vi.fn(() => ({ runTask })),
}));

vi.mock('@/modules/session/use-session-settings', () => ({
  useSessionSettings: vi.fn(() => ({ initialize })),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: vi.fn(() => ({ start: monitorStart })),
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
    migrateSettingsIfNeeded.mockReturnValue(undefined);
  });

  describe('loginSteps.unlock', () => {
    it('should resume from an existing session when already logged in and no conflict', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([{ location: 'kraken', name: 'kraken' }]);

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock(credentials);

      expect(result).toEqual({ ok: true, value: undefined });
      expect(getRawSettings).toHaveBeenCalled();
      expect(getExchanges).toHaveBeenCalled();
      expect(runTask).not.toHaveBeenCalled();
    });

    it('should fall back to lastLogin when credentials.username is empty', async () => {
      setupStore();
      set(lastLoginRef, 'remembered');
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);

      const { loginSteps } = useUnlockSteps();
      await loginSteps.unlock({ password: 'p', username: '' });

      expect(checkIfLogged).toHaveBeenCalledWith('remembered');
    });

    it('should run the login task path when not currently logged in', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);
      runTask.mockResolvedValue({
        result: { exchanges: [], settings: { frontendSettings: '{}' } },
        success: true,
      });

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock({ password: 'p', username: 'bob' });

      expect(result).toEqual({ ok: true, value: undefined });
      expect(runTask).toHaveBeenCalled();
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'p', username: 'bob' });
    });

    it('should return err(wrongPassword) on a non-actionable login failure', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);
      runTask.mockResolvedValue({ message: '', success: false });

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock({ password: 'p', username: 'bob' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.wrongPassword }, ok: false });
      expect(colibriLogin).not.toHaveBeenCalled();
    });

    it('should return a silent unknown err when no username and not logged in', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock({ password: 'p', username: '' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: '' }, ok: false });
      expect(runTask).not.toHaveBeenCalled();
    });

    it('should map SyncConflictError onto the store and return err(syncConflict)', async () => {
      const store = setupStore();
      const { syncConflict } = storeToRefs(store);
      checkIfLogged.mockResolvedValue(true);
      const payload = { localLastModified: 1, remoteLastModified: 2 };
      getRawSettings.mockRejectedValueOnce(new SyncConflictError('conflict!', payload));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock(credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.syncConflict, payload }, ok: false });
      expect(get(syncConflict)).toEqual({ message: 'conflict!', payload });
    });

    it('should map a SyncConflictError carried by an actionable login-task failure', async () => {
      const store = setupStore();
      const { syncConflict } = storeToRefs(store);
      checkIfLogged.mockResolvedValue(false);
      const payload = { localLastModified: 1, remoteLastModified: 2 };
      // the task monitor forwards the original error on the failed outcome
      runTask.mockResolvedValue({ error: new SyncConflictError('conflict!', payload), message: 'conflict!', success: false });

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock({ password: 'p', username: 'bob' });

      expect(result).toEqual({ error: { kind: UnlockErrorKind.syncConflict, payload }, ok: false });
      expect(get(syncConflict)).toEqual({ message: 'conflict!', payload });
      expect(colibriLogin).not.toHaveBeenCalled();
    });

    it('should map IncompleteUpgradeError onto the store and return err(incompleteUpgrade)', async () => {
      const store = setupStore();
      const { incompleteUpgradeConflict } = storeToRefs(store);
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockRejectedValueOnce(new IncompleteUpgradeError('upgrade!'));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock(credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.incompleteUpgrade }, ok: false });
      expect(get(incompleteUpgradeConflict)).toEqual({ message: 'upgrade!' });
    });

    it('should return err(unknown) with the message when an unexpected error is thrown', async () => {
      setupStore();
      checkIfLogged.mockRejectedValue(new Error('boom'));

      const { loginSteps } = useUnlockSteps();
      const result = await loginSteps.unlock(credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'boom' }, ok: false });
    });

    it('should persist migrated frontend settings on resume', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: 'OLD' });
      getExchanges.mockResolvedValue([]);
      migrateSettingsIfNeeded.mockReturnValue('NEW');

      const { loginSteps } = useUnlockSteps();
      await loginSteps.unlock(credentials);

      expect(setSettings).toHaveBeenCalledWith({ frontendSettings: 'NEW' });
    });
  });

  describe('createSteps(payload).unlock', () => {
    const payload: CreateAccountPayload = {
      credentials: { password: 'pw', username: 'new-user' },
      initialSettings: { submitUsageAnalytics: true },
    };

    it('should stash the new account when the create task succeeds', async () => {
      setupStore();
      runTask.mockResolvedValue({
        result: { exchanges: [], settings: { frontendSettings: '{}' } },
        success: true,
      });

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).unlock(payload.credentials);

      expect(result).toEqual({ ok: true, value: undefined });
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'pw', username: 'new-user' });
    });

    it('should return err(unknown) with the message when the create task fails', async () => {
      setupStore();
      runTask.mockResolvedValue({ message: 'nope', success: false });

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).unlock(payload.credentials);

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'nope' }, ok: false });
      expect(colibriLogin).not.toHaveBeenCalled();
    });

    it('should report no update for a fresh account', async () => {
      setupStore();

      const { createSteps } = useUnlockSteps();
      const result = await createSteps(payload).checkUpdate();

      expect(result).toEqual({ ok: true, value: { some: false } });
      expect(checkUpdate).not.toHaveBeenCalled();
    });
  });

  describe('loadSession', () => {
    it('should hydrate the store and emit session:ready after a successful unlock', async () => {
      const store = setupStore();
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);

      const { loginSteps } = useUnlockSteps();
      await loginSteps.unlock(credentials);
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
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);
      initialize.mockRejectedValueOnce(new Error('init failed'));

      const { loginSteps } = useUnlockSteps();
      await loginSteps.unlock(credentials);
      const result = await loginSteps.loadSession();

      expect(result).toEqual({ error: { kind: UnlockErrorKind.unknown, message: 'init failed' }, ok: false });
    });
  });

  describe('shared steps', () => {
    it('should resolve authenticate to ok without a session key', async () => {
      setupStore();
      const { loginSteps } = useUnlockSteps();
      expect(await loginSteps.authenticate(credentials)).toEqual({ ok: true, value: undefined });
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
