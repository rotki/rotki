/**
 * Whether the executables a packaged rotki ships are still on disk and still
 * runnable.
 *
 * @remarks
 * Security software quarantines false positives, and an unsigned native binary
 * is routine false-positive material. Rather than let that surface as a raw
 * `ENOENT` from a spawn, every packaged binary is inspected up front and again
 * whenever the backend dies, so the failure can be reported as the file it is
 * about. An antivirus kill can exit 0, so the exit code cannot be the
 * discriminator - only the file's absence can.
 */
import fs from 'node:fs';
import process from 'node:process';
import { BinaryComponent, BinaryPlatform, BinaryStatus, type UnusableBinary } from './binary-types';
import { resolvePackagedColibri, resolveStarlingBinary } from './starling-launchers';
import { coreSearchDirectory, findCoreBinary, packagedBackendDirectory } from './starling-paths';

/**
 * The spawn error codes that mean the system refused to start a file that is there.
 *
 * @remarks
 * Windows has no execute bit, so a block by security software, Smart App Control or a policy only
 * shows at the spawn: `EPERM` for an access denial, `UNKNOWN` for the codes libuv does not map
 * (`ERROR_VIRUS_INFECTED`, an application control policy). Node throws both from `spawn()` itself.
 * `EACCES` is the POSIX form, which arrives as an `error` event.
 */
const REFUSED_SPAWN_CODES: ReadonlySet<string> = new Set(['EACCES', 'EPERM', 'UNKNOWN']);

function currentPlatform(): BinaryPlatform {
  if (process.platform === 'win32')
    return BinaryPlatform.WINDOWS;
  return process.platform === 'darwin' ? BinaryPlatform.MACOS : BinaryPlatform.LINUX;
}

function report(component: BinaryComponent, path: string, status: BinaryStatus): UnusableBinary {
  return { component, path, platform: currentPlatform(), status };
}

/** Whether an error came from the system (it carries an errno `code`) rather than from our own checks. */
function isSystemError(error: unknown): error is Error & { code: string; syscall?: string } {
  return error instanceof Error && 'code' in error && typeof error.code === 'string';
}

/**
 * Inspect one binary.
 *
 * @remarks
 * `X_OK` is meaningless on Windows, where `accessSync` only tells us the file
 * exists, so `not-executable` is in practice a POSIX answer here. On Windows the
 * same condition only shows when the spawn fails, see {@link refusedStarling}.
 */
function inspectBinary(component: BinaryComponent, binary: string): UnusableBinary | undefined {
  if (!fs.existsSync(binary))
    return report(component, binary, BinaryStatus.MISSING);

  try {
    fs.accessSync(binary, fs.constants.X_OK);
  }
  catch {
    return report(component, binary, BinaryStatus.NOT_EXECUTABLE);
  }

  return undefined;
}

/**
 * The packaged core, reported against the folder searched rather than a file:
 * the whole folder can be what went, and the binary carries a version in its
 * name that the user has no way to guess.
 *
 * @remarks
 * `findCoreBinary` throws in two ways. A system error means the folder cannot be
 * listed, which is how security software locking it looks, so it is reported as
 * unreadable. A plain error means a broken upgrade left two binaries: not a
 * quarantine, so it is passed over and left to surface where the invocation is
 * built, whose error handling reports it. Nothing is rethrown, since this runs
 * inside the spawn path and the process event handlers.
 */
function inspectCore(): UnusableBinary | undefined {
  const directory = packagedBackendDirectory();
  let resolved: ReturnType<typeof findCoreBinary>;
  try {
    resolved = findCoreBinary(directory);
  }
  catch (error) {
    return isSystemError(error)
      ? report(BinaryComponent.CORE, directory, BinaryStatus.UNREADABLE)
      : undefined;
  }

  if (!resolved)
    return report(BinaryComponent.CORE, coreSearchDirectory(directory) ?? directory, BinaryStatus.MISSING);

  return inspectBinary(BinaryComponent.CORE, resolved.binary);
}

/** Whether a core other than `launchedCore` now sits where the core is looked for, as an update leaves it. */
function isReplacedByAnotherVersion(launchedCore: string): boolean {
  try {
    const current = findCoreBinary(packagedBackendDirectory());
    return current !== undefined && current.binary !== launchedCore && fs.existsSync(current.binary);
  }
  catch {
    return false;
  }
}

/**
 * The core a running starling was launched with.
 *
 * @remarks
 * The core carries its version in its file name, so an update installed while rotki runs (a
 * package manager, or a Homebrew cask swapping the app bundle) removes the launched file and puts
 * a new one beside it. That is reported as replaced, so the user is told to restart rather than
 * to look for a quarantine.
 */
function inspectLaunchedCore(launchedCore: string): UnusableBinary | undefined {
  const unusable = inspectBinary(BinaryComponent.CORE, launchedCore);
  if (unusable?.status === BinaryStatus.MISSING && isReplacedByAnotherVersion(launchedCore))
    return report(BinaryComponent.CORE, launchedCore, BinaryStatus.REPLACED);
  return unusable;
}

/**
 * The first packaged binary that cannot be run, starling first.
 *
 * @remarks
 * starling leads because it is the one Electron spawns itself: if it is the file
 * that went, there is no supervisor left to report anything and this check is
 * the only thing standing between the user and a bare io error.
 *
 * @param launchedCore - the core binary starling was started with. Once there is
 * one, that exact file is what matters: an upgrade can swap in a new version
 * beside it, and a fresh search of the directory would find that one healthy
 * while starling keeps respawning the old path. Before a launch the directory is
 * searched.
 */
export function findUnusableBinary(launchedCore?: string): UnusableBinary | undefined {
  return inspectBinary(BinaryComponent.STARLING, resolveStarlingBinary())
    ?? (launchedCore ? inspectLaunchedCore(launchedCore) : inspectCore())
    ?? inspectBinary(BinaryComponent.COLIBRI, resolvePackagedColibri().binary);
}

/**
 * starling, when a failed spawn of it means the system refused a file that is there.
 *
 * @remarks
 * Only a spawn error counts (its `syscall` names the spawn), since a failure building the
 * invocation can carry the same codes for an unrelated file.
 */
export function refusedStarling(error: unknown): UnusableBinary | undefined {
  if (!isSystemError(error) || !error.syscall?.startsWith('spawn') || !REFUSED_SPAWN_CODES.has(error.code))
    return undefined;

  const binary = resolveStarlingBinary();
  return fs.existsSync(binary) ? report(BinaryComponent.STARLING, binary, BinaryStatus.NOT_EXECUTABLE) : undefined;
}
