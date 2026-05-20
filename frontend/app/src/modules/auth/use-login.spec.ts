import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type CreateAccountPayload, IncompleteUpgradeError, type LoginCredentials, SyncConflictError } from '@/modules/auth/login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useLogin } from './use-login';

const {
  callCreateAccount,
  callLogin,
  checkIfLogged,
  colibriLogin,
  getExchanges,
  getRawSettings,
  initialize,
  lastLoginRef,
  migrateSettingsIfNeeded,
  monitorStart,
  runTask,
  setOnAuthFailure,
  setSettings,
  sigilEmit,
} = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    callCreateAccount: vi.fn(),
    callLogin: vi.fn(),
    checkIfLogged: vi.fn(),
    colibriLogin: vi.fn().mockResolvedValue(undefined),
    getExchanges: vi.fn(),
    getRawSettings: vi.fn(),
    initialize: vi.fn(),
    lastLoginRef: vueRef(''),
    migrateSettingsIfNeeded: vi.fn(),
    monitorStart: vi.fn(),
    runTask: vi.fn(),
    setOnAuthFailure: vi.fn<(callback: () => void) => void>(),
    setSettings: vi.fn(),
    sigilEmit: vi.fn(),
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

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: { setOnAuthFailure },
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

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/core/common/logging/error-handling', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
}));

function setupStore(): ReturnType<typeof useSessionAuthStore> {
  setActivePinia(createPinia());
  return useSessionAuthStore();
}

