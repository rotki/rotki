import type { LogLevel } from '@shared/log-level';
import type { Ref } from 'vue';
import { StarlingServiceStatus } from '@shared/ipc';
import { StarlingMethod, type StarlingService } from '@shared/starling/starling-protocol';
import { type MessageKey, msg } from '@/message-key';
import {
  ControlCapabilities,
  ControlRpcResponse,
  type ControlServiceStatus,
  ControlStatus,
} from '@/modules/core/control/types';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

/**
 * The one way the app drives the supervisor, whichever runtime it is in.
 *
 * Both transports end at the same control RPC; they differ only in the tunnel.
 * The desktop cannot reach starling's stdio pipe from the renderer, so it goes
 * through Electron IPC, which forwards the very same `startService`/`stopService`
 * calls. Docker posts them to `/_control` on its own origin. Consumers pick
 * neither: they ask this composable, and branch on {@link available} rather than
 * on which runtime they happen to be in.
 */
interface UseControlReturn {
  /** Whether any control operation can be attempted at all. */
  readonly available: Readonly<Ref<boolean>>;
  /**
   * Whether this runtime accepts a restart carrying backend options: data directory, log level,
   * log-rotation size. Desktop only, since `sanitize_restart_options` rejects them on every
   * transport but stdio.
   *
   * @remarks
   * Auto-start is not one of these. It has its own {@link setServiceAutostart}, which every
   * control surface accepts, so do not gate that toggle on this flag.
   */
  readonly supportsOptions: boolean;
  /** Resolve availability once per session. Safe to call repeatedly. */
  probe: () => Promise<boolean>;
  /**
   * One service's live state and its auto-start preference, read together: they
   * come from the same `status` snapshot, so asking for them separately would be
   * two round trips that can disagree.
   */
  serviceInfo: (service: StarlingService) => Promise<ControlServiceInfo>;
  setServiceRunning: (service: StarlingService, running: boolean) => Promise<StarlingServiceStatus>;
  /**
   * Record whether a service comes up with the backend tree from the next start
   * on. Starts and stops nothing: the running state is {@link setServiceRunning}.
   */
  setServiceAutostart: (service: StarlingService, autostart: boolean) => Promise<void>;
  /**
   * Bounce the backend tree with the boot-time layout.
   *
   * `loglevel` is the single setting a non-desktop restart may carry, so a
   * backend that will not come up can be brought back talking. Every other
   * option is refused by the supervisor rather than dropped.
   */
  restart: (loglevel?: LogLevel) => Promise<void>;
}

/** What one service's row in a `status` reply says, reduced to what the app uses. */
export interface ControlServiceInfo {
  readonly autostart: boolean;
  readonly state: StarlingServiceStatus;
}

const CONTROL_ENDPOINT = '/_control';

/**
 * Only a *positive* answer is cached. Whether the route exists cannot change
 * while the page is open, so a yes is durable — but a no can equally mean the
 * proxy was briefly unreachable, and the connection-failure screen probes in
 * exactly that state. Latching that would disable the controls for the rest of
 * the page's life, with a reload the only way out.
 */
const available = ref<boolean>(false);

/** Raised for a JSON-RPC `error` reply, so callers see a refused op as a failure. */
export class ControlError extends Error {
  constructor(readonly code: number, message: string) {
    super(message);
    this.name = 'ControlError';
  }
}

/** Translates a transport-level failure, which carries no message of its own. */
type Translate = (key: MessageKey) => string;

/**
 * Calls one JSON-RPC method on the `/_control` endpoint.
 *
 * @remarks
 * Uses `fetch` rather than the REST client, deliberately: `/_control` is not the rotki API. It sits
 * outside the `/api/1` prefix, speaks JSON-RPC instead of the result/message envelope, and must not
 * pass through the client's snake_case body rewriting or its session and task interceptors.
 *
 * A transport refusal carries only a status, so the user-facing message is written here rather than
 * relayed. Never use the HTTP reason phrase: it is untranslated and says nothing useful.
 *
 * @throws ControlError on a transport refusal, carrying an already-translated message
 */
async function postRpc(
  t: Translate,
  method: StarlingMethod,
  params?: Record<string, unknown>,
): Promise<unknown> {
  const response = await fetch(CONTROL_ENDPOINT, {
    body: JSON.stringify({ id: 1, jsonrpc: '2.0', method, ...(params ? { params } : {}) }),
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });

  if (!response.ok)
    throw new ControlError(response.status, t(transportErrorKey(response.status)));

  const parsed = ControlRpcResponse.parse(await response.json());
  // The supervisor's own message: relayed as-is, the way backend errors are
  // everywhere else in the app.
  if (parsed.error)
    throw new ControlError(parsed.error.code, parsed.error.message);

  return parsed.result;
}

