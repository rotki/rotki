import type { McpServiceState } from '@shared/ipc';

type StarlingRequest = (
  method: string,
  params?: Record<string, unknown>,
) => Promise<unknown>;

const MCP_SERVICE_STATES: ReadonlySet<string> = new Set([
  'Degraded',
  'Failed',
  'Idle',
  'Ready',
  'Restarting',
  'Spawning',
  'Stopped',
  'Stopping',
  'WaitingReady',
]);

function isMcpServiceState(value: unknown): value is McpServiceState {
  return typeof value === 'string' && MCP_SERVICE_STATES.has(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function mcpState(service: unknown): McpServiceState | undefined {
  if (!isRecord(service) || service.name !== 'mcp')
    return undefined;
  return isMcpServiceState(service.state) ? service.state : undefined;
}

export function isMcpCrash(params: unknown): boolean {
  return params !== null
    && typeof params === 'object'
    && 'service' in params
    && params.service === 'mcp';
}

export function eventLastError(params: unknown): string {
  if (
    params !== null
    && typeof params === 'object'
    && 'lastError' in params
    && typeof params.lastError === 'string'
    && params.lastError.length > 0
  ) {
    return params.lastError;
  }
  return 'The rotki backend stopped unexpectedly. Please check the logs for more details.';
}

export async function getMcpServerState(request: StarlingRequest): Promise<McpServiceState> {
  const status = await request('status');
  if (!isRecord(status) || !Array.isArray(status.services))
    return 'Unavailable';

  for (const service of status.services) {
    const state = mcpState(service);
    if (state)
      return state;
  }
  return 'Unavailable';
}

export async function setMcpServerRunning(
  request: StarlingRequest,
  running: boolean,
): Promise<McpServiceState> {
  await request(running ? 'startService' : 'stopService', { service: 'mcp' });
  return getMcpServerState(request);
}
