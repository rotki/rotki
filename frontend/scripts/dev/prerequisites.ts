import { execSync } from 'node:child_process';
import net from 'node:net';
import process from 'node:process';
import { MAX_PORT } from '../dev-instance';
import { createDevLogger } from './logger';

const logger = createDevLogger('dev:prerequisites');

let useUvForPython = false;

export function isUsingUvForPython(): boolean {
  return useUvForPython;
}

function checkForCargo(): boolean {
  try {
    const cargoVersion = execSync('cargo --version', { encoding: 'utf-8' });
    logger.info(`detected cargo: ${cargoVersion.trim()}`);
    return /cargo\s\d+\.\d+\.\d+/.test(cargoVersion);
  }
  catch {
    return false;
  }
}

function checkForUv(): boolean {
  try {
    const uvVersion = execSync('uv --version', { encoding: 'utf-8' });
    logger.info(`detected uv: ${uvVersion.trim()}`);
    return true;
  }
  catch {
    return false;
  }
}

export function ensurePrerequisites(): void {
  if (!process.env.VIRTUAL_ENV) {
    if (checkForUv()) {
      useUvForPython = true;
      logger.info('No python virtualenv active; invoking the backend via `uv run`.');
    }
    else {
      logger.error(
        'No python virtualenv active and `uv` is not on PATH.\n'
        + 'Activate a venv (e.g. `source .venv/bin/activate`) or install uv (https://docs.astral.sh/uv/).',
      );
      process.exit(1);
    }
  }

  if (!checkForCargo()) {
    logger.error('Cargo is not available — install the Rust toolchain via https://rustup.rs/ and re-run.');
    process.exit(1);
  }
}

/**
 * When a python virtualenv is active, confirm the `rotkehlchen` package is
 * actually installed AND answers. A common fresh-worktree footgun is activating a
 * venv but forgetting to sync the backend deps: `python -m rotkehlchen` then fails
 * at spawn time and the dev server just times out waiting for a backend that never
 * came up. `python -m rotkehlchen version` imports the package and runs its entry
 * point, so it catches both a missing install and an import that blows up — a
 * stronger signal than merely resolving the module.
 *
 * The uv path is skipped: `uv run` resolves the project and its deps itself.
 */
export function verifyBackendReady(): void {
  const venv = process.env.VIRTUAL_ENV;
  if (!venv)
    return;
  try {
    const version = execSync('python -m rotkehlchen version', { encoding: 'utf-8' }).trim();
    logger.info(`detected rotkehlchen ${version} in the active virtualenv`);
  }
  catch {
    logger.error(
      `A python virtualenv is active (${venv}) but \`rotkehlchen\` did not answer.\n`
      + 'It is likely not installed there — sync the backend deps (`uv sync`) or install it '
      + 'editable (`pip install -e .`) and re-run.',
    );
    process.exit(1);
  }
}

export function parsePort(raw: string | undefined, defaultValue: number): number {
  if (!raw)
    return defaultValue;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0 || n > MAX_PORT)
    return defaultValue;
  return n;
}

export function getDebuggerPort(): number | null {
  const raw = process.env.DEBUGGER_PORT;
  if (!raw)
    return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 && n <= MAX_PORT ? n : null;
}

async function isPortAvailable(port: number): Promise<boolean> {
  return new Promise<boolean>((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE' || err.code === 'EACCES')
        resolve(false);
      else
        reject(err);
    });
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

export async function selectPort(startPort: number): Promise<number> {
  for (let port = startPort; port <= MAX_PORT; port++) {
    if (await isPortAvailable(port))
      return port;
  }
  throw new Error('no free ports found');
}
