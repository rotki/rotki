import dayjs from 'dayjs';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountManagement } from '@/modules/auth/use-account-management';
import { createAutoLogin } from '@/modules/auth/use-auto-login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { Constraints } from '@/modules/core/common/constraints';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const { controllerErrors, controllerLoading, controllerState, reset, startCreate, startLogin, startAuto } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    controllerErrors: vueRef([]),
    controllerLoading: vueRef(false),
    controllerState: vueRef({ kind: 'idle' }),
    reset: vi.fn(),
    startCreate: vi.fn(),
    startLogin: vi.fn(),
    startAuto: vi.fn(),
  };
});

vi.mock('@/modules/auth/unlock-flow/use-unlock-flow-controller', () => ({
  useUnlockFlowController: vi.fn(() => ({
    applyUpdate: vi.fn(),
    errors: controllerErrors,
    loading: controllerLoading,
    reset,
    skipUpdate: vi.fn(),
    startCreate,
    startLogin,
    startAuto,
    state: controllerState,
  })),
}));

const mockInterop = vi.hoisted(() => ({
  getPassword: vi.fn(),
  isPackaged: true,
  logToFile: vi.fn(),
  premiumUserLoggedIn: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue(mockInterop),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
  useBackendManagement: vi.fn().mockReturnValue({
    resetSessionBackend: vi.fn(),
  }),
}));

const REMEMBER_PASSWORD_KEY = 'rotki.remember_password';

