import dayjs from 'dayjs';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePasswordConfirmation } from '@/modules/account/use-password-confirmation';
import { Constraints } from '@/modules/common/constraints';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const mockInterop = vi.hoisted(() => ({
  getPassword: vi.fn(),
  isPackaged: true,
  logToFile: vi.fn(),
  premiumUserLoggedIn: vi.fn(),
}));

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue(mockInterop),
}));

const REMEMBER_PASSWORD_KEY = 'rotki.remember_password';

describe('usePasswordConfirmation', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.clearAllMocks();
    mockInterop.isPackaged = true;
    localStorage.setItem(REMEMBER_PASSWORD_KEY, 'true');
  });

  afterEach(() => {
    localStorage.removeItem(REMEMBER_PASSWORD_KEY);
  });

  describe('checkIfPasswordConfirmationNeeded', () => {
    it('should not trigger when isPackaged is false', async () => {
      mockInterop.isPackaged = false;
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix() - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should not trigger when rememberPassword is disabled', async () => {
      localStorage.removeItem(REMEMBER_PASSWORD_KEY);
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix() - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should not trigger when password confirmation is disabled', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: false,
        lastPasswordConfirmed: 0,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });

    it('should initialize lastPasswordConfirmed when it is 0', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      const beforeTime = dayjs().unix();

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: 0,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');
      const afterTime = dayjs().unix();

      expect(get(needsPasswordConfirmation)).toBe(false);
      expect(frontendStore.lastPasswordConfirmed).toBeGreaterThanOrEqual(beforeTime);
      expect(frontendStore.lastPasswordConfirmed).toBeLessThanOrEqual(afterTime);
    });

    it('should not trigger when interval has not elapsed', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix(),
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
      expect(mockInterop.getPassword).not.toHaveBeenCalled();
    });

    it('should trigger when interval has elapsed and password exists', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('storedPassword');

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix() - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 100,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(true);
    });

    it('should not trigger when no stored password exists', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue(undefined);

      const frontendStore = useFrontendSettingsStore();
      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, false);

      frontendStore.update({
        enablePasswordConfirmation: true,
        lastPasswordConfirmed: dayjs().unix() - Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS - 1,
        passwordConfirmationInterval: Constraints.PASSWORD_CONFIRMATION_MIN_SECONDS,
      });

      const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
      await checkIfPasswordConfirmationNeeded('testUser');

      expect(get(needsPasswordConfirmation)).toBe(false);
    });
  });

  describe('confirmPassword', () => {
    it('should return true and reset state when password matches', async () => {
      const correctPassword = 'mySecurePassword123';
      vi.mocked(mockInterop.getPassword).mockResolvedValue(correctPassword);

      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, true);

      const frontendStore = useFrontendSettingsStore();
      const beforeTime = dayjs().unix();

      const { confirmPassword } = usePasswordConfirmation();
      const result = await confirmPassword(correctPassword);
      const afterTime = dayjs().unix();

      expect(result).toBe(true);
      expect(get(needsPasswordConfirmation)).toBe(false);
      expect(frontendStore.lastPasswordConfirmed).toBeGreaterThanOrEqual(beforeTime);
      expect(frontendStore.lastPasswordConfirmed).toBeLessThanOrEqual(afterTime);
    });

    it('should return false when password does not match', async () => {
      vi.mocked(mockInterop.getPassword).mockResolvedValue('correctPassword');

      const authStore = useSessionAuthStore();
      const { needsPasswordConfirmation } = storeToRefs(authStore);
      set(needsPasswordConfirmation, true);

      const { confirmPassword } = usePasswordConfirmation();
      const result = await confirmPassword('wrongPassword');

      expect(result).toBe(false);
      expect(get(needsPasswordConfirmation)).toBe(true);
    });
  });
});
