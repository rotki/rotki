import type { MoneriumOAuthResult, MoneriumStatus } from './types';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMoneriumOAuth } from './use-monerium-auth';

const getStatus = vi.fn();
const completeOAuthApi = vi.fn();
const disconnectApi = vi.fn();
const logged = ref<boolean>(false);
const allowed = ref<boolean>(false);

vi.mock('@/modules/integrations/monerium/use-monerium-api', () => ({
  useMoneriumOAuthApi: vi.fn().mockImplementation(() => ({
    completeOAuth: completeOAuthApi,
    disconnect: disconnectApi,
    getStatus,
  })),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn().mockImplementation(() => ({ logged })),
}));

vi.mock('@/modules/premium/use-feature-access', () => ({
  PremiumFeature: { MONERIUM: 'monerium' },
  useFeatureAccess: vi.fn().mockImplementation(() => ({ allowed })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

describe('useMoneriumOAuth', () => {
  beforeEach(async () => {
    // useMoneriumOAuth is wrapped in createSharedComposable, so the shared
    // instance persists across tests. Park it in the "skip" branch (logged or
    // premium are false) before clearing mock history, so any prior async
    // effect resolves first.
    set(logged, false);
    set(allowed, false);
    await flushPromises();
    vi.clearAllMocks();
    getStatus.mockResolvedValue({ authenticated: false });
    completeOAuthApi.mockReset();
    disconnectApi.mockReset();
  });

  it('should fetch status when user is logged in and premium feature is allowed', async () => {
    const statusResponse: MoneriumStatus = { authenticated: true, userEmail: 'a@b.com' };
    getStatus.mockResolvedValue(statusResponse);
    set(logged, true);
    set(allowed, true);

    const { authenticated, status } = useMoneriumOAuth();
    await flushPromises();

    expect(getStatus).toHaveBeenCalledTimes(1);
    expect(get(status)).toEqual(statusResponse);
    expect(get(authenticated)).toBe(true);
  });

  it('should not fetch status when user is not logged in', async () => {
    set(logged, false);
    set(allowed, true);

    const { authenticated, status } = useMoneriumOAuth();
    await flushPromises();

    expect(getStatus).not.toHaveBeenCalled();
    expect(get(status)).toBeUndefined();
    expect(get(authenticated)).toBe(false);
  });

  it('should not fetch status when feature is not allowed', async () => {
    set(logged, true);
    set(allowed, false);

    useMoneriumOAuth();
    await flushPromises();

    expect(getStatus).not.toHaveBeenCalled();
  });

  it('should fall back to unauthenticated status when getStatus throws', async () => {
    getStatus.mockRejectedValue(new Error('boom'));
    set(logged, true);
    set(allowed, true);

    const { authenticated, status } = useMoneriumOAuth();
    await flushPromises();

    expect(get(status)).toEqual({ authenticated: false });
    expect(get(authenticated)).toBe(false);
  });

  describe('refreshStatus', () => {
    it('should update status from the api', async () => {
      set(logged, true);
      set(allowed, true);
      const { authenticated, refreshStatus, status } = useMoneriumOAuth();
      await flushPromises();

      getStatus.mockResolvedValueOnce({ authenticated: true, userEmail: 'x@y.com' });
      await refreshStatus();

      expect(get(status)).toEqual({ authenticated: true, userEmail: 'x@y.com' });
      expect(get(authenticated)).toBe(true);
    });

    it('should set authenticated=false when refresh fails', async () => {
      set(logged, true);
      set(allowed, true);
      const { refreshStatus, status } = useMoneriumOAuth();
      await flushPromises();

      getStatus.mockRejectedValueOnce(new Error('network'));
      await refreshStatus();

      expect(get(status)).toEqual({ authenticated: false });
    });

    it('should toggle loading flag around the request', async () => {
      set(logged, true);
      set(allowed, true);
      const { loading, refreshStatus } = useMoneriumOAuth();
      await flushPromises();

      let resolveFn!: (value: MoneriumStatus) => void;
      getStatus.mockImplementationOnce(async () => new Promise<MoneriumStatus>((resolve) => {
        resolveFn = resolve;
      }));

      const promise = refreshStatus();
      expect(get(loading)).toBe(true);
      resolveFn({ authenticated: true });
      await promise;
      expect(get(loading)).toBe(false);
    });
  });

  describe('setStatus', () => {
    it('should update status synchronously', async () => {
      set(logged, true);
      set(allowed, true);
      const { authenticated, setStatus, status } = useMoneriumOAuth();
      await flushPromises();

      setStatus({ authenticated: true, userEmail: 'c@d.com' });

      expect(get(status)).toEqual({ authenticated: true, userEmail: 'c@d.com' });
      expect(get(authenticated)).toBe(true);
    });
  });

  describe('completeOAuth', () => {
    it('should call the api, update status and refresh', async () => {
      const apiResult: MoneriumOAuthResult = {
        defaultProfileId: 'p1',
        message: 'ok',
        profiles: [{ id: 'p1', name: 'profile-1' }],
        userEmail: 'user@example.com',
      };
      completeOAuthApi.mockResolvedValue(apiResult);
      getStatus.mockResolvedValue({ authenticated: true, userEmail: 'user@example.com' });
      set(logged, true);
      set(allowed, true);

      const { completeOAuth, status } = useMoneriumOAuth();
      await flushPromises();

      const result = await completeOAuth('access', 'refresh', 7200);

      expect(completeOAuthApi).toHaveBeenCalledWith('access', 'refresh', 7200);
      expect(result).toEqual(apiResult);
      expect(get(status)?.authenticated).toBe(true);
    });

    it('should default expiresIn to 3600 seconds when not provided', async () => {
      completeOAuthApi.mockResolvedValue({ message: 'ok' });
      getStatus.mockResolvedValue({ authenticated: true });
      set(logged, true);
      set(allowed, true);

      const { completeOAuth } = useMoneriumOAuth();
      await flushPromises();

      await completeOAuth('a', 'r');

      expect(completeOAuthApi).toHaveBeenCalledWith('a', 'r', 3600);
    });

    it('should propagate api errors', async () => {
      completeOAuthApi.mockRejectedValue(new Error('oauth failed'));
      set(logged, true);
      set(allowed, true);

      const { completeOAuth } = useMoneriumOAuth();
      await flushPromises();

      await expect(completeOAuth('a', 'r')).rejects.toThrow('oauth failed');
    });
  });

  describe('disconnect', () => {
    it('should call api and refresh status to unauthenticated', async () => {
      disconnectApi.mockResolvedValue(true);
      getStatus.mockResolvedValue({ authenticated: false });
      set(logged, true);
      set(allowed, true);

      const { authenticated, disconnect, status } = useMoneriumOAuth();
      await flushPromises();

      await disconnect();

      expect(disconnectApi).toHaveBeenCalled();
      expect(get(status)).toEqual({ authenticated: false });
      expect(get(authenticated)).toBe(false);
    });

    it('should propagate api errors', async () => {
      disconnectApi.mockRejectedValue(new Error('disconnect failed'));
      set(logged, true);
      set(allowed, true);

      const { disconnect } = useMoneriumOAuth();
      await flushPromises();

      await expect(disconnect()).rejects.toThrow('disconnect failed');
    });
  });
});