describe('useAccount', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    set(controllerErrors, []);
    set(controllerState, { kind: 'idle' });
    startLogin.mockReset();
    startCreate.mockReset();
    startAuto.mockReset();
    reset.mockReset();
  });

  describe('login', () => {
    it('should delegate to the controller with normalized credentials and surface no error on success', async () => {
      const { errors, userLogin } = useAccountManagement();

      await userLogin({ password: '1234', username: 'test' });

      expect(startLogin).toHaveBeenCalledWith({ password: '1234', resumeFromBackup: false, syncApproval: 'unknown', username: 'test' });
      expect(get(errors)).toStrictEqual([]);
    });

    it('should surface controller errors on failure', async () => {
      const { errors, userLogin } = useAccountManagement();
      set(controllerErrors, ['errors']);

      await userLogin({ password: '1234', username: 'test' });

      expect(get(errors)).toStrictEqual(['errors']);
    });

    it('should preserve the conflict-resolution fields when re-logging in', async () => {
      const { userLogin } = useAccountManagement();

      await userLogin({ password: '1234', resumeFromBackup: true, syncApproval: 'yes', username: 'test' });

      expect(startLogin).toHaveBeenCalledWith({ password: '1234', resumeFromBackup: true, syncApproval: 'yes', username: 'test' });
    });
  });

  describe('clearErrors', () => {
    it('should reset the flow to dismiss a terminal error', () => {
      const { clearErrors } = useAccountManagement();
      set(controllerState, { kind: 'error' });

      clearErrors();

      expect(reset).toHaveBeenCalled();
    });

    it('should not reset an in-flight flow (a background auto-unlock must survive `touched`)', () => {
      // A background auto-unlock can be in flight while the form is interactive; `touched` →
      // clearErrors must not reset it, or it would drop the flow's credentials and abort with
      // "unlock without an active flow".
      const { clearErrors } = useAccountManagement();

      for (const kind of ['authenticating', 'connecting', 'checking-update', 'unlocking', 'idle'] as const) {
        set(controllerState, { kind });
        clearErrors();
      }

      expect(reset).not.toHaveBeenCalled();
    });
  });

  describe('createAccount', () => {
    it('should forward the payload to the controller and not set an error on success', async () => {
      const { createNewAccount, error } = useAccountManagement();
      const payload = { credentials: { password: '1234', username: 'test' }, initialSettings: { submitUsageAnalytics: false } };

      await createNewAccount(payload);

      expect(startCreate).toHaveBeenCalledWith(payload);
      expect(get(error)).toBe('');
    });

    it('should set the error from the controller on failure', async () => {
      const { createNewAccount, error } = useAccountManagement();
      startCreate.mockImplementation(async () => {
        set(controllerState, { kind: 'error' });
        set(controllerErrors, ['errors']);
      });

      await createNewAccount({
        credentials: { password: '1234', username: 'test' },
        initialSettings: { submitUsageAnalytics: true },
      });

      expect(get(error)).toBe('errors');
    });
  });

  describe('password confirmation', () => {
    beforeEach(() => {
      vi.clearAllMocks();
      mockInterop.isPackaged = true;
      localStorage.setItem(REMEMBER_PASSWORD_KEY, 'true');
    });

    afterEach(() => {
      localStorage.removeItem(REMEMBER_PASSWORD_KEY);
    });

    it('should not set needsPasswordConfirmation when isPackaged is false, even when interval has elapsed', async () => {
      mockInterop.isPackaged = false;
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should not set needsPasswordConfirmation when rememberPassword is not enabled, even when interval has elapsed', async () => {
      localStorage.removeItem(REMEMBER_PASSWORD_KEY);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should set needsPasswordConfirmation when isPackaged is true and interval has elapsed', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should not set needsPasswordConfirmation when password confirmation is disabled', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: false,
        lastPasswordConfirmed: 0,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should not set needsPasswordConfirmation when no stored password exists', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue(undefined);

      // Set lastPasswordConfirmed to an old timestamp so interval has elapsed
      const oldTimestamp = dayjs().unix() - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 1;
      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: oldTimestamp,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      // Should not set needsPasswordConfirmation because no stored password
      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should not set needsPasswordConfirmation when interval has not elapsed', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix(), // Just now
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
      // getPassword should not be called when interval hasn't elapsed (optimization)
      expect(mockInterop.getPassword).not.toHaveBeenCalled();
    });

    it('should set needsPasswordConfirmation when interval has elapsed', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should set needsPasswordConfirmation when exactly at the boundary (interval + 1 second)', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();
      const interval = Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS;

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - interval - 1, // Exactly 1 second past
        passwordConfirmationInterval: interval,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should not set needsPasswordConfirmation when exactly at the interval boundary', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();
      const interval = Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS;

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - interval, // Exactly at boundary
        passwordConfirmationInterval: interval,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should handle 7 days interval correctly', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();
      const sevenDaysInSeconds = 7 * Constraints.SECONDS_PER_DAY;

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - sevenDaysInSeconds - 1,
        passwordConfirmationInterval: sevenDaysInSeconds,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should handle maximum interval (14 days) correctly', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MAX_SECONDS - 1,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MAX_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should not set needsPasswordConfirmation even when interval elapsed if confirmation is disabled', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const now = dayjs().unix();

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      frontendStore.update({
        enablePasswordConfirmation: false, // Disabled
        lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 1000,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should initialize lastPasswordConfirmed when it is 0 (first time use)', async () => {
      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);

      set(needsPasswordConfirmation, false);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const beforeTime = dayjs().unix();

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: 0, // First time use
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = createAutoLogin();
      await checkIfPasswordConfirmationNeeded('testUser');
      const afterTime = dayjs().unix();

      // Should not show dialog on first use
      expect(get(needsPasswordConfirmation)).toBe(false);
      // Should have initialized the timestamp
      expect(frontendStore.lastPasswordConfirmed).toBeGreaterThanOrEqual(beforeTime);
      expect(frontendStore.lastPasswordConfirmed).toBeLessThanOrEqual(afterTime);
    });

    it('should return true when password is correct', async () => {
      const { confirmPassword } = createAutoLogin();
      const correctPassword = 'mySecurePassword123';

      vi.mocked(mockInterop.getPassword).mockResolvedValue(correctPassword);

      const result = await confirmPassword(correctPassword);

      expect(result).toBe(true);
      expect(vi.mocked(mockInterop.getPassword)).toHaveBeenCalled();
    });

    it('should return false when password is incorrect', async () => {
      const { confirmPassword } = createAutoLogin();

      vi.mocked(mockInterop.getPassword).mockResolvedValue('correctPassword');

      const result = await confirmPassword('wrongPassword');

      expect(result).toBe(false);
    });

    it('should return false when password is empty', async () => {
      const { confirmPassword } = createAutoLogin();

      vi.mocked(mockInterop.getPassword).mockResolvedValue('somePassword');

      const result = await confirmPassword('');

      expect(result).toBe(false);
    });

    it('should update lastPasswordConfirmed timestamp when password is correct', async () => {
      const frontendStore = useFrontendSettingsStore();
      const { confirmPassword } = createAutoLogin();
      const correctPassword = 'testPassword';

      vi.mocked(mockInterop.getPassword).mockResolvedValue(correctPassword);

      const beforeTime = dayjs().unix();
      await confirmPassword(correctPassword);
      const afterTime = dayjs().unix();

      const updatedTimestamp = frontendStore.lastPasswordConfirmed;
      expect(updatedTimestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(updatedTimestamp).toBeLessThanOrEqual(afterTime);
    });

    it('should not update timestamp when password is incorrect', async () => {
      const frontendStore = useFrontendSettingsStore();
      const { confirmPassword } = createAutoLogin();

      const initialTimestamp = frontendStore.lastPasswordConfirmed;
      vi.mocked(mockInterop.getPassword).mockResolvedValue('correctPassword');

      await confirmPassword('wrongPassword');

      expect(frontendStore.lastPasswordConfirmed).toBe(initialTimestamp);
    });

    it('should set needsPasswordConfirmation to false when password is correct', async () => {
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const { confirmPassword } = createAutoLogin();
      const correctPassword = 'test123';

      set(needsPasswordConfirmation, true);
      vi.mocked(mockInterop.getPassword).mockResolvedValue(correctPassword);

      await confirmPassword(correctPassword);

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should handle special characters in password', async () => {
      const { confirmPassword } = createAutoLogin();
      const specialPassword = 'p@$$w0rd!#$%^&*()';

      vi.mocked(mockInterop.getPassword).mockResolvedValue(specialPassword);

      const result = await confirmPassword(specialPassword);

      expect(result).toBe(true);
    });

    it('should compare passwords case-sensitively', async () => {
      const { confirmPassword } = createAutoLogin();

      vi.mocked(mockInterop.getPassword).mockResolvedValue('Password123');

      const resultLower = await confirmPassword('password123');
      expect(resultLower).toBe(false);

      const resultCorrect = await confirmPassword('Password123');
      expect(resultCorrect).toBe(true);
    });

    it('should handle getPassword rejection', async () => {
      const { confirmPassword } = createAutoLogin();

      vi.mocked(mockInterop.getPassword).mockRejectedValue(new Error('Failed to get password'));

      await expect(confirmPassword('anyPassword')).rejects.toThrow('Failed to get password');
    });
  });
});
