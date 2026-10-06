import { StarlingServiceStatus } from '@shared/ipc';
import { StarlingMethod, StarlingService } from '@shared/starling/starling-protocol';

type StarlingRequest = (
  method: StarlingMethod,
  params?: Record<string, unknown>,
) => Promise<unknown>;

/**
 * Statuses starling itself reports. `Unavailable` is our own sentinel for
 * "starling is not running", so it never arrives over the wire.
 */
const REPORTED_STATUSES: ReadonlySet<string> = new Set(
  Object.values(StarlingServiceStatus).filter(status => status !== StarlingServiceStatus.UNAVAILABLE),
);

function isServiceStatus(value: unknown): value is StarlingServiceStatus {
  return typeof value === 'string' && REPORTED_STATUSES.has(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function mcpState(service: unknown): StarlingServiceStatus | undefined {
  if (!isRecord(service) || service.name !== StarlingService.MCP)
    return undefined;
  return isServiceStatus(service.state) ? service.state : undefined;
}

export function isMcpCrash(params: unknown): boolean {
  return params !== null
    && typeof params === 'object'
    && 'service' in params
    && params.service === StarlingService.MCP;
}

function nonEmptyField(params: unknown, field: string): string | undefined {
  const value: unknown = isRecord(params) ? params[field] : undefined;
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

/**
 * What to tell the user about a crashed service: starling's reason, led by the service when the
 * event names it, since the reason alone ("exited with code 1") does not say which service died.
 */
export function crashMessage(params: unknown): string {
  const lastError = nonEmptyField(params, 'lastError');
  const service = nonEmptyField(params, 'service');
  if (service) {
    const reason = lastError ? ` (${lastError})` : '';
    return `The rotki backend service '${service}' stopped unexpectedly${reason}. Please check the logs for more details.`;
  }
  return lastError ?? 'The rotki backend stopped unexpectedly. Please check the logs for more details.';
}

export async function getMcpServerState(request: StarlingRequest): Promise<StarlingServiceStatus> {
  const status = await request(StarlingMethod.STATUS);
  if (!isRecord(status) || !Array.isArray(status.services))
    return StarlingServiceStatus.UNAVAILABLE;

  for (const service of status.services) {
    const state = mcpState(service);
    if (state)
      return state;
  }
  return StarlingServiceStatus.UNAVAILABLE;
}

/**
 * A service is live once starling has it serving requests. `Degraded` still
 * counts: the process is up, just not fully healthy.
 */
export function isServiceLive(status: StarlingServiceStatus): boolean {
  return status === StarlingServiceStatus.READY || status === StarlingServiceStatus.DEGRADED;
}

export async function setMcpServerRunning(
  request: StarlingRequest,
  running: boolean,
): Promise<StarlingServiceStatus> {
  await request(
    running ? StarlingMethod.START_SERVICE : StarlingMethod.STOP_SERVICE,
    { service: StarlingService.MCP },
  );
  return getMcpServerState(request);
}
