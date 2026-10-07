import { assert } from '@rotki/common';
import { onSessionEnd } from '@/modules/core/session/session-lifecycle';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { useSessionMonitor } from '@/modules/shell/app/use-session-monitor';

/**
 * Builds the live session's monitor and hands it to `useMonitorService`. Call it from the setup of
 * the component rendered once per session.
 *
 * @remarks
 * The monitor lives in its own effect scope, stopped synchronously the moment the session ends:
 * its pollers stop before anything else can run, and its watchers are gone before the stores they
 * watch are reset, even the ones the end listeners change. The component itself only unmounts on
 * the next render.
 */
export function useSessionHost(): void {
  const scope = effectScope();
  const monitor = scope.run(() => useSessionMonitor());
  assert(monitor, 'the session monitor was not built');

  const withdraw = useMonitorService().host(monitor);
  const removeEndListener = onSessionEnd('session-host', () => scope.stop());

  onScopeDispose(() => {
    removeEndListener();
    withdraw();
    scope.stop();
  });
}
