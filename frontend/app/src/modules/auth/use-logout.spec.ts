import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLogout } from '@/modules/auth/use-logout';
import { endSession, hasLiveSession, onPendingWrite } from '@/modules/core/session/session-lifecycle';

const mockNavigateToUserLogin = vi.fn();
const mockCallLogout = vi.fn();
const mockGetLoggedUsers = vi.fn();
const mockDisconnectWallet = vi.fn();
const mockNotifyUserLogout = vi.fn();
const mockResetMcpSession = vi.fn();
const mockResetTray = vi.fn();
const mockSetMessage = vi.fn();
const mockClearPassword = vi.fn();
const mockInterop = { isPackaged: false };
const mockSavedRememberPassword = ref<string | null>(null);
const mockLogged = ref<boolean>(true);
const mockUsername = ref<string>('testuser');

vi.mock('@/modules/auth/use-remember-settings', () => ({
  useRememberSettings: vi.fn(() => ({
    savedRememberPassword: mockSavedRememberPassword,
  })),
}));

vi.mock('@/modules/shell/layout/use-navigation', () => ({
  useAppNavigation: vi.fn(() => ({
    navigateToUserLogin: mockNavigateToUserLogin,
  })),
}));

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
    logout: mockCallLogout,
    loggedUsers: mockGetLoggedUsers,
  })),
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  disconnectWalletIfActive: async (): Promise<void> => mockDisconnectWallet(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => createMock<ReturnType<typeof useInterop>>({
    clearPassword: mockClearPassword,
    isPackaged: mockInterop.isPackaged,
    notifyUserLogout: mockNotifyUserLogout,
    resetMcpSession: mockResetMcpSession,
    resetTray: mockResetTray,
  })),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: vi.fn(() => ({
    setMessage: mockSetMessage,
  })),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({
    logged: mockLogged,
    username: mockUsername,
  })),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: createMock<RotkiApi>({
    cancel: vi.fn(),
    cancelAllQueued: vi.fn(),
  }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    debug: vi.fn(),
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
    set(mockSavedRememberPassword, null);
    mockInterop.isPackaged = false;

    mockCallLogout.mockResolvedValue(undefined);
    mockDisconnectWallet.mockResolvedValue(undefined);
    mockNavigateToUserLogin.mockResolvedValue(undefined);
    mockGetLoggedUsers.mockResolvedValue([]);
    mockResetMcpSession.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('logout', () => {
    it('should end the session before anything else in the logout runs', async () => {
      const liveAt: boolean[] = [];
      mockNotifyUserLogout.mockImplementation(() => {
        liveAt.push(hasLiveSession());
      });
      expect(hasLiveSession()).toBe(true);

      const { logout } = useLogout();
      await logout();
      await flushPromises();

      expect(liveAt).toEqual([false]);
    });

    it('should finish the writes persisting the user\'s input while the session is still live', async () => {
      const liveAtWrite: boolean[] = [];
      const remove = onPendingWrite('spec', async () => {
        liveAtWrite.push(hasLiveSession());
      });

      const { logout } = useLogout();
      await logout();
      remove();

      expect(liveAtWrite).toEqual([true]);
      expect(hasLiveSession()).toBe(false);
    });

    it('should reset the MCP session after backend logout', async () => {
      const callOrder: string[] = [];
      mockCallLogout.mockImplementation(async () => {
        callOrder.push('backendLogout');
      });
      mockResetMcpSession.mockImplementation(async () => {
        callOrder.push('resetMcpSession');
      });

      const { logout } = useLogout();

      await logout();

      expect(callOrder).toEqual(['backendLogout', 'resetMcpSession']);
    });

    it('should show a failed backend logout although its session has ended', async () => {
      mockCallLogout.mockRejectedValue(new Error('backend down'));

      const { logout } = useLogout();
      await logout();

      expect(hasLiveSession()).toBe(false);
      expect(mockSetMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'backend down', title: 'Logout failed' }), { sessionless: true });
    });

    it('should show a failed MCP logout although its session has ended', async () => {
      mockResetMcpSession.mockRejectedValue(new Error('mcp down'));

      const { logout } = useLogout();
      await logout();

      expect(mockSetMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'mcp down', title: 'MCP logout failed' }), { sessionless: true });
    });
  });

  describe('logoutRemoteSession', () => {
    it('should show its failure on the logged-out screen', async () => {
      mockGetLoggedUsers.mockRejectedValue(new Error('unreachable'));
      endSession();

      const { logoutRemoteSession } = useLogout();
      const status = await logoutRemoteSession();

      expect(status).toEqual({ message: 'unreachable', success: false });
      expect(mockSetMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'unreachable', title: 'Remote session logout failure' }), { sessionless: true });
    });
  });

  describe('forgetting the saved password', () => {
    /**
     * Only the packaged build stores the password, and only when the user asked it to. Clearing it
     * is what stops the login screen from unlocking the profile again for whoever is at the machine.
     */
    it('should clear a password the desktop build remembered', async () => {
      mockInterop.isPackaged = true;
      set(mockSavedRememberPassword, 'true');

      await useLogout().logout(true, { forgetSavedPassword: true });

      expect(mockClearPassword).toHaveBeenCalledTimes(1);
      expect(mockCallLogout).toHaveBeenCalledWith('testuser');
    });

    it('should keep the password when the caller does not ask to forget it', async () => {
      mockInterop.isPackaged = true;
      set(mockSavedRememberPassword, 'true');

      await useLogout().logout();

      expect(mockClearPassword).not.toHaveBeenCalled();
    });

    it('should clear nothing when the password was never remembered', async () => {
      mockInterop.isPackaged = true;

      await useLogout().logout(true, { forgetSavedPassword: true });

      expect(mockClearPassword).not.toHaveBeenCalled();
    });

    it('should clear nothing in a browser, which stores no password', async () => {
      set(mockSavedRememberPassword, 'true');

      await useLogout().logout(true, { forgetSavedPassword: true });

      expect(mockClearPassword).not.toHaveBeenCalled();
    });
  });

  it('should skip the backend call but still clean up locally after a restart', async () => {
    const { logout } = useLogout();
    await logout(true, { skipBackendCall: true });
    await flushPromises();

    expect(mockCallLogout).not.toHaveBeenCalled();
    expect(mockDisconnectWallet).toHaveBeenCalled();
    expect(hasLiveSession()).toBe(false);
    expect(mockResetTray).toHaveBeenCalled();
    expect(mockNavigateToUserLogin).toHaveBeenCalled();
    expect(get(mockLogged)).toBe(false);
  });
});
