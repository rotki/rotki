import dayjs from 'dayjs';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useInterop } from '@/composables/electron-interop';
import { useAccountManagement, useAutoLogin } from '@/composables/user/account';
import { Constraints } from '@/data/constraints';
import { useLogin } from '@/modules/account/use-login';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
}));

vi.mock('@/modules/account/use-login', () => ({
  useLogin: vi.fn().mockReturnValue({
    login: vi.fn(),
    createAccount: vi.fn(),
  }),
}));

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    getPassword: vi.fn(),
    premiumUserLoggedIn: vi.fn(),
  }),
}));

describe('composables::user/account', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('existing account', () => {
    const { login } = useLogin();

    it('login success, should not show error message', async () => {
      const { userLogin, errors } = useAccountManagement();

      vi.mocked(login).mockResolvedValue({
        success: true,
      });

      await userLogin({ username: 'test', password: '1234' });

      expect(get(errors)).toStrictEqual([]);
    });

    it('login failed, should show error message', async () => {
      const { userLogin, errors } = useAccountManagement();

      vi.mocked(login).mockResolvedValue({
        success: false,
        message: 'errors',
      });

      await userLogin({ username: 'test', password: '1234' });

      expect(get(errors)).toStrictEqual(['errors']);
    });
  });

  describe('new account', () => {
    const { createAccount } = useLogin();

    it('create account success, should not show error message', async () => {
      const { createNewAccount, error } = useAccountManagement();

      vi.mocked(createAccount).mockResolvedValue({
        success: true,
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: false },
      });

      expect(get(error)).toStrictEqual('');
    });

    it('login failed, should show error message', async () => {
      const { createNewAccount, error } = useAccountManagement();

      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors',
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true },
      });

      expect(get(error)).toStrictEqual('errors');
    });

    it('create account with submitUsageAnalytics true', async () => {
      const { createNewAccount } = useAccountManagement();
      vi.clearAllMocks();
      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors',
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true },
      });

      expect(createAccount).toHaveBeenCalledWith({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true },
      });
    });

    it('create account with submitUsageAnalytics false', async () => {
      const { createNewAccount } = useAccountManagement();
      vi.clearAllMocks();
      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors',
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: false },
      });

      expect(createAccount).toHaveBeenCalledWith({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: false },
      });
    });
  });

  describe('password confirmation', () => {
    let mockGetPassword: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      vi.clearAllMocks();
      const { getPassword } = useInterop();
      mockGetPassword = vi.mocked(getPassword);
    });

    describe('checkIfPasswordConfirmationNeeded', () => {
      it('should not set needsPasswordConfirmation when password confirmation is disabled', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: false,
          lastPasswordConfirmed: 0,
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(false);
      });

      it('should not set needsPasswordConfirmation when no stored password exists', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue(undefined);

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: 0,
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(false);
      });

      it('should not set needsPasswordConfirmation when interval has not elapsed', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: dayjs().unix(), // Just now
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(false);
      });

      it('should set needsPasswordConfirmation when interval has elapsed', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);
        const now = dayjs().unix();

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
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
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: now - interval - 1, // Exactly 1 second past
          passwordConfirmationInterval: interval,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
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
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: now - interval, // Exactly at boundary
          passwordConfirmationInterval: interval,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
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
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: now - sevenDaysInSeconds - 1,
          passwordConfirmationInterval: sevenDaysInSeconds,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(true);
      });

      it('should handle maximum interval (14 days) correctly', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);
        const now = dayjs().unix();

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MAX_SECONDS - 1,
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MAX_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(true);
      });

      it('should not set needsPasswordConfirmation even when interval elapsed if confirmation is disabled', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);
        const now = dayjs().unix();

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        await frontendStore.updateSetting({
          enablePasswordConfirmation: false, // Disabled
          lastPasswordConfirmed: now - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 1000,
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');

        expect(get(needsPasswordConfirmation)).toBe(false);
      });

      it('should initialize lastPasswordConfirmed when it is 0 (first time use)', async () => {
        const frontendStore = useFrontendSettingsStore();
        const authStore = useSessionAuthStore();
        const { needsPasswordConfirmation } = storeToRefs(authStore);

        set(needsPasswordConfirmation, false);
        mockGetPassword.mockResolvedValue('storedPassword');

        const beforeTime = dayjs().unix();

        await frontendStore.updateSetting({
          enablePasswordConfirmation: true,
          lastPasswordConfirmed: 0, // First time use
          passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
        });

        const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
        await checkIfPasswordConfirmationNeeded('testUser');
        const afterTime = dayjs().unix();

        // Should not show dialog on first use
        expect(get(needsPasswordConfirmation)).toBe(false);
        // Should have initialized the timestamp
        expect(frontendStore.lastPasswordConfirmed).toBeGreaterThanOrEqual(beforeTime);
        expect(frontendStore.lastPasswordConfirmed).toBeLessThanOrEqual(afterTime);
      });
    });

    it('should return true when password is correct', async () => {
      const { confirmPassword } = useAutoLogin();
      const correctPassword = 'mySecurePassword123';

      mockGetPassword.mockResolvedValue(correctPassword);

      const result = await confirmPassword(correctPassword);

      expect(result).toBe(true);
      expect(mockGetPassword).toHaveBeenCalled();
    });

    it('should return false when password is incorrect', async () => {
      const { confirmPassword } = useAutoLogin();

      mockGetPassword.mockResolvedValue('correctPassword');

      const result = await confirmPassword('wrongPassword');

      expect(result).toBe(false);
    });

    it('should return false when password is empty', async () => {
      const { confirmPassword } = useAutoLogin();

      mockGetPassword.mockResolvedValue('somePassword');

      const result = await confirmPassword('');

      expect(result).toBe(false);
    });

    it('should update lastPasswordConfirmed timestamp when password is correct', async () => {
      const frontendStore = useFrontendSettingsStore();
      const { confirmPassword } = useAutoLogin();
      const correctPassword = 'testPassword';

      mockGetPassword.mockResolvedValue(correctPassword);

      const beforeTime = dayjs().unix();
      await confirmPassword(correctPassword);
      const afterTime = dayjs().unix();

      const updatedTimestamp = frontendStore.lastPasswordConfirmed;
      expect(updatedTimestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(updatedTimestamp).toBeLessThanOrEqual(afterTime);
    });

    it('should not update timestamp when password is incorrect', async () => {
      const frontendStore = useFrontendSettingsStore();
      const { confirmPassword } = useAutoLogin();

      const initialTimestamp = frontendStore.lastPasswordConfirmed;
      mockGetPassword.mockResolvedValue('correctPassword');

      await confirmPassword('wrongPassword');

      expect(frontendStore.lastPasswordConfirmed).toBe(initialTimestamp);
    });

    it('should set needsPasswordConfirmation to false when password is correct', async () => {
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      const { confirmPassword } = useAutoLogin();
      const correctPassword = 'test123';

      set(needsPasswordConfirmation, true);
      mockGetPassword.mockResolvedValue(correctPassword);

      await confirmPassword(correctPassword);

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should handle special characters in password', async () => {
      const { confirmPassword } = useAutoLogin();
      const specialPassword = 'p@$$w0rd!#$%^&*()';

      mockGetPassword.mockResolvedValue(specialPassword);

      const result = await confirmPassword(specialPassword);

      expect(result).toBe(true);
    });

    it('should compare passwords case-sensitively', async () => {
      const { confirmPassword } = useAutoLogin();

      mockGetPassword.mockResolvedValue('Password123');

      const resultLower = await confirmPassword('password123');
      expect(resultLower).toBe(false);

      const resultCorrect = await confirmPassword('Password123');
      expect(resultCorrect).toBe(true);
    });

    it('should handle getPassword rejection', async () => {
      const { confirmPassword } = useAutoLogin();

      mockGetPassword.mockRejectedValue(new Error('Failed to get password'));

      await expect(confirmPassword('anyPassword')).rejects.toThrow('Failed to get password');
    });
  });
});
