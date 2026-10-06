import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

export const BACKEND_DIRECTORY = 'backend';

/** The packaged-build resource root holding the bundled backend binaries. */
export function resourcesDir(): string {
  return process.resourcesPath ? process.resourcesPath : import.meta.dirname;
}

/**
 * A frozen core's file name, `rotki-core-<version>-<platform>`, as `rotkehlchen.spec` builds it.
 *
 * @remarks
 * The platform suffix is matched exactly, so a renamed copy (`….exe.bak`) or anything else that
 * merely starts with `rotki-core-` is not taken for the core: Windows runs a full path whatever its
 * extension, so a stray copy would otherwise be launched, or make the folder look ambiguous.
 */
const CORE_BINARY_NAME = /^rotki-core-.+-(?:linux|windows\.exe|macos-(?:arm64|x64))$/;

/** The folder a frozen core is looked for in: `<base>/rotki-core/` when it exists, else `<base>` itself. */
export function coreSearchDirectory(backendDirectory: string): string | undefined {
  const candidates = [path.join(backendDirectory, 'rotki-core'), backendDirectory];
  return candidates.find(directory => fs.existsSync(directory) && fs.statSync(directory).isDirectory());
}

/**
 * The single frozen `rotki-core-*` binary under a backend directory, looked for in
 * {@link coreSearchDirectory}. Returns the binary and its directory (the cwd the
 * backend expects), or undefined when there is no frozen build there - absence is
 * fatal only for a packaged build, so the callers decide. Two binaries is
 * ambiguous either way and always throws.
 */
export function findCoreBinary(backendDirectory: string): { binary: string; dir: string } | undefined {
  const dir = coreSearchDirectory(backendDirectory);
  if (!dir)
    return undefined;

  const binaries = fs.readdirSync(dir).filter(file => CORE_BINARY_NAME.test(file));
  if (binaries.length === 0)
    return undefined;
  if (binaries.length > 1)
    throw new Error(`Expected one rotki-core binary but found: ${binaries.join(', ')}. This might indicate a problematic upgrade.`);

  return { binary: path.join(dir, binaries[0]), dir };
}

/** Where a packaged build keeps its core, shared by the launcher and the health check so they cannot disagree. */
export function packagedBackendDirectory(): string {
  return path.join(resourcesDir(), BACKEND_DIRECTORY);
}

/** The packaged core binary; a packaged build without one cannot start. */
export function resolveCoreBinary(): { binary: string; dir: string } {
  const backendDirectory = packagedBackendDirectory();
  const resolved = findCoreBinary(backendDirectory);
  if (!resolved)
    throw new Error(`No rotki-core binary found under ${backendDirectory}`);

  return resolved;
}
