import { execSync } from 'node:child_process';
import net from 'node:net';
import os from 'node:os';
import { MAX_PORT, type PortName, portsForSlot } from './port-registry';

async function isPortListening(port: number): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const socket = new net.Socket();
    const finalize = (listening: boolean): void => {
      socket.destroy();
      resolve(listening);
    };
    socket.setTimeout(200);
    socket.once('connect', () => finalize(true));
    socket.once('timeout', () => finalize(false));
    socket.once('error', () => finalize(false));
    socket.connect(port, '127.0.0.1');
  });
}

function runPidProbe(cmd: string, args: string[], pattern: RegExp): number | undefined {
  try {
    const out = execSync([cmd, ...args].join(' '), { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] });
    const match = out.match(pattern);
    return match ? Number.parseInt(match[1], 10) : undefined;
  }
  catch {
    return undefined;
  }
}

function pidForPort(port: number): number | undefined {
  if (!Number.isInteger(port) || port <= 0 || port > MAX_PORT) {
    return undefined;
  }
  const platform = os.platform();
  if (platform === 'linux') {
    return runPidProbe('ss', ['-lntpH', `'sport = :${port}'`], /pid=(\d+)/);
  }
  if (platform === 'darwin') {
    return runPidProbe('lsof', ['-nP', `-iTCP:${port}`, '-sTCP:LISTEN', '-Fp'], /^p(\d+)/m);
  }
  if (platform === 'win32') {
    return runPidProbe('netstat', ['-ano', '-p', 'TCP'], new RegExp(`\\s127\\.0\\.0\\.1:${port}\\s.*LISTENING\\s+(\\d+)`));
  }
  return undefined;
}

export interface LiveProbeResult {
  name: PortName;
  port: number;
  pid?: number;
}

const ALL_PORT_NAMES: readonly PortName[] = ['restApi', 'proxy', 'colibri', 'dev'];

export async function probePortsLive(slot: number): Promise<LiveProbeResult[]> {
  const ports = portsForSlot(slot);
  const results: LiveProbeResult[] = [];
  for (const name of ALL_PORT_NAMES) {
    const port = ports[name];
    if (await isPortListening(port)) {
      results.push({ name, port, pid: pidForPort(port) });
    }
  }
  return results;
}
