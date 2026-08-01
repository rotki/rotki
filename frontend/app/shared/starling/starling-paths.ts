import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

export const BACKEND_DIRECTORY = 'backend';

/** The packaged-build resource root holding the bundled backend binaries. */
export function resourcesDir(): string {
  return process.resourcesPath ? process.resourcesPath : import.meta.dirname;
}

/**
 * The single frozen `rotki-core-*` binary under a backend directory: prefer
 * `<base>/rotki-core/`, fall back to `<base>` itself. Returns the binary and its
 * directory (the cwd the backend expects), or undefined when there is no frozen
 * build there - absence is fatal only for a packaged build, so the callers
 * decide. Two binaries is ambiguous either way and always throws.
 */
export function findCoreBinary(backendDirectory: string): { binary: string; dir: string } | undefined {
  const candidates = [path.join(backendDirectory, 'rotki-core'), backendDirectory];
  const dir = candidates.find(directory => fs.existsSync(directory) && fs.statSync(directory).isDirectory());
  if (!dir)
    return undefined;

  const binaries = fs.readdirSync(dir).filter(file => file.startsWith('rotki-core-'));
  if (binaries.length === 0)
    return undefined;
  if (binaries.length > 1)
    throw new Error(`Expected one rotki-core binary but found: ${binaries.join(', ')}. This might indicate a problematic upgrade.`);

  return { binary: path.join(dir, binaries[0]), dir };
}

/** The packaged core binary; a packaged build without one cannot start. */
export function resolveCoreBinary(): { binary: string; dir: string } {
  const backendDirectory = path.join(resourcesDir(), BACKEND_DIRECTORY);
  const resolved = findCoreBinary(backendDirectory);
  if (!resolved)
    throw new Error(`No rotki-core binary found under ${backendDirectory}`);

  return resolved;
}
