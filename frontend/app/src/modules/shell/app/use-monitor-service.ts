import type { SessionMonitor } from '@/modules/shell/app/use-session-monitor';
import { logger } from '@/modules/core/common/logging/logging';
import { hasLiveSession, onSessionEnd } from '@/modules/core/session/session-lifecycle';

const MonitorIntent = {
  STARTED: 'started',
  STOPPED: 'stopped',
} as const;

type MonitorIntent = { kind: typeof MonitorIntent.STOPPED } | { kind: typeof MonitorIntent.STARTED; restarting: boolean };

const STOPPED: MonitorIntent = { kind: MonitorIntent.STOPPED };

interface UseMonitorServiceReturn {
  /** Starts the live session's monitor, or once the session host has built it. */
  start: (restarting?: boolean) => void;
  stop: () => void;
  restart: () => void;
  /**
   * Hands the facade the live session's monitor, applying a start asked for before it existed.
   *
   * @returns a function that withdraws it
   */
  host: (monitor: SessionMonitor) => () => void;
}

/**
 * Starts and stops the live session's monitor, which the session host builds for each session.
 *
 * @remarks
 * Callers may ask for a start before the host has built the monitor: the unlock flow starts it as
 * soon as it connects, and the host only mounts on the next render after the session began. The
 * wanted state is kept and applied when the host hands its monitor over. A start with no session
 * live is ignored, so it can never carry over into the next session and open the websocket before
 * that session's handshake. When a session ends the wanted state goes back to stopped and its
 * monitor is dropped at once: its host only unmounts on the next render, and starting the ended
 * session's monitor in between would arm pollers nothing could stop.
 */
export const useMonitorService = createGlobalState((): UseMonitorServiceReturn => {
  let hosted: SessionMonitor | undefined;
  let intent: MonitorIntent = STOPPED;

  onSessionEnd('monitor-service', () => {
    intent = STOPPED;
    hosted = undefined;
  });

  function start(restarting = false): void {
    if (!hasLiveSession()) {
      logger.debug('monitor start ignored: no session is live');
      return;
    }
    intent = { kind: MonitorIntent.STARTED, restarting };
    hosted?.start(restarting);
  }

  function stop(): void {
    intent = STOPPED;
    hosted?.stop();
  }

  function restart(): void {
    stop();
    start(true);
  }

  function host(monitor: SessionMonitor): () => void {
    hosted = monitor;
    if (intent.kind === MonitorIntent.STARTED)
      monitor.start(intent.restarting);

    return () => {
      if (hosted === monitor)
        hosted = undefined;
    };
  }

  return { host, restart, start, stop };
});
