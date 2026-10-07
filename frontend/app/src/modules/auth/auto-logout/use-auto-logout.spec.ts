import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { useAutoLogout } from '@/modules/auth/auto-logout/use-auto-logout';
import { useAutoLogoutNotice } from '@/modules/auth/auto-logout/use-auto-logout-notice';

const { isActiveTab, logged, logout, period } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    isActiveTab: ref<boolean>(true),
    logged: ref<boolean>(true),
    logout: vi.fn<(navigate?: boolean, options?: { forgetSavedPassword?: boolean }) => Promise<void>>(),
    period: ref<number>(-1),
  };
});

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): { logout: typeof logout } => ({ logout }),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): { logged: typeof logged } => ({ logged }),
}));

vi.mock('@/modules/session/single-tab/use-single-tab', () => ({
  useSingleTab: (): { isActiveTab: typeof isActiveTab } => ({ isActiveTab }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): typeof period => period,
}));

const MINUTE = 60_000;

let scope: ReturnType<typeof effectScope> | undefined;

function startTracking(): void {
  scope = effectScope();
  scope.run(() => useAutoLogout());
}

function moveMouse(): void {
  window.dispatchEvent(new Event('pointermove'));
}

/** Moves the wall clock without running any timer, as a machine waking from sleep sees it. */
function sleepFor(ms: number): void {
  vi.setSystemTime(Date.now() + ms);
}

describe('useAutoLogout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    logout.mockResolvedValue(undefined);
    set(isActiveTab, true);
    set(logged, true);
    set(period, 15);
    useAutoLogoutNotice().dismiss();
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
    vi.useRealTimers();
    vi.restoreAllMocks();
    logout.mockReset();
  });

  describe('when the period passes without input', () => {
    it('should log out and forget the saved password', () => {
      startTracking();

      vi.advanceTimersByTime(15 * MINUTE);

      expect(logout).toHaveBeenCalledExactlyOnceWith(true, { forgetSavedPassword: true });
    });

    it('should tell the login screen how long the session was idle', () => {
      startTracking();

      vi.advanceTimersByTime(15 * MINUTE);

      expect(get(useAutoLogoutNotice().idleMinutes)).toBe(15);
    });

    it('should not log out a moment before the period ends', () => {
      startTracking();

      vi.advanceTimersByTime(15 * MINUTE - 1);

      expect(logout).not.toHaveBeenCalled();
    });
  });

  it('should count the period again from the last input', () => {
    startTracking();

    vi.advanceTimersByTime(10 * MINUTE);
    moveMouse();
    vi.advanceTimersByTime(10 * MINUTE);

    expect(logout).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5 * MINUTE);

    expect(logout).toHaveBeenCalledTimes(1);
  });

  describe('after the machine slept through the period', () => {
    it('should log out on the first input instead of counting it as activity', () => {
      startTracking();

      sleepFor(60 * MINUTE);
      moveMouse();

      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('should log out as soon as the window is shown again', async () => {
      const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
      startTracking();

      sleepFor(60 * MINUTE);
      visibility.mockReturnValue('visible');
      document.dispatchEvent(new Event('visibilitychange'));
      await nextTick();

      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('should log out as soon as the window is focused again', () => {
      startTracking();

      sleepFor(60 * MINUTE);
      window.dispatchEvent(new Event('focus'));

      expect(logout).toHaveBeenCalledTimes(1);
    });
  });

  it('should not count focusing the window as activity', () => {
    startTracking();

    vi.advanceTimersByTime(10 * MINUTE);
    window.dispatchEvent(new Event('focus'));
    vi.advanceTimersByTime(5 * MINUTE);

    expect(logout).toHaveBeenCalledTimes(1);
  });

  it('should log out once even when input arrives while the logout runs', () => {
    logout.mockReturnValue(new Promise<void>(() => {}));
    startTracking();

    sleepFor(60 * MINUTE);
    moveMouse();
    moveMouse();
    window.dispatchEvent(new Event('focus'));

    expect(logout).toHaveBeenCalledTimes(1);
  });

  describe('should never log out', () => {
    it('while the setting is off', () => {
      set(period, -1);
      startTracking();

      vi.advanceTimersByTime(24 * 60 * MINUTE);
      moveMouse();

      expect(logout).not.toHaveBeenCalled();
    });

    it('while nobody is logged in', () => {
      set(logged, false);
      startTracking();

      vi.advanceTimersByTime(60 * MINUTE);
      moveMouse();

      expect(logout).not.toHaveBeenCalled();
    });

    it('from a browser tab that another tab took the session from', () => {
      set(isActiveTab, false);
      startTracking();

      vi.advanceTimersByTime(60 * MINUTE);
      moveMouse();

      expect(logout).not.toHaveBeenCalled();
    });
  });

  it('should start the period afresh when it is changed', async () => {
    startTracking();

    vi.advanceTimersByTime(10 * MINUTE);
    set(period, 30);
    await nextTick();
    vi.advanceTimersByTime(29 * MINUTE);

    expect(logout).not.toHaveBeenCalled();

    vi.advanceTimersByTime(MINUTE);

    expect(logout).toHaveBeenCalledTimes(1);
  });

  it('should start counting at login rather than when the app opened', async () => {
    set(logged, false);
    startTracking();

    vi.advanceTimersByTime(60 * MINUTE);
    set(logged, true);
    await nextTick();
    vi.advanceTimersByTime(15 * MINUTE - 1);

    expect(logout).not.toHaveBeenCalled();
  });

  it('should clear the login screen notice on the next login', async () => {
    startTracking();
    vi.advanceTimersByTime(15 * MINUTE);
    set(logged, false);
    await nextTick();

    set(logged, true);
    await nextTick();

    expect(get(useAutoLogoutNotice().idleMinutes)).toBeUndefined();
  });
});
