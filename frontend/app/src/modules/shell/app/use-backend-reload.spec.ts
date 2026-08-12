import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendRestartStatus } from '@/modules/shell/app/use-backend-management';
import { useBackendReload } from './use-backend-reload';
import '@test/i18n';

const { connect, logout, notify, restartBackend, sessionState, setConnected } = vi.hoisted(() => ({
  connect: vi.fn(),
  logout: vi.fn(),
  notify: vi.fn(),
  restartBackend: vi.fn(),
  sessionState: { logged: true },
  setConnected: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-backend-management', async importOriginal => ({
  ...(await importOriginal<typeof import('@/modules/shell/app/use-backend-management')>()),
  useBackendManagement: vi.fn(() => ({ restartBackend })),
}));

vi.mock('@/modules/shell/app/use-backend-connection', () => ({
  useBackendConnection: vi.fn(() => ({ connect })),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: vi.fn(() => ({ logout })),
}));

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: vi.fn(() => ({ setConnected })),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn(() => ({ notify })),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  // Built per call so a test can set the flag before the composable reads it.
  useSessionAuthStore: vi.fn(() => ({ logged: ref<boolean>(sessionState.logged) })),
}));

describe('useBackendReload', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    sessionState.logged = true;
    logout.mockResolvedValue(undefined);
  });

  it('should sign the user out and reconnect once the backend has restarted', async () => {
    restartBackend.mockResolvedValue({ status: BackendRestartStatus.restarted });

    const result = await useBackendReload().reload();

    expect(setConnected).toHaveBeenCalledWith(false);
    expect(logout).toHaveBeenCalledWith(true, { skipBackendCall: true });
    expect(connect).toHaveBeenCalled();
    expect(notify).not.toHaveBeenCalled();
    expect(result.status).toBe(BackendRestartStatus.restarted);
  });

  /**
   * The whole point of the outcome: a restart that never happened used to be
   * indistinguishable from one that did, so the flow signed the user out and reported
   * completion regardless, leaving them to sign back in to a backend still holding the
   * data they had just replaced.
   */
  it('should report a refused restart instead of completing the flow', async () => {
    restartBackend.mockResolvedValue({
      message: 'authentication required',
      status: BackendRestartStatus.failed,
    });

    const result = await useBackendReload().reload();

    expect(notify).toHaveBeenCalled();
    expect(logout).not.toHaveBeenCalled();
    // Still reconnected: the backend refused the restart rather than going away, so
    // leaving the app disconnected would break something that is working.
    expect(connect).toHaveBeenCalled();
    expect(result.status).toBe(BackendRestartStatus.failed);
  });

  it('should relay the reason the restart was refused', async () => {
    restartBackend.mockResolvedValue({
      message: 'control is rate-limited; retry shortly',
      status: BackendRestartStatus.failed,
    });

    await useBackendReload().reload();

    expect(notify.mock.calls[0][0].message).toContain('control is rate-limited; retry shortly');
  });

  /**
   * No runtime could restart anything, which is how the plain web build has always
   * behaved. The change was still applied, so the flow completes as it always did - but
   * the logout has to reach the backend. Nothing restarted, so nothing logged the user
   * out on that side, and skipping the HTTP call left the backend holding a session the
   * frontend had already discarded.
   */
  it('should still log out of the backend where no restart is possible at all', async () => {
    restartBackend.mockResolvedValue({ status: BackendRestartStatus.unavailable });

    const result = await useBackendReload().reload();

    expect(notify).not.toHaveBeenCalled();
    expect(logout).toHaveBeenCalledWith(true, { skipBackendCall: false });
    expect(connect).toHaveBeenCalled();
    expect(result.status).toBe(BackendRestartStatus.unavailable);
  });

  it('should skip the logout when no one is signed in', async () => {
    sessionState.logged = false;
    restartBackend.mockResolvedValue({ status: BackendRestartStatus.restarted });

    await useBackendReload().reload();

    expect(logout).not.toHaveBeenCalled();
    expect(connect).toHaveBeenCalled();
  });
});
