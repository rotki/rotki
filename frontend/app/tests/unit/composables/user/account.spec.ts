import { beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';

import type ActionSuccess from '@/types/action';

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

describe('user/account', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('existing account', () => {
    beforeEach(() => {
      const { login } = useSessionStore();
      const { logged } = storeToRefs(useSessionAuthStore());

      vi.mocked(login).mockImplementation(async (): Promise<ActionSuccess> => {
        set(logged, true);
        return {
          success: true
        };
      });
    });

    test('non premium users should see the premium dialog', async () => {
      const { userLogin } = useAccountManagement();
      const { isPremiumDialogVisible } = usePremiumReminder();
      const { premiumUserLoggedIn } = useInterop();

      await userLogin({ username: 'test', password: '1234' });
      expect(get(isPremiumDialogVisible)).toBe(true);
      expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
    });

    test('premium users should not see the premium dialog', async () => {
      const { premium } = storeToRefs(usePremiumStore());
      const { userLogin } = useAccountManagement();
      const { isPremiumDialogVisible } = usePremiumReminder();
      const { premiumUserLoggedIn } = useInterop();

      set(premium, true);

      await userLogin({ username: 'test', password: '1234' });
      expect(get(isPremiumDialogVisible)).toBe(false);
      expect(premiumUserLoggedIn).toHaveBeenCalledWith(true);
    });
  });

  describe('new account', () => {
    beforeEach(() => {
      const { createAccount } = useSessionStore();
      const { logged } = storeToRefs(useSessionAuthStore());

      vi.mocked(createAccount).mockImplementation(
        async (): Promise<ActionSuccess> => {
          set(logged, true);
          return {
            success: true
          };
        }
      );
    });

    test('non premium users should only see menu', async () => {
      const { createNewAccount } = useAccountManagement();
      const { isPremiumDialogVisible } = usePremiumReminder();
      const { premiumUserLoggedIn } = useInterop();

      await createNewAccount({
        credentials: { username: 'test', password: '1234' }
      });
      expect(get(isPremiumDialogVisible)).toBe(false);
      expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
    });

    test('premium users should not see the premium menu entry', async () => {
      const { createNewAccount } = useAccountManagement();
      const { isPremiumDialogVisible } = usePremiumReminder();
      const { premiumUserLoggedIn } = useInterop();

      await createNewAccount({
        credentials: { username: 'test', password: '1234' }
      });
      expect(get(isPremiumDialogVisible)).toBe(false);
      expect(premiumUserLoggedIn).toHaveBeenCalledWith(true);
    });
  });
});