describe('useLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(lastLoginRef, '');
    migrateSettingsIfNeeded.mockReturnValue(undefined);
  });

  describe('login', () => {
    it('should hydrate from existing session when already logged in and no conflict', async () => {
      const store = setupStore();
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([{ name: 'kraken', location: 'kraken' }]);

      const credentials: LoginCredentials = { password: 'p', username: 'alice' };
      const { login } = useLogin();
      const result = await login(credentials);

      expect(result).toEqual({ success: true });
      expect(getRawSettings).toHaveBeenCalled();
      expect(getExchanges).toHaveBeenCalled();
      expect(initialize).toHaveBeenCalled();
      const refs = storeToRefs(store);
      expect(get(refs.logged)).toBe(true);
      expect(get(refs.username)).toBe('alice');
      expect(get(refs.shouldFetchData)).toBe(true);
      expect(sigilEmit).toHaveBeenCalledWith('session:ready');
    });

    it('should fall back to lastLogin when credentials.username is empty and user is logged in', async () => {
      setupStore();
      set(lastLoginRef, 'remembered');
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
      getExchanges.mockResolvedValue([]);

      const { login } = useLogin();
      await login({ password: 'p', username: '' });

      expect(checkIfLogged).toHaveBeenCalledWith('remembered');
    });

    it('should run the login task path when not currently logged in', async () => {
      const store = setupStore();
      checkIfLogged.mockResolvedValue(false);
      runTask.mockResolvedValue({
        result: { exchanges: [], settings: { frontendSettings: '{}' } },
        success: true,
      });

      const credentials: LoginCredentials = { password: 'p', username: 'bob' };
      const { login } = useLogin();
      const result = await login(credentials);

      expect(result).toEqual({ success: true });
      expect(monitorStart).toHaveBeenCalled();
      expect(runTask).toHaveBeenCalled();
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'p', username: 'bob' });
      expect(get(storeToRefs(store).logged)).toBe(true);
    });

    it('should return a silent failure when no username is provided and the user is not logged in', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);

      const { login } = useLogin();
      const result = await login({ password: 'p', username: '' });

      expect(result).toEqual({ message: '', success: false });
      expect(runTask).not.toHaveBeenCalled();
    });

    it('should return silent failure when login task fails without an actionable error', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(false);
      runTask.mockResolvedValue({ message: '', success: false });

      const { login } = useLogin();
      const result = await login({ password: 'p', username: 'bob' });

      expect(result).toEqual({ message: '', success: false });
    });

    it('should map SyncConflictError onto the store when raised during hydration', async () => {
      const store = setupStore();
      const { syncConflict } = storeToRefs(store);
      checkIfLogged.mockResolvedValue(true);
      const payload = { localLastModified: 1, remoteLastModified: 2 };
      getRawSettings.mockRejectedValueOnce(new SyncConflictError('conflict!', payload));

      const { login } = useLogin();
      const result = await login({ password: 'p', username: 'alice' });

      expect(result.success).toBe(false);
      expect(get(syncConflict)).toEqual({ message: 'conflict!', payload });
    });

    it('should map IncompleteUpgradeError onto the store when raised during hydration', async () => {
      const store = setupStore();
      const { incompleteUpgradeConflict } = storeToRefs(store);
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockRejectedValueOnce(new IncompleteUpgradeError('upgrade!'));

      const { login } = useLogin();
      await login({ password: 'p', username: 'alice' });

      expect(get(incompleteUpgradeConflict)).toEqual({ message: 'upgrade!' });
    });

    it('should return error message via createActionStatus when an unexpected error is thrown', async () => {
      setupStore();
      checkIfLogged.mockRejectedValue(new Error('boom'));

      const { login } = useLogin();
      const result = await login({ password: 'p', username: 'bob' });

      expect(result).toEqual({ message: 'boom', success: false });
    });

    it('should persist migrated frontend settings when a migration is needed', async () => {
      setupStore();
      checkIfLogged.mockResolvedValue(true);
      getRawSettings.mockResolvedValue({ frontendSettings: 'OLD' });
      getExchanges.mockResolvedValue([]);
      migrateSettingsIfNeeded.mockReturnValue('NEW');

      const { login } = useLogin();
      await login({ password: 'p', username: 'alice' });

      expect(setSettings).toHaveBeenCalledWith({ frontendSettings: 'NEW' });
    });
  });

  describe('createAccount', () => {
    it('should unlock the session when the create-account task succeeds', async () => {
      const store = setupStore();
      runTask.mockResolvedValue({
        result: { exchanges: [], settings: { frontendSettings: '{}' } },
        success: true,
      });

      const payload: CreateAccountPayload = {
        credentials: { password: 'pw', username: 'new-user' },
        initialSettings: { submitUsageAnalytics: true },
      };
      const { createAccount } = useLogin();
      const result = await createAccount(payload);

      const refs = storeToRefs(store);
      expect(result).toEqual({ success: true });
      expect(monitorStart).toHaveBeenCalled();
      expect(colibriLogin).toHaveBeenCalledWith({ password: 'pw', username: 'new-user' });
      expect(get(refs.username)).toBe('new-user');
      expect(get(refs.logged)).toBe(true);
    });

    it('should propagate the syncDatabase flag from premiumSetup as fetchData', async () => {
      const store = setupStore();
      runTask.mockResolvedValue({
        result: { exchanges: [], settings: { frontendSettings: '{}' } },
        success: true,
      });

      const payload: CreateAccountPayload = {
        credentials: { password: 'pw', username: 'pro' },
        initialSettings: { submitUsageAnalytics: true },
        premiumSetup: { apiKey: 'k', apiSecret: 's', syncDatabase: true },
      };

      const { createAccount } = useLogin();
      await createAccount(payload);

      expect(get(storeToRefs(store).shouldFetchData)).toBe(true);
    });

    it('should return a failure when the create-account task fails', async () => {
      setupStore();
      runTask.mockResolvedValue({ message: 'nope', success: false });

      const { createAccount } = useLogin();
      const result = await createAccount({
        credentials: { password: 'pw', username: 'new-user' },
        initialSettings: { submitUsageAnalytics: true },
      });

      expect(result).toEqual({ message: 'nope', success: false });
      expect(colibriLogin).not.toHaveBeenCalled();
    });
  });

  describe('unlock side effects', () => {
    it('should reset logged when the api auth-failure handler fires', async () => {
      const store = setupStore();
      const { logged } = storeToRefs(store);
      useLogin();
      await flushPromises();

      set(logged, true);
      setOnAuthFailure.mock.calls.at(-1)?.[0]?.();

      expect(get(logged)).toBe(false);
    });
  });

  it('should propagate initialize failures as createActionStatus', async () => {
    setupStore();
    checkIfLogged.mockResolvedValue(true);
    getRawSettings.mockResolvedValue({ frontendSettings: '{}' });
    getExchanges.mockResolvedValue([]);
    initialize.mockRejectedValueOnce(new Error('init failed'));

    const { login } = useLogin();
    const result = await login({ password: 'p', username: 'alice' });

    expect(result).toEqual({ message: 'init failed', success: false });
  });
});
