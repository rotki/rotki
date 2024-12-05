import { beforeAll, describe, expect, it, vi } from 'vitest';
import { useSessionStore } from '@/store/session';
import { useAccountManagement } from '@/composables/user/account';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
}));

vi.mock('@/store/session', () => ({
  useSessionStore: vi.fn().mockReturnValue({
    login: vi.fn(),
    createAccount: vi.fn(),
  }),
}));

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    premiumUserLoggedIn: vi.fn(),
  }),
}));

describe('composables::user/account', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('existing account', () => {
    const { login } = useSessionStore();

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
    const { createAccount } = useSessionStore();

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
});