/**
 * Branded with `msg.$t` because the key is resolved later through `t(key)`
 * rather than translated here; the lint rule counts that as a real usage and so
 * will not report these as unused.
 */
function transportErrorKey(status: number): MessageKey {
  if (status === 401)
    return msg.$t('control.errors.unauthorized');
  if (status === 503)
    return msg.$t('control.errors.unavailable');
  if (status === 404)
    return msg.$t('control.errors.not_supported');
  return msg.$t('control.errors.failed');
}

function serviceInfoOf(status: ControlStatus, service: StarlingService): ControlServiceInfo {
  const found = status.services.find((entry: ControlServiceStatus) => entry.name === service);
  // A service the supervisor does not manage has no preference to report, and
  // `false` is the honest answer: nothing is going to start it.
  return { autostart: found?.autostart ?? false, state: found?.state ?? StarlingServiceStatus.UNAVAILABLE };
}

export function useControl(): UseControlReturn {
  const { t } = useI18n({ useScope: 'global' });
  const {
    isPackaged,
    getMcpServerStatus,
    restartBackend,
    setMcpAutoStart,
    startMcpServer,
    stopMcpServer,
  } = useInterop();

  const probe = async (): Promise<boolean> => {
    if (get(available))
      return true;

    if (isPackaged) {
      // The desktop always has a supervisor on the other end of its IPC.
      set(available, true);
      return true;
    }

    try {
      const response = await fetch(CONTROL_ENDPOINT, { credentials: 'same-origin' });
      // A 404 is the honest answer from a deployment with no session cookie
      // configured, not an error to report.
      set(available, response.ok && ControlCapabilities.safeParse(await response.json()).success);
    }
    catch {
      // Offline, or nothing serving. Not cached: it may well be the transient
      // outage that brought the user to the connection-failure screen.
      set(available, false);
    }
    return get(available);
  };

  const serviceInfo = async (service: StarlingService): Promise<ControlServiceInfo> => {
    if (!await probe())
      return { autostart: false, state: StarlingServiceStatus.UNAVAILABLE };

    if (isPackaged) {
      // The desktop's preference is an Electron app setting, not a supervisor
      // one, so it comes back from the same IPC call that reports the state.
      const status = await getMcpServerStatus();
      return { autostart: status.autoStart, state: status.state };
    }

    const status = ControlStatus.parse(await postRpc(t, StarlingMethod.STATUS));
    return serviceInfoOf(status, service);
  };

  const setServiceRunning = async (
    service: StarlingService,
    running: boolean,
  ): Promise<StarlingServiceStatus> => {
    if (!await probe())
      return StarlingServiceStatus.UNAVAILABLE;

    if (isPackaged)
      return (await (running ? startMcpServer() : stopMcpServer())).state;

    await postRpc(t, running ? StarlingMethod.START_SERVICE : StarlingMethod.STOP_SERVICE, { service });
    return (await serviceInfo(service)).state;
  };

  /**
   * Sets whether a service starts with the tree.
   *
   * @remarks
   * The desktop keeps this in Electron's own app settings, where it rides along in the next start's
   * options. Sending the RPC there as well would put the same value in two places with nothing
   * keeping them in step.
   */
  const setServiceAutostart = async (service: StarlingService, autostart: boolean): Promise<void> => {
    if (!await probe())
      return;

    if (isPackaged) {
      await setMcpAutoStart(autostart);
      return;
    }

    await postRpc(t, StarlingMethod.SET_SERVICE_AUTOSTART, { autostart, service });
  };

  /**
   * Restarts the backend, optionally changing the log level.
   *
   * @remarks
   * The desktop keeps its own path: its restart carries the user's whole option set, data and log
   * directories included, which only the stdio transport accepts. Do not flatten the two.
   */
  const restart = async (loglevel?: LogLevel): Promise<void> => {
    if (!await probe())
      return;

    if (isPackaged) {
      await restartBackend(loglevel ? { loglevel } : {}, true);
      return;
    }

    await postRpc(t, StarlingMethod.RESTART, loglevel ? { loglevel } : undefined);
  };

  return {
    available: readonly(available),
    probe,
    restart,
    serviceInfo,
    setServiceAutostart,
    setServiceRunning,
    supportsOptions: isPackaged,
  };
}
