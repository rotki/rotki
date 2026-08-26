import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSingleTab } from '@/modules/session/single-tab/use-single-tab';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';

/**
 * Wires same-browser tab coordination ([[useSingleTab]]) into the session lifecycle.
 * Mounted once in `AppHost.vue`, alongside `useSessionStateCleaner`.
 *
 * - On login this tab claims ownership, superseding any older tab of the same browser.
 * - On logout it releases the claim so a backgrounded tab does not keep the lock.
 * - When a newer tab takes over, the monitor is stopped here (websocket + all pollers)
 *   without a backend logout. Reclaiming is a full page reload (see `SingleTabOverlay`),
 *   which reboots the tab clean, so there is no in-place restart to do here.
 */
export function useSingleTabGuard(): void {
  const { claim, isActiveTab, release, supported } = useSingleTab();
  if (!supported)
    return;

  const { logged } = storeToRefs(useSessionAuthStore());
  const { stop } = useMonitorService();

  watch(logged, (isLogged, wasLogged) => {
    if (isLogged)
      claim();
    else if (wasLogged)
      release();
  }, { immediate: true });

  watch(isActiveTab, (isActive) => {
    if (!isActive && get(logged))
      stop();
  }, { immediate: true });
}
