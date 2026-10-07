import { startPromise } from '@shared/utils';
import { useAutoLogoutNotice } from '@/modules/auth/auto-logout/use-auto-logout-notice';
import { useLogout } from '@/modules/auth/use-logout';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSingleTab } from '@/modules/session/single-tab/use-single-tab';
import { useSetting } from '@/modules/settings/use-setting';

const MINUTE_MS = 60_000;

/** The input that counts as the user being present. */
const ACTIVITY_EVENTS = ['keydown', 'pointerdown', 'pointermove', 'touchstart', 'wheel'];

/**
 * Logs the user out after `autoLogoutPeriod` minutes without input, when the setting is on.
 *
 * @remarks
 * Idle time is measured against the wall clock, and every input checks it before counting as
 * activity. A timer alone is not enough: it does not advance while the machine sleeps, and the
 * first mouse move after waking, or after the window comes back from the tray, would otherwise
 * reset the period and keep the session open for whoever is at the keyboard. For the same reason
 * the window becoming visible or focused is checked but never counts as activity.
 *
 * The logout forgets the password saved for auto-login, as the menu logout does, since the login
 * screen would otherwise unlock the profile again straight away.
 *
 * Runs only in the tab that owns the session, so a background tab of the web app does not log out
 * the user while they work in another.
 */
export function useAutoLogout(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const autoLogoutPeriod = useSetting('autoLogoutPeriod');
  const { isActiveTab } = useSingleTab();
  const { logout } = useLogout();
  const { dismiss, show } = useAutoLogoutNotice();

  const periodMs = computed<number>(() => Math.max(get(autoLogoutPeriod), 0) * MINUTE_MS);
  const armed = computed<boolean>(() => get(logged) && get(isActiveTab) && get(periodMs) > 0);

  let lastActive = Date.now();
  let timer: ReturnType<typeof setTimeout> | undefined;
  /** Set once the logout starts, since `logged` stays true until its first awaits are done. */
  let locking = false;

  function clearTimer(): void {
    clearTimeout(timer);
    timer = undefined;
  }

  function hasExpired(now: number): boolean {
    return now - lastActive >= get(periodMs);
  }

  function lockSession(): void {
    clearTimer();
    locking = true;
    show(get(autoLogoutPeriod));
    startPromise(logout(true, { forgetSavedPassword: true }));
  }

  function checkIdle(): void {
    if (!get(armed) || locking)
      return;

    const now = Date.now();
    if (hasExpired(now)) {
      lockSession();
      return;
    }
    clearTimeout(timer);
    timer = setTimeout(checkIdle, lastActive + get(periodMs) - now);
  }

  function onActivity(): void {
    if (!get(armed) || locking)
      return;

    const now = Date.now();
    if (hasExpired(now))
      lockSession();
    else
      lastActive = now;
  }

  /** Starts the period afresh on login, on a change of period, and when this tab takes the session over. */
  function restart(isArmed: boolean): void {
    clearTimer();
    locking = false;
    if (!isArmed)
      return;

    lastActive = Date.now();
    checkIdle();
  }

  useEventListener(window, ACTIVITY_EVENTS, onActivity, { capture: true, passive: true });
  useEventListener(window, 'focus', checkIdle);

  watch([armed, periodMs], ([isArmed]) => restart(isArmed), { immediate: true });

  watch(useDocumentVisibility(), (visibility) => {
    if (visibility === 'visible')
      checkIdle();
  });

  watch(logged, (isLogged) => {
    if (isLogged)
      dismiss();
  });

  onScopeDispose(clearTimer);
}
