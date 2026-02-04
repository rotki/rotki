import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLogout } from '@/modules/account/use-logout';

const mockResetSchedulerState = vi.fn();
const mockNavigateToUserLogin = vi.fn();
const mockCallLogout = vi.fn();
const mockGetLoggedUsers = vi.fn();
const mockDisconnectWallet = vi.fn();
const mockNotifyUserLogout = vi.fn();
const mockResetTray = vi.fn();
const mockSetMessage = vi.fn();
const mockLogged = ref<boolean>(true);
const mockUsername = ref<string>('testuser');

vi.mock('@/composables/session/use-scheduler-state', () => ({
  useSchedulerState: vi.fn(() => ({
    reset: mockResetSchedulerState,
  })),
}));

vi.mock('@/composables/navigation', () => ({
  useAppNavigation: vi.fn(() => ({
    navigateToUserLogin: mockNavigateToUserLogin,
  })),
}));

vi.mock('@/composables/api/session/users', () => ({
  useUsersApi: vi.fn(() => ({
    logout: mockCallLogout,
    loggedUsers: mockGetLoggedUsers,
  })),
}));

vi.mock('@/modules/onchain/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({
    disconnect: mockDisconnectWallet,
  })),
}));

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn(() => ({
    notifyUserLogout: mockNotifyUserLogout,
    resetTray: mockResetTray,
  })),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: vi.fn(() => ({
    setMessage: mockSetMessage,
  })),
}));

vi.mock('@/store/session/auth', () => ({
  useSessionAuthStore: vi.fn(() => ({
    logged: mockLogged,
    username: mockUsername,
  })),
}));

vi.mock('@/modules/api', () => ({
  api: {
    cancelAllQueued: vi.fn(),
    cancel: vi.fn(),
  },
}));

vi.mock('@/utils/logging', () => ({
  logger: {
    error: vi.fn(),
  },
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core');
  return {
    ...actual,
    promiseTimeout: vi.fn().mockResolvedValue(undefined),
  };
});

describe('modules::account::use-logout', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);

    set(mockLogged, true);
    set(mockUsername, 'testuser');

    mockCallLogout.mockResolvedValue(undefined);
    mockDisconnectWallet.mockResolvedValue(undefined);
    mockNavigateToUserLogin.mockResolvedValue(undefined);
    mockGetLoggedUsers.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('logout', () => {
    it('should call resetSchedulerState when logout is called', async () => {
      const { logout } = useLogout();

      await logout();
      await flushPromises();

      expect(mockResetSchedulerState).toHaveBeenCalledTimes(1);
    });

    it('should call resetSchedulerState before other logout operations', async () => {
      const callOrder: string[] = [];

      mockResetSchedulerState.mockImplementation(() => {
        callOrder.push('resetSchedulerState');
      });
      mockNotifyUserLogout.mockImplementation(() => {
        callOrder.push('notifyUserLogout');
      });
      mockDisconnectWallet.mockImplementation(async () => {
        callOrder.push('disconnectWallet');
      });

      const { logout } = useLogout();

      await logout();
      await flushPromises();

      expect(callOrder[0]).toBe('resetSchedulerState');
      expect(callOrder).toContain('notifyUserLogout');
      expect(callOrder).toContain('disconnectWallet');
    });

    it('should call resetSchedulerState even if logout fails', async () => {
      mockCallLogout.mockRejectedValue(new Error('Logout failed'));

      const { logout } = useLogout();

      await logout();
      await flushPromises();

      expect(mockResetSchedulerState).toHaveBeenCalledTimes(1);
    });
  });
});
