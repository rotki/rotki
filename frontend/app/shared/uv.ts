import { execSync } from 'node:child_process';
import process from 'node:process';

/**
 * Probing uv shells out, and the answer cannot change within a single run, so it
 * is resolved once. `null` means uv is not on PATH.
 */
let cachedVersion: string | null | undefined;

/** The `uv --version` output, or `null` when uv is not on PATH. Cached. */
export function uvVersion(): string | null {
  if (cachedVersion === undefined) {
    try {
      cachedVersion = execSync('uv --version', { encoding: 'utf-8' }).trim();
    }
    catch {
      cachedVersion = null;
    }
  }
  return cachedVersion;
}

/** Whether uv is installed and usable. */
export function isUvAvailable(): boolean {
  return uvVersion() !== null;
}

/**
 * Whether the python backend should be launched through uv rather than the
 * interpreter on PATH. An active virtualenv wins: the developer chose it, and its
 * `python` already resolves. Without one, bare `python` is almost never the right
 * interpreter, so uv resolves it against the repo's `uv.lock` instead.
 *
 * Shared so the dev prerequisites check and the starling launcher cannot drift on
 * a decision that has to agree — one refuses to start when it is false, the other
 * picks the interpreter it implies.
 */
export function shouldUseUv(): boolean {
  if (process.env.VIRTUAL_ENV)
    return false;
  return isUvAvailable();
}
