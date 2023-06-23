import { beforeAll, describe, test, vi } from 'vitest';
import { useSessionStore } from '../../../../../src/store/session';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn()
  })
}));

vi.mock('@/store/session', () => ({
  useSessionStore: vi.fn().mockReturnValue({
    login: vi.fn(),
    createAccount: vi.fn()
  })
}));

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    premiumUserLoggedIn: vi.fn()
  })
}));

describe('composables::user/account', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('existing account', () => {
    const { login } = useSessionStore();

    test('login success, should not show error message', async () => {
      const { userLogin, errors } = useAccountManagement();

      vi.mocked(login).mockResolvedValue({
        success: true
      });

      await userLogin({ username: 'test', password: '1234' });

      expect(get(errors)).toStrictEqual([]);
    });

    test('login failed, should show error message', async () => {
      const { userLogin, errors } = useAccountManagement();

      vi.mocked(login).mockResolvedValue({
        success: false,
        message: 'errors'
      });

      await userLogin({ username: 'test', password: '1234' });

      expect(get(errors)).toStrictEqual(['errors']);
    });
  });

  describe('new account', () => {
    const { createAccount } = useSessionStore();

    test('create account success, should not show error message', async () => {
      const { createNewAccount, error } = useAccountManagement();

      vi.mocked(createAccount).mockResolvedValue({
        success: true
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' }
      });

      expect(get(error)).toStrictEqual('');
    });

    test('login failed, should show error message', async () => {
      const { createNewAccount, error } = useAccountManagement();

      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors'
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true }
      });

      expect(get(error)).toStrictEqual('errors');
    });

    test('create account with submitUsageAnalytics true', async () => {
      const { createNewAccount } = useAccountManagement();
      vi.clearAllMocks();
      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors'
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true }
      });

      expect(createAccount).toHaveBeenCalledWith({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: true }
      });
    });

    test('create account with submitUsageAnalytics false', async () => {
      const { createNewAccount } = useAccountManagement();
      vi.clearAllMocks();
      vi.mocked(createAccount).mockResolvedValue({
        success: false,
        message: 'errors'
      });

      await createNewAccount({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: false }
      });

      expect(createAccount).toHaveBeenCalledWith({
        credentials: { username: 'test', password: '1234' },
        initialSettings: { submitUsageAnalytics: false }
      });
    });
  });
});
